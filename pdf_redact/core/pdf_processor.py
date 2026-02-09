"""Main PDF processing orchestrator."""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from pdf_redact.config import RedactionConfig
from pdf_redact.core.text_redactor import TextRedactor, RedactionArea
from pdf_redact.core.image_redactor import ImageRedactor


class PDFProcessor:
    """Main orchestrator for PDF redaction processing."""

    def __init__(self, config: RedactionConfig):
        self.config = config
        self.text_redactor = TextRedactor(config)
        self.image_redactor = ImageRedactor(config)
        self.all_redactions = []

    def process_pdf(self, input_path: str, output_path: str) -> List[RedactionArea]:
        """Process a single PDF file."""
        try:
            doc = fitz.open(input_path)
            redaction_areas = []

            for page in doc:
                page_areas = self.process_page(page)
                redaction_areas.extend(page_areas)

            output_settings = self.config.processing.output

            save_options = {
                "garbage": 4,
                "deflate": output_settings.compress,
                "clean": not output_settings.preserve_metadata,
            }

            doc.save(output_path, **save_options)
            doc.close()

            return redaction_areas

        except Exception as e:
            print(f"Error processing PDF {input_path}: {e}")
            raise

    def process_page(self, page: fitz.Page) -> List[RedactionArea]:
        """Process a single page."""
        all_areas = []

        # Text redaction
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
        """Apply redactions to a page with white fill."""
        if not areas:
            return

        # Get redaction color from config (RGB 0-255)
        color_rgb = self.config.processing.redaction_color
        # Convert to 0-1 range for PyMuPDF
        fill_color = tuple(c / 255.0 for c in color_rgb)

        for area in areas:
            page.add_redact_annot(area.rect, fill=fill_color)

        page.apply_redactions()

    def process_directory(
        self,
        input_dir: str,
        output_dir: str,
        pattern: str = "*.pdf"
    ) -> dict:
        """Process all PDFs in a directory."""
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        output_path.mkdir(parents=True, exist_ok=True)

        # Find all PDFs (both .pdf and .PDF)
        pdf_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))

        if not pdf_files:
            print(f"No PDF files found in {input_dir}")
            return {}

        print(f"Found {len(pdf_files)} PDF file(s) to process")

        max_workers = self.config.processing.max_workers
        results = {}

        if max_workers == 1:
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
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_pdf = {}
                for pdf_file in pdf_files:
                    output_file = output_path / pdf_file.name
                    future = executor.submit(
                        self.process_pdf,
                        str(pdf_file),
                        str(output_file)
                    )
                    future_to_pdf[future] = (str(pdf_file), str(output_file))

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
        """Preview what would be redacted without actually redacting."""
        doc = fitz.open(pdf_path)
        all_areas = []

        for page in doc:
            if self.text_redactor.patterns:
                text_areas = self.text_redactor.find_redaction_areas(
                    page,
                    self.text_redactor.patterns
                )
                all_areas.extend(text_areas)

            if self.config.logo_redaction.templates:
                logo_areas = self.image_redactor.find_all_logos(page)
                all_areas.extend(logo_areas)

        doc.close()
        return all_areas
