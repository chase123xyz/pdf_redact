"""Geometry utilities for coordinate transformations."""

import fitz  # PyMuPDF


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
    scale = 72.0 / dpi

    pdf_x0 = img_x * scale
    pdf_y0 = img_y * scale
    pdf_x1 = (img_x + img_w) * scale
    pdf_y1 = (img_y + img_h) * scale

    return fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)


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
