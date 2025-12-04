"""Command-line interface for PDF redaction tool."""

import click
import yaml
from pathlib import Path
from colorama import init, Fore, Style

from pdf_redact.config import RedactionConfig, TextPattern, LogoTemplate, ScaleRange
from pdf_redact.core.pdf_processor import PDFProcessor
from pdf_redact.utils.report_generator import ReportGenerator

# Initialize colorama for cross-platform colored output
init(autoreset=True)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    PDF Redaction Tool - Context-aware redaction for industrial documents.

    Intelligently redacts text and logos from PDFs while preserving
    technical schematics and dimension labels.
    """
    pass


@cli.command()
@click.option(
    '--output',
    '-o',
    default='config.yaml',
    help='Output config file path'
)
def init(output):
    """
    Interactive wizard to create a redaction configuration file.

    Guides you through:
    - Defining text patterns to redact
    - Setting up context keywords
    - Configuring logo templates
    - Tuning detection parameters
    """
    click.echo(Fore.GREEN + "\n" + "="*80)
    click.echo(Fore.GREEN + "PDF Redaction Tool - Configuration Wizard")
    click.echo(Fore.GREEN + "="*80 + "\n")

    click.echo("This wizard will help you create a configuration file for PDF redaction.\n")

    # Create config
    config = RedactionConfig.create_default()

    # Text redaction setup
    if click.confirm("Do you want to configure text redaction?", default=True):
        config.text_redaction.patterns = configure_text_patterns()

    # Logo redaction setup
    if click.confirm("\nDo you want to configure logo redaction?", default=True):
        config.logo_redaction.templates = configure_logo_templates()

    # Processing settings
    if click.confirm("\nDo you want to customize processing settings?", default=False):
        config.processing = configure_processing_settings(config.processing)

    # Save configuration
    try:
        config.to_yaml(output)
        click.echo(Fore.GREEN + f"\n✓ Configuration saved to: {output}")
        click.echo("\nNext steps:")
        click.echo(f"  1. Review and edit {output} as needed")
        click.echo("  2. Place reference logo images in ./reference_logos/")
        click.echo("  3. Run: pdf-redact preview --config config.yaml --pdf sample.pdf")
        click.echo("  4. Run: pdf-redact process --config config.yaml --input-dir ./pdfs --output-dir ./redacted")
    except Exception as e:
        click.echo(Fore.RED + f"\n✗ Error saving configuration: {e}")


@cli.command()
@click.option(
    '--config',
    '-c',
    required=True,
    type=click.Path(exists=True),
    help='Path to configuration file'
)
@click.option(
    '--input-dir',
    '-i',
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Input directory containing PDFs'
)
@click.option(
    '--output-dir',
    '-o',
    required=True,
    type=click.Path(),
    help='Output directory for redacted PDFs'
)
def process(config, input_dir, output_dir):
    """
    Process all PDFs in a directory using the configuration file.

    Applies text and logo redactions to all PDF files found in the input
    directory and saves redacted versions to the output directory.
    """
    try:
        # Load configuration
        click.echo(Fore.CYAN + f"\nLoading configuration from: {config}")
        redaction_config = RedactionConfig.from_yaml(config)

        # Create processor
        processor = PDFProcessor(redaction_config)

        # Process directory
        click.echo(Fore.CYAN + f"Processing PDFs from: {input_dir}")
        click.echo(Fore.CYAN + f"Saving to: {output_dir}\n")

        results = processor.process_directory(input_dir, output_dir)

        # Generate report
        if redaction_config.reporting.generate_report:
            report_gen = ReportGenerator(redaction_config)
            report_gen.generate_report(results, output_dir)

        # Summary
        success_count = sum(1 for r in results.values() if r['success'])
        total_count = len(results)
        total_redactions = sum(r['redaction_count'] for r in results.values())

        click.echo("\n" + Fore.GREEN + "="*80)
        click.echo(Fore.GREEN + "Processing Complete")
        click.echo(Fore.GREEN + "="*80)
        click.echo(f"Files processed: {success_count}/{total_count}")
        click.echo(f"Total redactions: {total_redactions}")

        if success_count < total_count:
            click.echo(Fore.YELLOW + f"\nWarning: {total_count - success_count} file(s) failed")

    except Exception as e:
        click.echo(Fore.RED + f"\n✗ Error: {e}")
        raise click.Abort()


@cli.command()
@click.option(
    '--config',
    '-c',
    required=True,
    type=click.Path(exists=True),
    help='Path to configuration file'
)
@click.option(
    '--pdf',
    '-p',
    required=True,
    type=click.Path(exists=True),
    help='PDF file to preview'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Show detailed information about each redaction'
)
def preview(config, pdf, verbose):
    """
    Preview what would be redacted without actually saving changes.

    Shows a list of all areas that would be redacted, including:
    - Pattern matched
    - Page number
    - Bounding box coordinates
    - Confidence scores
    """
    try:
        # Load configuration
        click.echo(Fore.CYAN + f"\nLoading configuration from: {config}")
        redaction_config = RedactionConfig.from_yaml(config)

        # Create processor
        processor = PDFProcessor(redaction_config)

        # Preview redactions
        click.echo(Fore.CYAN + f"Previewing redactions for: {pdf}\n")

        areas = processor.preview_redactions(pdf)

        # Display results
        if not areas:
            click.echo(Fore.YELLOW + "No redactions found.")
            return

        click.echo(Fore.GREEN + f"Found {len(areas)} redaction(s):\n")

        # Group by page and type
        by_page = {}
        for area in areas:
            page = area.page_number
            if page not in by_page:
                by_page[page] = {"text": [], "logo": []}
            by_page[page][area.redaction_type].append(area)

        # Display
        for page_num in sorted(by_page.keys()):
            page_areas = by_page[page_num]
            text_count = len(page_areas["text"])
            logo_count = len(page_areas["logo"])

            click.echo(Fore.CYAN + f"Page {page_num + 1}:")
            click.echo(f"  Text redactions: {text_count}")
            click.echo(f"  Logo redactions: {logo_count}")

            if verbose:
                # Show details
                for area in page_areas["text"]:
                    click.echo(f"    - {area.matched_pattern}")
                    if area.metadata and "content" in area.metadata:
                        click.echo(f"      Content: {area.metadata['content']}")
                    click.echo(f"      Location: ({area.rect.x0:.1f}, {area.rect.y0:.1f}) to ({area.rect.x1:.1f}, {area.rect.y1:.1f})")

                for area in page_areas["logo"]:
                    click.echo(f"    - Logo: {area.matched_pattern}")
                    click.echo(f"      Confidence: {area.confidence:.2f}")
                    click.echo(f"      Location: ({area.rect.x0:.1f}, {area.rect.y0:.1f}) to ({area.rect.x1:.1f}, {area.rect.y1:.1f})")

            click.echo()

    except Exception as e:
        click.echo(Fore.RED + f"\n✗ Error: {e}")
        raise click.Abort()


def configure_text_patterns():
    """Interactive configuration of text redaction patterns."""
    patterns = []

    click.echo(Fore.CYAN + "\n--- Text Redaction Configuration ---\n")

    while True:
        click.echo("\nCommon patterns:")
        click.echo("  1. Street addresses")
        click.echo("  2. Phone numbers")
        click.echo("  3. Email addresses")
        click.echo("  4. Person names")
        click.echo("  5. Custom pattern")

        choice = click.prompt(
            "Select a pattern type (or press Enter to finish)",
            type=int,
            default=0,
            show_default=False
        )

        if choice == 0:
            break

        pattern = None

        if choice == 1:
            pattern = TextPattern(
                pattern=r"\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)",
                description="Street addresses",
                context_keywords=["Address:", "Location:", "Ship to:", "Bill to:"],
                exclude_if_near=["Dimension", "Drawing", "Scale", "Detail"],
                proximity_threshold=150
            )
        elif choice == 2:
            pattern = TextPattern(
                pattern=r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}",
                description="Phone numbers",
                context_keywords=["Phone:", "Tel:", "Contact:"],
                proximity_threshold=100
            )
        elif choice == 3:
            pattern = TextPattern(
                pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                description="Email addresses",
                context_keywords=["Email:", "Contact:"],
                proximity_threshold=100
            )
        elif choice == 4:
            pattern = TextPattern(
                pattern=r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                description="Person names",
                context_keywords=["Designed by:", "Approved by:", "Engineer:"],
                proximity_threshold=80
            )
        elif choice == 5:
            regex_pattern = click.prompt("Enter regex pattern")
            description = click.prompt("Enter description")
            keywords = click.prompt(
                "Enter context keywords (comma-separated)",
                default=""
            ).split(",")
            keywords = [k.strip() for k in keywords if k.strip()]

            pattern = TextPattern(
                pattern=regex_pattern,
                description=description,
                context_keywords=keywords,
                proximity_threshold=150
            )

        if pattern:
            patterns.append(pattern)
            click.echo(Fore.GREEN + f"✓ Added pattern: {pattern.description}")

    return patterns


def configure_logo_templates():
    """Interactive configuration of logo templates."""
    templates = []

    click.echo(Fore.CYAN + "\n--- Logo Redaction Configuration ---\n")
    click.echo("Place your logo image files in ./reference_logos/ directory")

    while True:
        if not click.confirm("\nAdd a logo template?", default=True if not templates else False):
            break

        name = click.prompt("Template name (e.g., 'company_logo')")
        image_path = click.prompt(
            "Image path",
            default="./reference_logos/logo.png"
        )
        confidence = click.prompt(
            "Confidence threshold (0-1)",
            type=float,
            default=0.85
        )

        template = LogoTemplate(
            name=name,
            image_path=image_path,
            confidence_threshold=confidence,
            scale_range=ScaleRange(min=0.5, max=2.0, step=0.1)
        )

        templates.append(template)
        click.echo(Fore.GREEN + f"✓ Added logo template: {name}")

    return templates


def configure_processing_settings(current_settings):
    """Configure processing settings."""
    click.echo(Fore.CYAN + "\n--- Processing Settings ---\n")

    dpi = click.prompt(
        "Rendering DPI for logo detection (higher = better quality, slower)",
        type=int,
        default=current_settings.render_dpi
    )

    max_workers = click.prompt(
        "Max parallel workers",
        type=int,
        default=current_settings.max_workers
    )

    current_settings.render_dpi = dpi
    current_settings.max_workers = max_workers

    return current_settings


if __name__ == "__main__":
    cli()
