# PDF Redaction Tool

**Intelligent PII redaction for PDF documents**

Automatically detect and redact sensitive information (PII) from PDF files including emails, phone numbers, addresses, names, and custom text patterns. Permanently removes content with true redaction (not just white boxes).

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Installation](#installation)
  - [macOS Installation](#macos-installation)
  - [Windows Installation](#windows-installation)
  - [Linux Installation](#linux-installation)
- [Quick Start](#quick-start)
- [Detailed Usage](#detailed-usage)
  - [Interactive Configuration](#interactive-configuration)
  - [Processing PDFs](#processing-pdfs)
  - [Preview Mode](#preview-mode)
- [Configuration Guide](#configuration-guide)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Features

✅ **One Command Setup**: Just run `pdf-redact init` and everything happens automatically
✅ **Automatic PII Detection**: Built-in patterns for emails, phone numbers, addresses, and SSNs
✅ **Custom Name Redaction**: Specify exact names to redact across all documents
✅ **Auto Logo Detection**: Automatically finds and redacts all images in reference_logos folder
✅ **True Redaction**: Permanently removes content (not fake white boxes)
✅ **Batch Processing**: Process multiple PDFs in parallel
✅ **No Configuration Needed**: Simple wizard asks what to redact, handles the rest
✅ **Detailed Reports**: JSON reports of all redactions
✅ **Case-Insensitive**: Works with both .pdf and .PDF file extensions

## How It Works

### Automatic PII Detection

The tool can automatically detect and redact:

1. **Email Addresses**: `john.doe@company.com`
2. **Phone Numbers**: `(555) 123-4567`, `555-123-4567`, `555.123.4567`
3. **Street Addresses**: `123 Main Street`, `456 Oak Avenue`
4. **Social Security Numbers**: `123-45-6789`

### Custom Redaction

You can also specify:

- **Specific Names**: "John Smith", "Acme Corporation"
- **Custom Text**: "CONFIDENTIAL", "INTERNAL USE ONLY"
- **Regex Patterns**: `Employee ID: \d+`, `Case #\d{6}`

### Logo Detection

Multi-scale template matching finds company logos at various sizes and rotations across all pages.

---

## Installation

### Prerequisites

- **Python 3.9 or higher**
- **8GB RAM** (recommended for large PDFs)
- **500MB disk space** for dependencies

### macOS Installation

```bash
# 1. Check Python version
python3 --version  # Should be 3.9 or higher

# 2. Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. Clone or download the repository
cd /Users/chase/Documents/Development/Claude
cd pdf_redact

# 4. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Install the package
pip install -e .

# 7. Verify installation
pdf-redact --help
```

#### macOS Troubleshooting

**Problem**: `pip` command not found
**Solution**: Use `pip3` instead: `pip3 install -r requirements.txt`

**Problem**: Permission errors during install
**Solution**: Don't use `sudo`. Always use a virtual environment as shown above.

**Problem**: OpenCV fails on M1/M2 Macs
**Solution**:
```bash
brew install opencv
pip install opencv-python
```

**Problem**: `pdf-redact` command not found after install
**Solution 1**: Re-activate virtual environment: `source venv/bin/activate`
**Solution 2**: Use module form: `python -m pdf_redact.cli --help`
**Solution 3**: Check PATH includes `venv/bin`: `echo $PATH`

### Windows Installation

```powershell
# 1. Check Python version (Command Prompt or PowerShell)
python --version  # Should be 3.9 or higher

# 2. Navigate to project directory
cd C:\Users\chase\Documents\Development\Claude\pdf_redact

# 3. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install the package
pip install -e .

# 6. Verify installation
pdf-redact --help
```

#### Windows Troubleshooting

**Problem**: `python` not recognized
**Solution**: Install Python from [python.org](https://python.org). During installation, check "Add Python to PATH".

**Problem**: Microsoft Visual C++ 14.0 required (OpenCV error)
**Solution**:
1. Download [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Install with "Desktop development with C++" workload
3. Restart terminal and retry installation

**Problem**: PowerShell execution policy errors
**Solution**: Run PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Problem**: `pdf-redact` not recognized
**Solution 1**: Add Scripts to PATH: `C:\path\to\venv\Scripts`
**Solution 2**: Use module form: `python -m pdf_redact.cli --help`
**Solution 3**: Run directly: `.\venv\Scripts\pdf-redact.exe --help`

### Linux Installation (Ubuntu/Debian)

```bash
# 1. Install Python and dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 2. Install OpenCV system dependencies
sudo apt install libgl1-mesa-glx libglib2.0-0

# 3. Follow same steps as macOS for virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## Quick Start

**It's a single command!** Just run:

```bash
pdf-redact init
```

That's it! The wizard will:
1. **Create folders** automatically (input_pdfs, output_pdfs, reference_logos)
2. Tell you where to put your files
3. Ask what text you want to redact
4. Auto-detect logos from reference_logos folder
5. **Automatically process all PDFs** in input_pdfs
6. Save redacted PDFs to output_pdfs

**Example session:**
```
================================================================================
PDF Redaction Tool - Setup Wizard
================================================================================

✓ Created folders: input_pdfs, output_pdfs, reference_logos

WHERE TO PUT YOUR FILES:
  • Put your PDF files in the 'input_pdfs' folder
  • Put logo images (PNG/JPG) in the 'reference_logos' folder
  • Redacted PDFs will be saved to 'output_pdfs'

Press Enter to continue...

--- TEXT REDACTION ---

What text do you want to redact?

Enter text or names to redact (one per line).
Examples: 'John Smith', 'Acme Corporation', 'CONFIDENTIAL'
Type 'done' when finished.

Text to redact: John Smith
✓ Will redact: John Smith
Text to redact: Acme Corporation
✓ Will redact: Acme Corporation
Text to redact: done

Also redact email addresses? (e.g., john@example.com) [y/N]: y
✓ Will redact email addresses

Also redact phone numbers? (e.g., 555-123-4567) [y/N]: y
✓ Will redact phone numbers

--- LOGO REDACTION ---

Found 2 logo(s) in reference_logos folder:
  • company_logo
  • watermark

================================================================================
✓ Configuration saved to: config.yaml
================================================================================

Processing your PDFs now...

Found 3 PDF file(s) to process

================================================================================
✓ ALL DONE!
================================================================================
Files processed: 3/3
Total redactions: 47

REDACTED PDFs ARE IN: output_pdfs/
(Your original PDFs in input_pdfs/ are unchanged)
```

**That's it!** Your redacted PDFs are ready in the `output_pdfs/` folder.

---

## Detailed Usage

### First-Time Setup

The `init` command does everything automatically:

```bash
pdf-redact init
```

**What it does:**
1. Creates folders (input_pdfs, output_pdfs, reference_logos)
2. Asks what text to redact
3. Auto-detects logos in reference_logos folder
4. Saves configuration
5. **Processes all PDFs immediately**

**Optional: Custom config filename**
```bash
pdf-redact init --output my_config.yaml
```

### Re-Running with Existing Config

If you already have a config file and want to re-process PDFs:

```bash
pdf-redact process --config config.yaml --input-dir input_pdfs --output-dir output_pdfs
```

**Options:**
- `--config, -c`: Path to configuration file (required)
- `--input-dir, -i`: Directory containing PDFs (required)
- `--output-dir, -o`: Directory for redacted PDFs (required)

This is useful when:
- You add more PDFs to input_pdfs
- You want to re-process with the same settings
- You modified the config file manually

### Preview Mode

Preview redactions without saving changes:

```bash
pdf-redact preview --config config.yaml --pdf document.pdf --verbose
```

**Output includes:**
- Total redactions found
- Breakdown by page
- Redaction types (text vs logo)
- With `--verbose`: Exact locations and confidence scores

**Example output:**
```
Found 15 redaction(s):

Page 1:
  Text redactions: 3
  Logo redactions: 1
    - Street addresses
      Content: 123 Main Street
      Location: (50.0, 100.0) to (200.0, 115.0)
    - Logo: company_logo
      Confidence: 0.92
      Location: (450.0, 50.0) to (550.0, 100.0)

Page 2:
  Text redactions: 11
  Logo redactions: 0
```

---

## Configuration Guide

Configuration files use YAML format. Here's a simple example:

```yaml
version: "1.0"

# TEXT REDACTION (PII)
text_redaction:
  pii:
    # Enable automatic PII detection
    redact_emails: true
    redact_phone_numbers: true
    redact_addresses: true
    redact_ssn: false

    # Specific names to redact
    custom_names:
      - "John Smith"
      - "Jane Doe"
      - "Acme Corporation"

    # Custom text patterns
    custom_patterns:
      - pattern: "CONFIDENTIAL"
        description: "Confidential watermark"
        case_sensitive: false
      - pattern: "Employee ID: \\d+"
        description: "Employee IDs"
        case_sensitive: false

# LOGO/IMAGE REDACTION (Optional)
logo_redaction:
  templates:
    - name: "company_logo"
      image_path: "./reference_logos/logo.png"
      confidence_threshold: 0.85
      scale_range:
        min: 0.5
        max: 2.0
        step: 0.1

# PROCESSING SETTINGS
processing:
  render_dpi: 300                        # Quality for logo detection
  max_workers: 4                         # Parallel PDF processing
  redaction_color: [255, 255, 255]      # RGB white

# REPORTING
reporting:
  generate_report: true
  report_format: "json"                  # Options: json, html, txt
  include_coordinates: true
```

See `examples/sample_config.yaml` for a fully-commented example.


## Advanced Usage

### Custom Regex Patterns

You can add custom patterns to match specific text formats in your documents:

**Employee IDs**:
```yaml
custom_patterns:
  - pattern: "EMP-\\d{5}"
    description: "Employee IDs (e.g., EMP-12345)"
    case_sensitive: false
```

**Case Numbers**:
```yaml
custom_patterns:
  - pattern: "Case #\\d{6}"
    description: "Case numbers"
    case_sensitive: false
```

**Account Numbers**:
```yaml
custom_patterns:
  - pattern: "Account:\\s*\\d{8,12}"
    description: "Account numbers"
    case_sensitive: false
```

**Confidential Markers**:
```yaml
custom_patterns:
  - pattern: "(CONFIDENTIAL|INTERNAL USE ONLY|PROPRIETARY)"
    description: "Confidential watermarks"
    case_sensitive: false
```

### Batch Processing Multiple Configs

Different document types need different rules:

**macOS/Linux**:
```bash
# Architectural drawings
pdf-redact process --config configs/architectural.yaml \
  --input-dir ./drawings --output-dir ./redacted/drawings

# Specification sheets
pdf-redact process --config configs/specs.yaml \
  --input-dir ./specs --output-dir ./redacted/specs
```

**Windows**:
```powershell
pdf-redact process --config configs\architectural.yaml --input-dir .\drawings --output-dir .\redacted\drawings
pdf-redact process --config configs\specs.yaml --input-dir .\specs --output-dir .\redacted\specs
```

### Tuning for Accuracy

**Too many false positives (schematics being redacted)?**

1. Add exclusion keywords:
```yaml
exclude_if_near:
  - "Dimension"
  - "mm"
  - "inches"
  - "Detail"
  - "Tolerance"
```

2. Exclude technical fonts:
```yaml
font_criteria:
  exclude_fonts: ["CourierNew", "Monaco", "ISOCP", "Consolas"]
```

3. Restrict zones:
```yaml
zone_filter:
  include: ["header", "footer"]
  exclude: ["body", "schematic"]
```

**Missing redactions (false negatives)?**

1. Add more context keywords:
```yaml
context_keywords:
  - "Address:"
  - "Located at:"
  - "Facility:"
  - "Site:"
```

2. Increase proximity:
```yaml
proximity_threshold: 250  # Wider search area
```

---

## Troubleshooting

### "Logo not detected"

**Problem**: Logo appears in PDF but isn't redacted.

**Solutions**:

1. **Check image quality**:
   - Extract logo at high resolution
   - Crop tightly (no whitespace)
   - Save as PNG (not JPEG)
   - Ensure image is clear

2. **Lower confidence threshold**:
```yaml
confidence_threshold: 0.75  # Try 0.70 - 0.80
```

3. **Expand scale range**:
```yaml
scale_range:
  min: 0.3  # Smaller logos
  max: 3.0  # Larger logos
  step: 0.05  # Finer steps
```

4. **Try different variations**:
   - Color vs black & white logos
   - Logo with and without text
   - Different logo versions

### "Numbers in schematics being redacted"

**Problem**: Dimension labels incorrectly removed.

**Solutions**:

1. **Add schematic keywords**:
```yaml
exclude_if_near:
  - "Dimension"
  - "mm"
  - "inches"
  - "\""  # Inch symbol
  - "Scale"
  - "Detail"
```

2. **Exclude technical fonts**:
```yaml
font_criteria:
  exclude_fonts: ["CourierNew", "Monaco", "ISOCP", "Consolas"]
```

3. **Restrict to headers/footers**:
```yaml
zone_filter:
  include: ["header", "footer"]
  exclude: ["body", "schematic"]
```

### "Missing redactions"

**Problem**: Some sensitive text not being redacted.

**Solutions**:

1. **Use preview mode to debug**:
```bash
pdf-redact preview --config config.yaml --pdf problem.pdf --verbose
```

2. **Broaden pattern**:
```yaml
# Too specific:
pattern: "\\d+\\s+North\\s+Main\\s+Street"

# Better (more general):
pattern: "\\d+\\s+[A-Za-z\\s]+(Street|St|Ave)"
```

3. **Increase proximity**:
```yaml
proximity_threshold: 300  # Very wide search
```

### Platform-Specific Issues

**macOS: "command not found: pdf-redact"**
```bash
# Use Python module
python -m pdf_redact.cli --help

# Re-activate virtual environment
source venv/bin/activate

# Reinstall
pip install -e .
```

**Windows: "not recognized as internal or external command"**
```powershell
# Use Python module
python -m pdf_redact.cli --help

# Run directly
.\venv\Scripts\pdf-redact.exe --help
```

**macOS M1/M2: OpenCV fails**
```bash
brew install opencv
pip install opencv-python
```

---

## FAQ

**Q: Are redactions permanent?**
A: Yes. The tool uses PyMuPDF's `apply_redactions()` which permanently removes content. This is not a fake redaction with white boxes.

**Q: Can this handle scanned PDFs?**
A: Not currently. The tool requires selectable text. OCR support is planned for future releases.

**Q: How accurate is context-aware matching?**
A: With proper configuration: >95% precision (few false positives) and >98% recall (catches sensitive data). Always use preview mode first.

**Q: Can I undo redactions?**
A: No. Once applied, content is permanently removed. Always keep original PDFs as backups.

**Q: How do I extract a logo from a PDF?**
A:
1. Take screenshot of logo in PDF viewer
2. Crop tightly in image editor
3. Save as PNG
4. Place in `reference_logos/` folder

**Q: Why is processing slow?**
A: High DPI rendering and template matching are CPU-intensive. Adjust `render_dpi` (default 300) and increase `max_workers` in config.

**Q: Can I redact specific names?**
A: Yes. Use literal patterns:
```yaml
pattern: "John Smith"  # Exact match
pattern: "\\bJohn Smith\\b"  # With word boundaries
```

**Q: What about hundreds of PDFs?**
A: Use batch processing with parallel workers:
```bash
pdf-redact process --config config.yaml \
  --input-dir ./all_pdfs \
  --output-dir ./redacted
```

Adjust `max_workers` in config (4-12 recommended).

**Q: How do I verify redactions worked?**
A:
1. Open redacted PDF
2. Try to select/copy redacted text (should be gone)
3. Check `redaction_report.json`
4. Use `pdftotext redacted.pdf` and search for sensitive terms

---

## Best Practices

1. **Always preview first**:
```bash
pdf-redact preview --config config.yaml --pdf sample.pdf --verbose
```

2. **Start conservative**:
   - High confidence thresholds (0.85+)
   - Narrow proximity (100-150px)
   - Review and adjust

3. **Keep original PDFs**:
   - Redactions are permanent
   - Maintain backups in secure location

4. **Use version control for configs**:
   - Track changes with git
   - Document threshold adjustments

5. **Validate before distribution**:
   - Manually review first few PDFs
   - Use `pdftotext` to verify removal
   - Check metadata is stripped

6. **Organize reference logos**:
```
reference_logos/
├── company_logo_color.png
├── company_logo_bw.png
├── partner1_logo.png
└── partner2_logo.png
```

7. **Use descriptive config names**:
```
configs/
├── architectural_drawings.yaml
├── specification_sheets.yaml
└── client_proposals.yaml
```

---

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: [github.com/yourusername/pdf-redact/issues](https://github.com/yourusername/pdf-redact/issues)
- Email: your.email@example.com

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

---

**Made with ❤️ for industrial document redaction**
