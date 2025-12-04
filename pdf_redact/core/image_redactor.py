"""Logo/image redaction using multi-scale template matching."""

import fitz  # PyMuPDF
import cv2
import numpy as np
from typing import List, Tuple
from dataclasses import dataclass
from pathlib import Path

from pdf_redact.config import RedactionConfig, LogoTemplate
from pdf_redact.utils.geometry import image_coords_to_pdf_rect
from pdf_redact.core.text_redactor import RedactionArea


@dataclass
class LogoMatch:
    """Represents a logo match in image coordinates."""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    scale: float


class ImageRedactor:
    """Handles logo/image detection and redaction using template matching."""

    def __init__(self, config: RedactionConfig):
        """
        Initialize the image redactor.

        Args:
            config: Redaction configuration
        """
        self.config = config
        self.templates = self._load_templates()

    def _load_templates(self) -> dict:
        """
        Load all logo templates from config.

        Returns:
            Dictionary mapping template names to loaded images
        """
        templates = {}

        for template_config in self.config.logo_redaction.templates:
            try:
                # Load image in grayscale for matching
                template_path = Path(template_config.image_path)
                if not template_path.exists():
                    print(f"Warning: Template image not found: {template_config.image_path}")
                    continue

                img = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    print(f"Warning: Could not load template: {template_config.image_path}")
                    continue

                templates[template_config.name] = img
            except Exception as e:
                print(f"Warning: Error loading template {template_config.name}: {e}")

        return templates

    def find_all_logos(self, page: fitz.Page) -> List[RedactionArea]:
        """
        Find all logo instances on a page.

        Args:
            page: PDF page to search

        Returns:
            List of redaction areas for logos
        """
        all_areas = []

        for template_config in self.config.logo_redaction.templates:
            if template_config.name not in self.templates:
                continue

            areas = self.find_logos(page, template_config)
            all_areas.extend(areas)

        return all_areas

    def find_logos(self, page: fitz.Page, template_config: LogoTemplate) -> List[RedactionArea]:
        """
        Find logo instances using multi-scale template matching.

        Args:
            page: PDF page to search
            template_config: Logo template configuration

        Returns:
            List of redaction areas
        """
        if template_config.name not in self.templates:
            return []

        template = self.templates[template_config.name]

        try:
            # Render page to image
            dpi = self.config.processing.render_dpi
            pix = page.get_pixmap(dpi=dpi)
            page_img = self._pixmap_to_numpy(pix)

            # Convert to grayscale
            if len(page_img.shape) == 3:
                page_gray = cv2.cvtColor(page_img, cv2.COLOR_RGB2GRAY)
            else:
                page_gray = page_img

            # Multi-scale template matching
            matches = self.multi_scale_match(
                page_gray,
                template,
                template_config.scale_range.min,
                template_config.scale_range.max,
                template_config.scale_range.step,
                template_config.confidence_threshold,
                template_config.method
            )

            # Convert matches to redaction areas
            redaction_areas = []
            for match in matches:
                pdf_rect = image_coords_to_pdf_rect(
                    page,
                    match.x,
                    match.y,
                    match.width,
                    match.height,
                    dpi
                )

                area = RedactionArea(
                    rect=pdf_rect,
                    page_number=page.number,
                    redaction_type="logo",
                    matched_pattern=template_config.name,
                    confidence=match.confidence,
                    metadata={
                        "template": template_config.name,
                        "scale": match.scale,
                        "method": template_config.method
                    }
                )
                redaction_areas.append(area)

            return redaction_areas

        except Exception as e:
            print(f"Error finding logos on page {page.number}: {e}")
            return []

    def multi_scale_match(
        self,
        page_img: np.ndarray,
        template: np.ndarray,
        min_scale: float,
        max_scale: float,
        scale_step: float,
        confidence_threshold: float,
        method: str
    ) -> List[LogoMatch]:
        """
        Perform template matching at multiple scales.

        Args:
            page_img: Page image (grayscale)
            template: Template image (grayscale)
            min_scale: Minimum scale factor
            max_scale: Maximum scale factor
            scale_step: Scale increment
            confidence_threshold: Minimum confidence for matches
            method: OpenCV matching method

        Returns:
            List of logo matches
        """
        all_matches = []

        # Convert method string to OpenCV constant
        method_map = {
            "cv2.TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
            "cv2.TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
            "cv2.TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
        }
        cv_method = method_map.get(method, cv2.TM_CCOEFF_NORMED)

        # Iterate through scales
        scale = min_scale
        while scale <= max_scale:
            # Resize template
            scaled_width = int(template.shape[1] * scale)
            scaled_height = int(template.shape[0] * scale)

            # Skip if template is larger than page
            if scaled_height > page_img.shape[0] or scaled_width > page_img.shape[1]:
                scale += scale_step
                continue

            scaled_template = cv2.resize(
                template,
                (scaled_width, scaled_height),
                interpolation=cv2.INTER_CUBIC
            )

            # Template matching
            result = cv2.matchTemplate(page_img, scaled_template, cv_method)

            # Find matches above threshold
            if cv_method == cv2.TM_SQDIFF_NORMED:
                # For SQDIFF, lower is better, so invert threshold
                locations = np.where(result <= (1.0 - confidence_threshold))
            else:
                locations = np.where(result >= confidence_threshold)

            # Collect matches
            for pt in zip(*locations[::-1]):  # Switch x and y
                match = LogoMatch(
                    x=pt[0],
                    y=pt[1],
                    width=scaled_width,
                    height=scaled_height,
                    confidence=float(result[pt[1], pt[0]]),
                    scale=scale
                )
                all_matches.append(match)

            scale += scale_step

        # Non-maximum suppression to remove overlapping detections
        final_matches = self.non_max_suppression(all_matches, overlap_threshold=0.3)

        return final_matches

    def non_max_suppression(
        self,
        matches: List[LogoMatch],
        overlap_threshold: float = 0.3
    ) -> List[LogoMatch]:
        """
        Remove overlapping detections, keeping only the best match.

        Args:
            matches: List of logo matches
            overlap_threshold: IoU threshold for considering overlap

        Returns:
            Filtered list of matches
        """
        if not matches:
            return []

        # Sort by confidence (descending)
        sorted_matches = sorted(matches, key=lambda m: m.confidence, reverse=True)

        keep = []

        while sorted_matches:
            # Take the best match
            best = sorted_matches.pop(0)
            keep.append(best)

            # Remove all matches that overlap significantly with best
            sorted_matches = [
                m for m in sorted_matches
                if self._calculate_iou(best, m) < overlap_threshold
            ]

        return keep

    @staticmethod
    def _calculate_iou(match1: LogoMatch, match2: LogoMatch) -> float:
        """
        Calculate Intersection over Union (IoU) of two matches.

        Args:
            match1: First match
            match2: Second match

        Returns:
            IoU value (0-1)
        """
        # Calculate intersection
        x1 = max(match1.x, match2.x)
        y1 = max(match1.y, match2.y)
        x2 = min(match1.x + match1.width, match2.x + match2.width)
        y2 = min(match1.y + match1.height, match2.y + match2.height)

        if x2 < x1 or y2 < y1:
            return 0.0  # No overlap

        intersection = (x2 - x1) * (y2 - y1)

        # Calculate union
        area1 = match1.width * match1.height
        area2 = match2.width * match2.height
        union = area1 + area2 - intersection

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def _pixmap_to_numpy(pix: fitz.Pixmap) -> np.ndarray:
        """
        Convert PyMuPDF pixmap to NumPy array.

        Args:
            pix: PyMuPDF pixmap

        Returns:
            NumPy array (H x W x C)
        """
        # Get image data
        img_data = pix.samples

        # Reshape to image
        if pix.n == 1:  # Grayscale
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w)
        elif pix.n == 3:  # RGB
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w, 3)
        elif pix.n == 4:  # RGBA
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w, 4)
            # Convert RGBA to RGB
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        else:
            raise ValueError(f"Unsupported number of channels: {pix.n}")

        return img
