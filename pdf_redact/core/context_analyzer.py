"""Context-aware analysis to distinguish redactable text from schematic labels."""

import fitz  # PyMuPDF
import cv2
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

from pdf_redact.config import RedactionConfig, TextPattern
from pdf_redact.utils.geometry import (
    expand_rect, get_zone_rect, calculate_distance, rects_overlap
)


@dataclass
class FontCharacteristics:
    """Font characteristics analysis result."""
    is_annotation_font: bool = False
    is_technical_font: bool = False
    size_matches_annotation: bool = False
    is_styled: bool = False  # Bold or italic
    annotation_confidence: float = 0.0


class ContextAnalyzer:
    """
    Analyzes context to determine if text should be redacted.

    Uses multiple heuristics:
    1. Proximity analysis - nearby keywords
    2. Font analysis - font family and size
    3. Zone classification - position on page
    4. Schematic detection - dense line areas
    """

    def __init__(self, config: RedactionConfig):
        """
        Initialize the context analyzer.

        Args:
            config: Redaction configuration
        """
        self.config = config
        self.context_rules = config.context_rules
        self._schematic_cache = {}  # Cache schematic areas per page

    def is_in_redactable_context(
        self,
        page: fitz.Page,
        instance: 'TextInstance',
        pattern: TextPattern
    ) -> bool:
        """
        Determine if a text instance should be redacted based on context.

        Args:
            page: PDF page
            instance: Text instance to analyze
            pattern: Pattern configuration

        Returns:
            True if text should be redacted
        """
        # Calculate individual heuristic scores
        proximity_score = self._calculate_proximity_score(page, instance, pattern)
        font_score = self._calculate_font_score(instance, pattern)
        zone_score = self._calculate_zone_score(page, instance, pattern)
        schematic_penalty = self._calculate_schematic_penalty(page, instance)

        # Weighted decision fusion
        # Weights: proximity (40%), font (30%), zone (30%)
        final_score = (
            0.4 * proximity_score +
            0.3 * font_score +
            0.3 * zone_score -
            2.0 * schematic_penalty  # Heavy penalty for schematic areas
        )

        # Threshold for redaction decision
        threshold = 0.6
        return final_score > threshold

    def _calculate_proximity_score(
        self,
        page: fitz.Page,
        instance: 'TextInstance',
        pattern: TextPattern
    ) -> float:
        """
        Calculate score based on nearby keywords.

        Args:
            page: PDF page
            instance: Text instance
            pattern: Pattern configuration

        Returns:
            Proximity score (0-1)
        """
        if not pattern.context_keywords and not pattern.exclude_if_near:
            return 0.5  # Neutral if no keywords specified

        # Find nearby keywords
        context_keyword_count = self._count_nearby_keywords(
            page, instance.bbox, pattern.context_keywords, pattern.proximity_threshold
        )

        exclusion_keyword_count = self._count_nearby_keywords(
            page, instance.bbox, pattern.exclude_if_near, pattern.proximity_threshold
        )

        # Score calculation
        # Positive for context keywords, negative for exclusion keywords
        raw_score = context_keyword_count - exclusion_keyword_count

        # Normalize to 0-1 range using sigmoid
        return self._sigmoid(raw_score)

    def _count_nearby_keywords(
        self,
        page: fitz.Page,
        bbox: fitz.Rect,
        keywords: List[str],
        radius: int
    ) -> int:
        """
        Count how many keywords appear near the given bounding box.

        Args:
            page: PDF page
            bbox: Bounding box to search around
            keywords: Keywords to search for
            radius: Search radius in pixels

        Returns:
            Count of nearby keywords
        """
        if not keywords:
            return 0

        # Expand bbox by radius
        search_area = expand_rect(bbox, radius)

        # Get text in search area
        nearby_text = page.get_text("text", clip=search_area).lower()

        # Count keywords
        count = sum(1 for keyword in keywords if keyword.lower() in nearby_text)
        return count

    def _calculate_font_score(
        self,
        instance: 'TextInstance',
        pattern: TextPattern
    ) -> float:
        """
        Calculate score based on font characteristics.

        Args:
            instance: Text instance
            pattern: Pattern configuration

        Returns:
            Font score (0-1)
        """
        analysis = self.analyze_font_characteristics(instance)

        # Check pattern-specific font criteria
        if pattern.font_criteria:
            # Check if font is excluded
            if instance.font_name in pattern.font_criteria.exclude_fonts:
                return 0.0  # Never redact excluded fonts

            # Check font size range
            if pattern.font_criteria.min_size and instance.font_size < pattern.font_criteria.min_size:
                return 0.0
            if pattern.font_criteria.max_size and instance.font_size > pattern.font_criteria.max_size:
                return 0.0

        # Use analyzed confidence
        return analysis.annotation_confidence

    def analyze_font_characteristics(self, instance: 'TextInstance') -> FontCharacteristics:
        """
        Analyze font characteristics to distinguish annotations from schematics.

        Args:
            instance: Text instance

        Returns:
            Font analysis result
        """
        font_name = instance.font_name
        font_size = instance.font_size

        analysis = FontCharacteristics()

        # Font family classification
        annotation_fonts = self.context_rules.font_heuristics.annotation_fonts
        technical_fonts = self.context_rules.font_heuristics.technical_fonts

        # Check if font name contains any annotation font
        for afont in annotation_fonts:
            if afont.lower() in font_name.lower():
                analysis.is_annotation_font = True
                analysis.annotation_confidence = 0.7
                break

        # Check for technical fonts
        for tfont in technical_fonts:
            if tfont.lower() in font_name.lower():
                analysis.is_technical_font = True
                analysis.annotation_confidence = 0.2
                break

        # Size-based classification
        ann_size_range = self.context_rules.font_heuristics.annotation_size_range
        if ann_size_range[0] <= font_size <= ann_size_range[1]:
            analysis.size_matches_annotation = True
            analysis.annotation_confidence += 0.2

        # Check for styling (bold/italic)
        # Font flags: bit 0=superscript, 1=italic, 2=serifed, 3=monospace, 4=bold
        if instance.font_flags & (1 << 1) or instance.font_flags & (1 << 4):
            analysis.is_styled = True
            analysis.annotation_confidence += 0.1

        # Cap confidence at 1.0
        analysis.annotation_confidence = min(analysis.annotation_confidence, 1.0)

        return analysis

    def _calculate_zone_score(
        self,
        page: fitz.Page,
        instance: 'TextInstance',
        pattern: TextPattern
    ) -> float:
        """
        Calculate score based on page zone.

        Args:
            page: PDF page
            instance: Text instance
            pattern: Pattern configuration

        Returns:
            Zone score (0-1)
        """
        # Check pattern-specific zone filter
        if pattern.zone_filter:
            zone_name = self._get_zone_for_rect(page, instance.bbox)

            # Check exclusions first
            if zone_name in pattern.zone_filter.exclude:
                return 0.0

            # Check inclusions
            if pattern.zone_filter.include and zone_name not in pattern.zone_filter.include:
                return 0.0

        # Get general zone classification
        zone_name = self._get_zone_for_rect(page, instance.bbox)

        # Zone-based scoring
        zone_scores = {
            "header": 0.9,      # Very likely redactable
            "footer": 0.9,      # Very likely redactable
            "title_block": 0.7, # Somewhat likely redactable
            "body": 0.5,        # Neutral
            "schematic": 0.1    # Unlikely redactable
        }

        return zone_scores.get(zone_name, 0.5)

    def _get_zone_for_rect(self, page: fitz.Page, rect: fitz.Rect) -> str:
        """
        Determine which zone a rectangle is in.

        Args:
            page: PDF page
            rect: Rectangle to classify

        Returns:
            Zone name
        """
        zone_defs = self.context_rules.zone_definitions

        # Get center point of rect
        center_x = (rect.x0 + rect.x1) / 2
        center_y = (rect.y0 + rect.y1) / 2
        center = (center_x, center_y)

        # Check title block first (most specific)
        if zone_defs.title_block:
            title_block_rect = get_zone_rect(
                page,
                zone_defs.title_block.top_percent,
                zone_defs.title_block.bottom_percent,
                zone_defs.title_block.left_percent or 0,
                zone_defs.title_block.right_percent or 100
            )
            if rects_overlap(rect, title_block_rect):
                return "title_block"

        # Check header
        header_rect = get_zone_rect(
            page,
            zone_defs.header.top_percent,
            zone_defs.header.bottom_percent
        )
        if rects_overlap(rect, header_rect):
            return "header"

        # Check footer
        footer_rect = get_zone_rect(
            page,
            zone_defs.footer.top_percent,
            zone_defs.footer.bottom_percent
        )
        if rects_overlap(rect, footer_rect):
            return "footer"

        # Check if in schematic area
        if self._is_in_schematic_area(page, rect):
            return "schematic"

        # Default to body
        return "body"

    def _calculate_schematic_penalty(self, page: fitz.Page, instance: 'TextInstance') -> float:
        """
        Calculate penalty if text is in a schematic area.

        Args:
            page: PDF page
            instance: Text instance

        Returns:
            Penalty score (0-1)
        """
        if self._is_in_schematic_area(page, instance.bbox):
            return 1.0
        return 0.0

    def _is_in_schematic_area(self, page: fitz.Page, rect: fitz.Rect) -> bool:
        """
        Determine if a rectangle is in a schematic/drawing area.

        Uses line density detection via OpenCV.

        Args:
            page: PDF page
            rect: Rectangle to check

        Returns:
            True if in schematic area
        """
        # Check cache
        page_id = (page.parent.name, page.number)
        if page_id not in self._schematic_cache:
            self._schematic_cache[page_id] = self._detect_schematic_areas(page)

        schematic_areas = self._schematic_cache[page_id]

        # Check if rect overlaps with any schematic area
        for schematic_rect in schematic_areas:
            if rects_overlap(rect, schematic_rect):
                return True

        return False

    def _detect_schematic_areas(self, page: fitz.Page) -> List[fitz.Rect]:
        """
        Detect areas with dense line drawings (schematics).

        Args:
            page: PDF page

        Returns:
            List of rectangular areas containing schematics
        """
        try:
            # Render page to image at moderate resolution for line detection
            pix = page.get_pixmap(dpi=150)
            img_data = pix.samples
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

            # Convert to grayscale
            if img.shape[2] == 4:  # RGBA
                gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
            else:  # RGB
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

            # Detect edges
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # Detect lines using Hough transform
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=50,
                minLineLength=30,
                maxLineGap=10
            )

            if lines is None or len(lines) == 0:
                return []

            # Create density map by dividing page into grid
            grid_size = 50  # pixels
            h, w = gray.shape
            grid_h = (h + grid_size - 1) // grid_size
            grid_w = (w + grid_size - 1) // grid_size
            density_map = np.zeros((grid_h, grid_w), dtype=np.int32)

            # Count lines in each grid cell
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # Mark grid cells this line passes through
                for t in np.linspace(0, 1, 10):
                    x = int(x1 + t * (x2 - x1))
                    y = int(y1 + t * (y2 - y1))
                    grid_x = min(x // grid_size, grid_w - 1)
                    grid_y = min(y // grid_size, grid_h - 1)
                    density_map[grid_y, grid_x] += 1

            # Find high-density areas (threshold: >5 lines per grid cell)
            high_density = density_map > 5

            # Convert high-density grid cells to PDF rectangles
            schematic_rects = []
            dpi = 150
            scale = 72.0 / dpi  # Convert pixels to PDF points

            for gy in range(grid_h):
                for gx in range(grid_w):
                    if high_density[gy, gx]:
                        # Convert grid cell to PDF coordinates
                        img_x0 = gx * grid_size
                        img_y0 = gy * grid_size
                        img_x1 = min((gx + 1) * grid_size, w)
                        img_y1 = min((gy + 1) * grid_size, h)

                        pdf_rect = fitz.Rect(
                            img_x0 * scale,
                            img_y0 * scale,
                            img_x1 * scale,
                            img_y1 * scale
                        )
                        schematic_rects.append(pdf_rect)

            # Merge nearby rectangles
            from pdf_redact.utils.geometry import merge_nearby_rects
            merged = merge_nearby_rects(schematic_rects, max_distance=10.0)

            return merged

        except Exception as e:
            # If schematic detection fails, return empty list (no schematics detected)
            print(f"Warning: Schematic detection failed for page {page.number}: {e}")
            return []

    def classify_page_zones(self, page: fitz.Page) -> Dict[str, fitz.Rect]:
        """
        Classify page into zones.

        Args:
            page: PDF page

        Returns:
            Dictionary mapping zone names to rectangles
        """
        zone_defs = self.context_rules.zone_definitions

        zones = {}

        # Header
        zones["header"] = get_zone_rect(
            page,
            zone_defs.header.top_percent,
            zone_defs.header.bottom_percent
        )

        # Footer
        zones["footer"] = get_zone_rect(
            page,
            zone_defs.footer.top_percent,
            zone_defs.footer.bottom_percent
        )

        # Title block
        if zone_defs.title_block:
            zones["title_block"] = get_zone_rect(
                page,
                zone_defs.title_block.top_percent,
                zone_defs.title_block.bottom_percent,
                zone_defs.title_block.left_percent or 0,
                zone_defs.title_block.right_percent or 100
            )

        return zones

    @staticmethod
    def _sigmoid(x: float) -> float:
        """
        Sigmoid function to normalize scores to 0-1 range.

        Args:
            x: Input value

        Returns:
            Normalized value between 0 and 1
        """
        return 1.0 / (1.0 + np.exp(-x))
