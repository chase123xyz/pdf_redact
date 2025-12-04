"""Main PDF processing orchestrator."""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from pdf_redact.config import RedactionConfig
from pdf_redact.core.text_redactor import TextRedactor, RedactionArea
from pdf_redact.core.image_redactor import ImageRedactor
from pdf_redact.core.context_analyzer import ContextAnalyzer
from pdf_redact.utils.geometry import merge_nearby_rects


class PDFProcessor:
    """Main orchestrator for PDF redaction processing."""

    def __init__(self, config: RedactionConfig):
        """
        Initialize the PDF processor.

        Args:
            config: Redaction configuration
        """
        self.config = config

        # Initialize components
        self.context_analyzer = ContextAnalyzer(config)
        self.text_redactor = TextRedactor(config)
        self.image_redactor = ImageRedactor(config)

        # Link text redactor with context analyzer
        self.text_redactor.set_context_analyzer(self.context_analyzer)

        # Track all redactions for reporting
        self.all_redactions = []

    def process_pdf(self, input_path: str, output_path: str) -> List[RedactionArea]:
        """
        Process a single PDF file.

        Args:
            input_path: Path to input PDF
            output_path: Path to save redacted PDF

        Returns:
            List of all redaction areas applied
        """
        try:
            # Open PDF
            doc = fitz.open(input_path)

            redaction_areas = []

            # Process each page
            for page in doc:
                page_areas = self.process_page(page)
                redaction_areas.extend(page_areas)

            # Save redacted PDF
            output_settings = self.config.processing.output

            save_options = {
                "garbage": 4,  # Garbage collection level
                "deflate": output_settings.compress,
                "clean": not output_settings.preserve_metadata,
                "linear": output_settings.linearize,
            }

            doc.save(output_path, **save_options)
            doc.close()

            return redaction_areas

        except Exception as e:
            print(f"Error processing PDF {input_path}: {e}")
            raise

    def process_page(self, page: fitz.Page) -> List[RedactionArea]:
        """
        Process a single page.

        Args:
            page: PDF page

        Returns:
            List of redaction areas applied to this page
        """
        all_areas = []

        # Text redaction - use patterns built from config
        if self.text_redactor.patterns:
            text_areas = self.text_redactor.find_redaction_areas(
                page,
                self.text_redactor.patterns
            )
            all_areas.extend(text_areas)

        # Logo redaction
        if self.config.logo_redaction.templates:
            logo_areas = self.image_redactor.find_all_logos(page)
            all_areas.extend(logo_areas)

        # Apply redactions
        if all_areas:
            self.apply_redactions(page, all_areas)

        return all_areas

    def apply_redactions(self, page: fitz.Page, areas: List[RedactionArea]) -> None:
        """
        Apply redactions to a page with white fill.

        Args:
            page: PDF page
            areas: List of areas to redact
        """
        if not areas:
            return

        # Get redaction color from config (RGB 0-255)
        color_rgb = self.config.processing.redaction_color
        # Convert to 0-1 range for PyMuPDF
        fill_color = tuple(c / 255.0 for c in color_rgb)

        # Merge nearby rectangles to avoid gaps
        rects = [area.rect for area in areas]
        merged_rects = merge_nearby_rects(rects, max_distance=5.0)

        # Add redaction annotations
        for rect in merged_rects:
            page.add_redact_annot(rect, fill=fill_color)

        # Apply redactions (permanently removes content)
        page.apply_redactions()

    def process_directory(
        self,
        input_dir: str,
        output_dir: str,
        pattern: str = "*.pdf"
    ) -> dict:
        """
        Process all PDFs in a directory.

        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            pattern: File pattern to match (default: "*.pdf")

        Returns:
            Dictionary mapping input paths to redaction counts
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)

        # Find all PDFs
        pdf_files = list(input_path.glob(pattern))

        if not pdf_files:
            print(f"No PDF files found in {input_dir}")
            return {}

        print(f"Found {len(pdf_files)} PDF file(s) to process")

        # Process PDFs
        max_workers = self.config.processing.max_workers
        results = {}

        if max_workers == 1:
            # Single-threaded processing
            for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
                output_file = output_path / pdf_file.name
                try:
                    redactions = self.process_pdf(str(pdf_file), str(output_file))
                    results[str(pdf_file)] = {
                        "output": str(output_file),
                        "redaction_count": len(redactions),
                        "redactions": redactions,
                        "success": True,
                        "error": None
                    }
                except Exception as e:
                    results[str(pdf_file)] = {
                        "output": None,
                        "redaction_count": 0,
                        "redactions": [],
                        "success": False,
                        "error": str(e)
                    }
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_pdf = {}
                for pdf_file in pdf_files:
                    output_file = output_path / pdf_file.name
                    future = executor.submit(
                        self.process_pdf,
                        str(pdf_file),
                        str(output_file)
                    )
                    future_to_pdf[future] = (str(pdf_file), str(output_file))

                # Collect results with progress bar
                for future in tqdm(
                    as_completed(future_to_pdf),
                    total=len(future_to_pdf),
                    desc="Processing PDFs"
                ):
                    input_file, output_file = future_to_pdf[future]
                    try:
                        redactions = future.result()
                        results[input_file] = {
                            "output": output_file,
                            "redaction_count": len(redactions),
                            "redactions": redactions,
                            "success": True,
                            "error": None
                        }
                    except Exception as e:
                        results[input_file] = {
                            "output": None,
                            "redaction_count": 0,
                            "redactions": [],
                            "success": False,
                            "error": str(e)
                        }

        return results

    def preview_redactions(self, pdf_path: str) -> List[RedactionArea]:
        """
        Preview what would be redacted without actually redacting.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of redaction areas that would be applied
        """
        doc = fitz.open(pdf_path)
        all_areas = []

        for page in doc:
            # Text redaction
            if self.config.text_redaction.patterns:
                text_areas = self.text_redactor.find_redaction_areas(
                    page,
                    self.config.text_redaction.patterns
                )
                all_areas.extend(text_areas)

            # Logo redaction
            if self.config.logo_redaction.templates:
                logo_areas = self.image_redactor.find_all_logos(page)
                all_areas.extend(logo_areas)

        doc.close()
        return all_areas
