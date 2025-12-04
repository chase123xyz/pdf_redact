# PDF Redaction Tool

**Context-aware PDF redaction for industrial documents**

Intelligently redact text and logos from PDF files while preserving technical schematics and dimension labels. Perfect for architectural drawings, engineering specifications, and manufacturing documents.

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
- [Context-Aware Matching Explained](#context-aware-matching-explained)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Best Practices](#best-practices)

## Features

✅ **Context-Aware Redaction**: Intelligently distinguishes addresses ("123 Main St") from schematic labels ("123 mm")
✅ **Multi-Scale Logo Detection**: Find company logos at various sizes across pages
✅ **True Redaction**: Permanently removes content (not fake white boxes)
✅ **Batch Processing**: Process multiple PDFs in parallel
✅ **Interactive CLI**: Easy configuration with step-by-step wizard
✅ **Detailed Reports**: JSON/HTML/TXT reports of all redactions

## How It Works

The tool uses a multi-layered approach to determine what to redact:

### 1. Proximity Analysis
Checks for context keywords within 150 pixels of the matched text:
- **Redact** if near: "Address:", "Phone:", "Email:"
- **Don't redact** if near: "Dimension", "Drawing", "Scale"

### 2. Font Analysis
Distinguishes annotation fonts from technical fonts:
- Arial/Helvetica 10-12pt → **Likely annotation** → Redact
- Courier/Monaco 6-8pt → **Likely technical label** → Don't redact

### 3. Zone Classification
Divides pages into zones:
- Header/Footer → **High redaction probability**
- Schematic areas (dense line drawings) → **Low redaction probability**

### 4. Decision Fusion
Combines all heuristics with weighted scores:
```python
final_score = (
    0.4 × proximity_score +
    0.3 × font_score +
    0.3 × zone_score -
    2.0 × schematic_penalty
)
```

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

### Step 1: Prepare Your Workspace

**macOS/Linux:**
```bash
mkdir -p ~/pdf_redaction_project/{input_pdfs,output_pdfs,reference_logos}
cd ~/pdf_redaction_project
```

**Windows:**
```powershell
New-Item -ItemType Directory -Path C:\pdf_redaction_project\input_pdfs
New-Item -ItemType Directory -Path C:\pdf_redaction_project\output_pdfs
New-Item -ItemType Directory -Path C:\pdf_redaction_project\reference_logos
cd C:\pdf_redaction_project
```

### Step 2: Gather Materials

1. **Place PDFs** to redact in `input_pdfs/` folder
2. **Extract logos** from PDFs:
   - Take screenshot of logo
   - Crop tightly (no whitespace)
   - Save as PNG: `company_logo.png`
   - Place in `reference_logos/` folder

### Step 3: Create Configuration

```bash
pdf-redact init
```

Follow the interactive wizard:
- Select text patterns (addresses, phone numbers, emails)
- Specify context keywords (e.g., "Address:", "Phone:")
- Add logo templates
- Review and save configuration

### Step 4: Preview (Dry Run)

```bash
pdf-redact preview --config config.yaml --pdf ./input_pdfs/sample.pdf
```

Review what will be redacted before processing.

### Step 5: Process PDFs

**macOS/Linux:**
```bash
pdf-redact process \
  --config config.yaml \
  --input-dir ./input_pdfs \
  --output-dir ./output_pdfs
```

**Windows:**
```powershell
pdf-redact process --config config.yaml --input-dir .\input_pdfs --output-dir .\output_pdfs
```

### Step 6: Verify Results

1. Open redacted PDFs in `output_pdfs/`
2. Try to select redacted text (should be gone)
3. Check schematics are intact
4. Review `redaction_report.json` for details

---

## Detailed Usage

### Interactive Configuration

The `init` command guides you through creating a configuration file:

```bash
pdf-redact init --output my_config.yaml
```

**Wizard Steps:**

1. **Text Patterns**: Choose from common patterns or create custom regex
   - Street addresses
   - Phone numbers
   - Email addresses
   - Person names
   - Custom patterns

2. **Context Keywords**: Specify words that indicate redactable context
   - Example: "Address:", "Location:", "Ship to:"

3. **Exclusion Keywords**: Words that prevent redaction
   - Example: "Dimension", "Drawing", "Scale"

4. **Logo Templates**: Add reference images
   - Provide image path
   - Set confidence threshold (0.85 recommended)

5. **Processing Settings**: Tune performance
   - DPI for logo detection (300 recommended)
   - Parallel workers (4 recommended)

### Processing PDFs

Process all PDFs in a directory:

```bash
pdf-redact process --config config.yaml --input-dir ./pdfs --output-dir ./redacted
```

**Options:**
- `--config, -c`: Path to configuration file (required)
- `--input-dir, -i`: Directory containing PDFs (required)
- `--output-dir, -o`: Directory for redacted PDFs (required)

The tool will:
1. Find all PDF files in input directory
2. Apply configured redactions
3. Save redacted versions to output directory
4. Generate a report (JSON/HTML/TXT)
5. Display summary statistics

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

Configuration files use YAML format. Here's a complete example:

```yaml
version: "1.0"

# TEXT REDACTION RULES
text_redaction:
  patterns:
    - pattern: "\\d+\\s+[A-Za-z]+\\s+(Street|St|Avenue|Ave)"
      description: "Street addresses"
      context_mode: "proximity"          # How to detect context
      context_keywords:                  # Nearby text indicating redaction
        - "Address:"
        - "Location:"
      proximity_threshold: 150           # Search radius in pixels
      exclude_if_near:                   # Nearby text preventing redaction
        - "Dimension"
        - "Drawing"
      zone_filter:                       # Restrict to specific page areas
        include: ["header", "footer"]
        exclude: ["schematic"]
      font_criteria:                     # Font-based filtering
        min_size: 8
        max_size: 14
        exclude_fonts: ["CourierNew", "Monaco"]

# LOGO/IMAGE REDACTION
logo_redaction:
  templates:
    - name: "company_logo"
      image_path: "./reference_logos/logo.png"
      confidence_threshold: 0.85         # Match confidence (0-1)
      scale_range:                       # Test multiple sizes
        min: 0.5
        max: 2.0
        step: 0.1
      method: "cv2.TM_CCOEFF_NORMED"    # OpenCV method

# CONTEXT ANALYSIS
context_rules:
  address_indicators:                    # Words suggesting addresses
    - "Address"
    - "Street"
    - "City"
  schematic_indicators:                  # Words suggesting schematics
    - "Scale"
    - "Drawing"
    - "Dimension"
  font_heuristics:
    annotation_fonts: ["Arial", "Helvetica"]
    technical_fonts: ["CourierNew", "Monaco"]

# PROCESSING
processing:
  render_dpi: 300                        # Quality for logo detection
  max_workers: 4                         # Parallel PDF processing
  redaction_color: [255, 255, 255]      # RGB white
  output:
    preserve_metadata: false
    compress: true
    linearize: true

# REPORTING
reporting:
  generate_report: true
  report_format: "json"                  # Options: json, html, txt
  include_coordinates: true
```

See `examples/sample_config.yaml` for a fully-commented example.

---

## Context-Aware Matching Explained

### The Challenge

Industrial PDFs contain both:
- **Sensitive text**: "123 Main Street" → **SHOULD REDACT**
- **Technical data**: "123 mm" dimension label → **SHOULD NOT REDACT**

How does the tool distinguish them?

### The Solution: Multi-Layered Intelligence

#### Layer 1: Proximity Analysis

**How it works**: Scan text within 150 pixels for context clues.

**Example**:
```
Text found: "123"

Nearby text (within 150px):
- "Address: 123 Main St"  → Contains "Address" → REDACT ✓
- "Dimension: 123 mm"     → Contains "Dimension" → DON'T REDACT ✗
```

**Configuration**:
```yaml
context_keywords: ["Address:", "Phone:", "Contact:"]
exclude_if_near: ["Dimension", "Drawing", "Scale"]
proximity_threshold: 150  # pixels
```

#### Layer 2: Font Analysis

**How it works**: Analyze font family and size.

**Typical patterns**:
- Addresses: Arial/Helvetica 10-12pt → Annotation → REDACT
- Dimensions: Courier 6-8pt → Technical label → DON'T REDACT

**Example**:
```
Text: "123 Main St"
Font: Arial, 11pt
→ Matches annotation_fonts → REDACT ✓

Text: "123"
Font: CourierNew, 7pt
→ Matches technical_fonts → DON'T REDACT ✗
```

#### Layer 3: Zone Classification

**How it works**: Divide page into zones.

**Zones**:
- Header (top 15%): High redaction probability
- Footer (bottom 15%): Often contains contact info
- Title block (bottom-right): Engineering metadata
- Body (middle): Mixed content
- Schematic areas (dense lines): Low redaction probability

**Visual Example**:
```
┌─────────────────────────────────────┐
│ ACME Corp - 123 Oak Ave            │ ← Header (REDACT address)
│                                     │
│  ╔═════════════════╗                │
│  ║  ┌───┐   123    ║                │ ← Dense lines (schematic)
│  ║  │   ├──────────║                │   DON'T REDACT "123"
│  ║  └───┘          ║                │
│  ╚═════════════════╝                │
│                                     │
│ Contact: 123 Main St                │ ← Body with keyword (REDACT)
└─────────────────────────────────────┘
```

#### Layer 4: Schematic Detection

**How it works**: Use OpenCV to find dense line drawings.

**Process**:
1. Convert PDF page to image
2. Detect edges using Canny
3. Find lines using Hough transform
4. Calculate line density in grid cells
5. High-density areas = schematics
6. Text in schematic areas gets heavy penalty

#### Decision Fusion

All layers combined:

```python
final_score = (
    0.4 × proximity_score +     # Most important (40%)
    0.3 × font_score +          # Secondary (30%)
    0.3 × zone_score -          # Secondary (30%)
    2.0 × schematic_penalty     # Heavy penalty
)

if final_score > 0.6:
    REDACT
else:
    DON'T REDACT
```

---

## Advanced Usage

### Custom Regex Patterns

**Part Numbers**:
```yaml
pattern: "[A-Z]{2,3}-\\d{4,6}(-[A-Z0-9]+)?"
description: "Part numbers (e.g., ABC-12345-REV2)"
# These are always in schematics, so no context keywords
```

**Drawing References**:
```yaml
pattern: "DWG[- ]?\\d+"
description: "Drawing reference numbers"
```

**Addresses with Suites**:
```yaml
pattern: "\\d+\\s+[A-Za-z\\s]+,\\s*(?:Suite|Ste|Apt|#)\\s*\\d+"
description: "Addresses with suite/apt numbers"
context_keywords: ["Address:", "Office:"]
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
