"""Geometry utilities for bounding box operations and coordinate transformations."""

import fitz  # PyMuPDF
from typing import List, Tuple
import math


def expand_rect(rect: fitz.Rect, radius: float) -> fitz.Rect:
    """
    Expand a rectangle by the given radius in all directions.

    Args:
        rect: Original rectangle
        radius: Expansion radius in pixels

    Returns:
        Expanded rectangle
    """
    return fitz.Rect(
        rect.x0 - radius,
        rect.y0 - radius,
        rect.x1 + radius,
        rect.y1 + radius
    )


def rects_overlap(rect1: fitz.Rect, rect2: fitz.Rect) -> bool:
    """
    Check if two rectangles overlap.

    Args:
        rect1: First rectangle
        rect2: Second rectangle

    Returns:
        True if rectangles overlap
    """
    return not (rect1.x1 < rect2.x0 or rect2.x1 < rect1.x0 or
                rect1.y1 < rect2.y0 or rect2.y1 < rect1.y0)


def merge_nearby_rects(rects: List[fitz.Rect], max_distance: float = 5.0) -> List[fitz.Rect]:
    """
    Merge rectangles that are close to each other to avoid gaps in redactions.

    Args:
        rects: List of rectangles
        max_distance: Maximum distance for merging

    Returns:
        List of merged rectangles
    """
    if not rects:
        return []

    # Sort by x0, then y0
    sorted_rects = sorted(rects, key=lambda r: (r.x0, r.y0))
    merged = [sorted_rects[0]]

    for current in sorted_rects[1:]:
        last = merged[-1]

        # Check if current is close to last
        # Expand last rect by max_distance and see if it overlaps with current
        expanded = expand_rect(last, max_distance)

        if rects_overlap(expanded, current):
            # Merge by taking union
            merged[-1] = fitz.Rect(
                min(last.x0, current.x0),
                min(last.y0, current.y0),
                max(last.x1, current.x1),
                max(last.y1, current.y1)
            )
        else:
            merged.append(current)

    return merged


def calculate_distance(rect1: fitz.Rect, rect2: fitz.Rect) -> float:
    """
    Calculate the minimum distance between two rectangles.

    Args:
        rect1: First rectangle
        rect2: Second rectangle

    Returns:
        Minimum distance in pixels (0 if overlapping)
    """
    if rects_overlap(rect1, rect2):
        return 0.0

    # Calculate center points
    center1_x = (rect1.x0 + rect1.x1) / 2
    center1_y = (rect1.y0 + rect1.y1) / 2
    center2_x = (rect2.x0 + rect2.x1) / 2
    center2_y = (rect2.y0 + rect2.y1) / 2

    # Euclidean distance between centers
    dx = center2_x - center1_x
    dy = center2_y - center1_y

    return math.sqrt(dx * dx + dy * dy)


def point_in_rect(point: Tuple[float, float], rect: fitz.Rect) -> bool:
    """
    Check if a point is inside a rectangle.

    Args:
        point: (x, y) coordinates
        rect: Rectangle to check

    Returns:
        True if point is inside rectangle
    """
    x, y = point
    return rect.x0 <= x <= rect.x1 and rect.y0 <= y <= rect.y1


def rect_area(rect: fitz.Rect) -> float:
    """
    Calculate the area of a rectangle.

    Args:
        rect: Rectangle

    Returns:
        Area in square pixels
    """
    return (rect.x1 - rect.x0) * (rect.y1 - rect.y0)


def image_coords_to_pdf_rect(
    page: fitz.Page,
    img_x: int,
    img_y: int,
    img_w: int,
    img_h: int,
    dpi: int
) -> fitz.Rect:
    """
    Convert image pixel coordinates to PDF coordinates.

    PyMuPDF coordinate system:
    - Origin at top-left
    - Units in points (1/72 inch)

    Image coordinate system:
    - Origin at top-left
    - Units in pixels at given DPI

    Args:
        page: PDF page
        img_x: Image x coordinate (left)
        img_y: Image y coordinate (top)
        img_w: Image width
        img_h: Image height
        dpi: DPI used for rendering

    Returns:
        PDF rectangle in page coordinates
    """
    # Get page dimensions
    page_rect = page.rect

    # Calculate scaling factor
    # Page width in points, rendered at dpi gives image width in pixels
    # image_width = page_width * dpi / 72
    # So: pdf_coord = image_coord * 72 / dpi
    scale = 72.0 / dpi

    # Convert image coordinates to PDF coordinates
    pdf_x0 = img_x * scale
    pdf_y0 = img_y * scale
    pdf_x1 = (img_x + img_w) * scale
    pdf_y1 = (img_y + img_h) * scale

    return fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)


def get_zone_rect(page: fitz.Page, top_percent: float, bottom_percent: float,
                  left_percent: float = 0, right_percent: float = 100) -> fitz.Rect:
    """
    Get a rectangle representing a zone on the page based on percentages.

    Args:
        page: PDF page
        top_percent: Top boundary as percentage (0-100)
        bottom_percent: Bottom boundary as percentage (0-100)
        left_percent: Left boundary as percentage (0-100)
        right_percent: Right boundary as percentage (0-100)

    Returns:
        Rectangle representing the zone
    """
    page_rect = page.rect
    width = page_rect.width
    height = page_rect.height

    return fitz.Rect(
        page_rect.x0 + width * left_percent / 100,
        page_rect.y0 + height * top_percent / 100,
        page_rect.x0 + width * right_percent / 100,
        page_rect.y0 + height * bottom_percent / 100
    )


def rect_to_dict(rect: fitz.Rect) -> dict:
    """
    Convert a fitz.Rect to a dictionary for serialization.

    Args:
        rect: Rectangle to convert

    Returns:
        Dictionary with x0, y0, x1, y1
    """
    return {
        "x0": rect.x0,
        "y0": rect.y0,
        "x1": rect.x1,
        "y1": rect.y1
    }
