# PDF Redaction Tool

Permanently redact text and logos from PDF files. Removes specified words, text patterns, PII, and company logos using true PDF redaction (content is deleted, not hidden).

## Features

- **One command**: `pdf-redact` walks you through everything and processes immediately
- **Text redaction**: Word-level or textbox-level precision
- **PII detection**: Built-in patterns for emails, phone numbers, addresses, SSNs
- **Logo detection**: Multi-scale template matching finds logos at any size
- **True redaction**: Content is permanently removed via PyMuPDF
- **Batch processing**: Process multiple PDFs in parallel
- **Detailed reports**: JSON reports of all redactions applied

## Installation

Requires Python 3.9+.

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install
pip install -r .dev/requirements.txt
pip install -e .dev/

# Verify
pdf-redact --help
```

### Platform Notes

**macOS M1/M2**: If OpenCV fails, run `brew install opencv && pip install opencv-python`.

**Windows**: If you get a C++ build tools error, install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the "Desktop development with C++" workload.

**Linux**: Install system deps first: `sudo apt install libgl1-mesa-glx libglib2.0-0`

## Quick Start

```bash
pdf-redact
```

The wizard will:
1. Create folders (`1. original_pdfs/`, `2. logos/`, `3. outputs/`)
2. Ask what text to redact
3. Auto-detect logos in `2. logos/`
4. Process all PDFs immediately

Put your files in place before running, or re-run after adding files.

## Folder Structure

```
your_project/
  1. original_pdfs/   ← Put your PDFs here
  2. logos/            ← Put logo images (PNG/JPG) here
  3. outputs/          ← Redacted PDFs appear here
  .pdf_redact/        ← Config & reports (hidden)
```

## Usage

```bash
pdf-redact              # Interactive wizard + process
pdf-redact -v           # Verbose mode (logo detection debug output)
pdf-redact -c my.yaml   # Use a specific config file
```

## Configuration

Configuration is YAML, stored in `.pdf_redact/config.yaml` (hidden). The wizard generates this for you, but you can edit it manually:

```yaml
version: "1.0"

text_redaction:
  pii:
    redact_emails: true
    redact_phone_numbers: true
    redact_addresses: false
    redact_ssn: false
    custom_names:
      - "John Smith"
      - "Acme Corporation"
    custom_textbox_matches:
      - "CONFIDENTIAL"
    custom_patterns:
      - pattern: "EMP-\\d{5}"
        description: "Employee IDs"
        case_sensitive: false

logo_redaction:
  templates:
    - name: "company_logo"
      image_path: "/absolute/path/to/2. logos/logo.png"
      confidence_threshold: 0.65
      scale_range:
        min: 0.5
        max: 3.0
        step: 0.1

processing:
  render_dpi: 300
  max_workers: 4
  redaction_color: [255, 255, 255]
```

## Troubleshooting

### Logo not detected

1. **Use a clean reference image**: Crop tightly, save as PNG, no whitespace border
2. **Lower confidence threshold**: Try `0.55` - `0.65` in config
3. **Check scale range**: Default `0.5` - `3.0` covers most cases. Use `-v` to see what scales are being tested
4. **Try both color and B&W versions** of the logo as separate templates

### Command not found

```bash
# Re-activate virtual environment
source venv/bin/activate

# Or use module form
python -m pdf_redact.cli --help
```

## FAQ

**Are redactions permanent?**
Yes. PyMuPDF's `apply_redactions()` permanently removes content. Always keep original PDFs as backups.

**Can this handle scanned PDFs?**
Not currently. The tool requires selectable text. Logo detection works on any PDF.

**Can I undo redactions?**
No. Keep your originals in a separate location.

**Why is processing slow?**
Logo detection renders each page at 300 DPI and runs template matching at multiple scales. Lower `render_dpi` or increase `max_workers` in config.

## License

MIT License - see LICENSE file for details.
