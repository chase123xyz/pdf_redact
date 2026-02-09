# PDF Redact

PDF redaction tool that permanently removes specified words, text patterns, and logos from PDF files.

## Tech Stack

- Python 3.9+
- PyMuPDF (fitz) - PDF reading, redaction annotations, saving
- OpenCV (cv2) - Template matching for logo detection
- Click - CLI framework
- Pydantic - Config validation
- PyYAML - Config file parsing

## Architecture

```
cli.py              CLI entry point (init wizard, process, preview commands)
  -> PDFProcessor   Orchestrator: iterates pages, delegates to redactors
     -> TextRedactor    Finds text matches using regex/literal patterns
     -> ImageRedactor   Finds logos using multi-scale template matching
```

## Key Directories

- `input_pdfs/` - Source PDFs to redact
- `output_pdfs/` - Redacted output PDFs
- `reference_logos/` - Logo images (PNG/JPG) used as templates for detection

## Running

```bash
pip install -e .
pdf-redact init        # Interactive wizard, processes PDFs automatically
pdf-redact process     # Re-process with existing config.yaml
pdf-redact process -v  # Verbose mode for logo detection debugging
```

## How It Works

1. **Text redaction**: Extracts text with `page.get_text("words")` or `page.get_text("dict")`, matches against regex/literal patterns, creates redaction annotations at matched bounding boxes
2. **Logo detection**: Renders each page at 300 DPI, runs OpenCV `matchTemplate` at multiple scales with both grayscale and edge-based matching, converts pixel coordinates back to PDF points
3. **Redaction**: Uses `page.add_redact_annot()` + `page.apply_redactions()` which permanently removes content

## Common Pitfalls

- **Logo template paths**: Stored as absolute paths in config. `ImageRedactor._load_templates()` resolves relative paths against CWD.
- **Confidence threshold**: Default 0.65. Too low = false positives, too high = misses. Use `--verbose` to debug.
- **Scale range**: Default 0.5-3.0 with step 0.1. Templates smaller than 30px after scaling are skipped. Matches with PDF area < 200 sq pts are rejected.
- **Config compatibility**: `RedactionConfig` uses `model_config = {"extra": "ignore"}` so old configs with removed fields (like `context_rules`) won't crash.
