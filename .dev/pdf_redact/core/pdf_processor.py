"""Main PDF processing orchestrator."""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, MofNCompleteColumn

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
            raise RuntimeError(f"Error processing PDF {input_path}: {e}") from e

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
        pattern: str = "*.pdf",
        console: Optional[Console] = None,
    ) -> dict:
        """Process all PDFs in a directory."""
        if console is None:
            console = Console()

        input_path = Path(input_dir)
        output_path = Path(output_dir)

        output_path.mkdir(parents=True, exist_ok=True)

        # Find all PDFs (both .pdf and .PDF)
        pdf_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))

        if not pdf_files:
            console.print(f"[yellow]No PDF files found in {input_dir}[/yellow]")
            return {}

        console.print(f"Found [bold]{len(pdf_files)}[/bold] PDF file(s) to process\n")

        max_workers = self.config.processing.max_workers
        results = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.fields[filename]}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing", total=len(pdf_files), filename="")

            if max_workers == 1:
                for pdf_file in pdf_files:
                    progress.update(task, filename=pdf_file.name)
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
                    progress.advance(task)
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
                        future_to_pdf[future] = (str(pdf_file), str(output_file), pdf_file.name)

                    for future in as_completed(future_to_pdf):
                        input_file, output_file, filename = future_to_pdf[future]
                        progress.update(task, filename=filename)
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
                        progress.advance(task)

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
