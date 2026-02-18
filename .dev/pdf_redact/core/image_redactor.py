"""Logo/image redaction using multi-scale template matching."""

import fitz  # PyMuPDF
import cv2
import numpy as np
from typing import List
from dataclasses import dataclass
from pathlib import Path

from pdf_redact.config import RedactionConfig, LogoTemplate
from pdf_redact.utils.geometry import image_coords_to_pdf_rect
from pdf_redact.core.text_redactor import RedactionArea

# Minimum bounding box area in PDF points squared to reject tiny false positives
MIN_MATCH_AREA_PTS = 200

# Minimum template dimension in pixels after scaling
MIN_TEMPLATE_DIM = 30


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

    def __init__(self, config: RedactionConfig, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.templates = self._load_templates()

    def _load_templates(self) -> dict:
        """Load all logo templates from config."""
        templates = {}

        for template_config in self.config.logo_redaction.templates:
            try:
                template_path = Path(template_config.image_path)

                # Resolve relative paths against CWD
                if not template_path.is_absolute():
                    template_path = Path.cwd() / template_path

                if not template_path.exists():
                    print(f"Warning: Template image not found: {template_path}")
                    continue

                # Load image with alpha channel support
                # Use numpy fromfile + imdecode to handle unicode paths
                # (cv2.imread fails on non-ASCII filenames)
                img_bytes = np.fromfile(str(template_path), dtype=np.uint8)
                img = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
                if img is None:
                    print(f"Warning: Could not load template: {template_path}")
                    continue

                # Handle alpha channel: composite onto white background
                if len(img.shape) == 3 and img.shape[2] == 4:
                    alpha = img[:, :, 3] / 255.0
                    rgb = img[:, :, :3]
                    white_bg = np.ones_like(rgb, dtype=np.uint8) * 255
                    composited = (rgb * alpha[:, :, np.newaxis] + white_bg * (1 - alpha[:, :, np.newaxis])).astype(np.uint8)
                    gray = cv2.cvtColor(composited, cv2.COLOR_BGR2GRAY)
                elif len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                else:
                    gray = img

                templates[template_config.name] = gray
                if self.verbose:
                    print(f"  Loaded template '{template_config.name}': {gray.shape[1]}x{gray.shape[0]}px from {template_path}")

            except Exception as e:
                print(f"Warning: Error loading template {template_config.name}: {e}")

        return templates

    def find_all_logos(self, page: fitz.Page) -> List[RedactionArea]:
        """Find all logo instances on a page."""
        all_areas = []

        for template_config in self.config.logo_redaction.templates:
            if template_config.name not in self.templates:
                continue

            areas = self.find_logos(page, template_config)
            all_areas.extend(areas)

        return all_areas

    def find_logos(self, page: fitz.Page, template_config: LogoTemplate) -> List[RedactionArea]:
        """Find logo instances using multi-scale template matching."""
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

            # Multi-scale matching (no rotation search — logos appear at 0 degrees)
            matches = self.multi_scale_match(
                page_gray,
                template,
                template_config.scale_range.min,
                template_config.scale_range.max,
                template_config.scale_range.step,
                template_config.confidence_threshold,
                template_config.method
            )

            # NMS to remove overlapping detections
            matches = self.non_max_suppression(matches, overlap_threshold=0.5)

            # Convert matches to redaction areas, filtering by minimum PDF size
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

                # Reject matches whose PDF bounding box is too small
                rect_area = (pdf_rect.x1 - pdf_rect.x0) * (pdf_rect.y1 - pdf_rect.y0)
                if rect_area < MIN_MATCH_AREA_PTS:
                    if self.verbose:
                        print(f"    Rejected small match: {rect_area:.0f} sq pts (min {MIN_MATCH_AREA_PTS})")
                    continue

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

            if self.verbose:
                print(f"  Page {page.number + 1}: {len(redaction_areas)} logo match(es) for '{template_config.name}'")

            return redaction_areas

        except Exception as e:
            print(f"Error finding logos on page {page.number}: {e}")
            return []

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """Apply Gaussian blur and normalization for robust matching."""
        blurred = cv2.GaussianBlur(img, (3, 3), 0)
        normalized = cv2.normalize(blurred, None, 0, 255, cv2.NORM_MINMAX)
        return normalized

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
        """Perform template matching at multiple scales with edge-based matching."""
        all_matches = []

        # Convert method string to OpenCV constant
        method_map = {
            "cv2.TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
            "cv2.TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
            "cv2.TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
        }
        cv_method = method_map.get(method, cv2.TM_CCOEFF_NORMED)

        # Preprocess page image
        page_preprocessed = self._preprocess(page_img)

        # Compute edge maps for the page
        page_edges = cv2.Canny(page_preprocessed, 50, 150)

        # Iterate through scales
        scale = min_scale
        while scale <= max_scale:
            scaled_width = int(template.shape[1] * scale)
            scaled_height = int(template.shape[0] * scale)

            # Skip if template is too small
            if scaled_width < MIN_TEMPLATE_DIM or scaled_height < MIN_TEMPLATE_DIM:
                scale += scale_step
                continue

            # Skip if template is larger than page
            if scaled_height > page_img.shape[0] or scaled_width > page_img.shape[1]:
                scale += scale_step
                continue

            scaled_template = cv2.resize(
                template,
                (scaled_width, scaled_height),
                interpolation=cv2.INTER_CUBIC
            )

            # Preprocess scaled template
            template_preprocessed = self._preprocess(scaled_template)

            # Grayscale template matching
            result_gray = cv2.matchTemplate(page_preprocessed, template_preprocessed, cv_method)

            # Edge-based template matching
            template_edges = cv2.Canny(template_preprocessed, 50, 150)
            result_edges = cv2.matchTemplate(page_edges, template_edges, cv_method)

            # Weighted average: grayscale is primary, edge is supplementary
            # Edge scores tend to be much lower, so weight grayscale more heavily
            result = np.maximum(result_gray, 0.7 * result_gray + 0.3 * result_edges)

            # Find matches above the configured threshold
            if cv_method == cv2.TM_SQDIFF_NORMED:
                locations = np.where(result <= (1.0 - confidence_threshold))
            else:
                locations = np.where(result >= confidence_threshold)

            # Collect matches
            for pt in zip(*locations[::-1]):  # Switch x and y
                confidence_val = float(result[pt[1], pt[0]])

                if cv_method == cv2.TM_SQDIFF_NORMED:
                    if confidence_val <= (1.0 - confidence_threshold):
                        match = LogoMatch(
                            x=pt[0],
                            y=pt[1],
                            width=scaled_width,
                            height=scaled_height,
                            confidence=1.0 - confidence_val,
                            scale=scale
                        )
                        all_matches.append(match)
                else:
                    if confidence_val >= confidence_threshold:
                        match = LogoMatch(
                            x=pt[0],
                            y=pt[1],
                            width=scaled_width,
                            height=scaled_height,
                            confidence=confidence_val,
                            scale=scale
                        )
                        all_matches.append(match)

            scale += scale_step

        # NMS to remove overlapping detections
        final_matches = self.non_max_suppression(all_matches, overlap_threshold=0.5)

        return final_matches

    def non_max_suppression(
        self,
        matches: List[LogoMatch],
        overlap_threshold: float = 0.5
    ) -> List[LogoMatch]:
        """Remove overlapping detections, keeping only the best match."""
        if not matches:
            return []

        # Sort by confidence (descending)
        sorted_matches = sorted(matches, key=lambda m: m.confidence, reverse=True)

        keep = []

        while sorted_matches:
            best = sorted_matches.pop(0)
            keep.append(best)

            sorted_matches = [
                m for m in sorted_matches
                if self._calculate_iou(best, m) < overlap_threshold
            ]

        return keep

    @staticmethod
    def _calculate_iou(match1: LogoMatch, match2: LogoMatch) -> float:
        """Calculate Intersection over Union (IoU) of two matches."""
        x1 = max(match1.x, match2.x)
        y1 = max(match1.y, match2.y)
        x2 = min(match1.x + match1.width, match2.x + match2.width)
        y2 = min(match1.y + match1.height, match2.y + match2.height)

        if x2 < x1 or y2 < y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)

        area1 = match1.width * match1.height
        area2 = match2.width * match2.height
        union = area1 + area2 - intersection

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def _pixmap_to_numpy(pix: fitz.Pixmap) -> np.ndarray:
        """Convert PyMuPDF pixmap to NumPy array."""
        img_data = pix.samples

        if pix.n == 1:  # Grayscale
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w)
        elif pix.n == 3:  # RGB
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w, 3)
        elif pix.n == 4:  # RGBA
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w, 4)
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        else:
            raise ValueError(f"Unsupported number of channels: {pix.n}")

        return img
