"""Command-line interface for PDF redaction tool."""

import click
import yaml
from pathlib import Path
from colorama import init, Fore, Style

from pdf_redact.config import RedactionConfig, TextPattern, LogoTemplate, ScaleRange, PIIRedactionConfig
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

    Guides you through setting up text and logo redaction.
    """
    from pathlib import Path

    click.echo(Fore.GREEN + "\n" + "="*80)
    click.echo(Fore.GREEN + "PDF Redaction Tool - Setup Wizard")
    click.echo(Fore.GREEN + "="*80 + "\n")

    # Create required folders
    folders = ['input_pdfs', 'output_pdfs', 'reference_logos']
    for folder in folders:
        Path(folder).mkdir(exist_ok=True)

    click.echo(Fore.GREEN + "✓ Created folders: input_pdfs, output_pdfs, reference_logos\n")

    # Setup instructions
    click.echo(Fore.CYAN + "WHERE TO PUT YOUR FILES:")
    click.echo("  • Put your PDF files in the 'input_pdfs' folder")
    click.echo("  • Put logo images (PNG/JPG) in the 'reference_logos' folder")
    click.echo("  • Redacted PDFs will be saved to 'output_pdfs'\n")

    click.pause("Press Enter to continue...")
    click.echo()

    # Create config
    config = RedactionConfig.create_default()

    # Text redaction setup
    click.echo(Fore.CYAN + "--- TEXT REDACTION ---\n")
    config.text_redaction.pii = configure_pii_redaction()

    # Logo redaction setup - auto-detect all images in reference_logos
    click.echo(Fore.CYAN + "\n--- LOGO REDACTION ---\n")
    logo_templates = auto_detect_logos()
    if logo_templates:
        click.echo(f"Found {len(logo_templates)} logo(s) in reference_logos folder:")
        for template in logo_templates:
            click.echo(f"  • {template.name}")
        config.logo_redaction.templates = logo_templates
    else:
        click.echo("No logo images found in reference_logos folder.")

    # Save configuration
    try:
        config.to_yaml(output)
        click.echo()
        click.echo(Fore.GREEN + "="*80)
        click.echo(Fore.GREEN + f"✓ SETUP COMPLETE - Configuration saved to: {output}")
        click.echo(Fore.GREEN + "="*80)
        click.echo()

        click.echo(Fore.CYAN + Style.BRIGHT + "NOW RUN THIS COMMAND TO REDACT YOUR PDFs:")
        click.echo()
        click.echo(Fore.YELLOW + Style.BRIGHT + f"  pdf-redact process --config {output} --input-dir input_pdfs --output-dir output_pdfs")
        click.echo()
        click.echo(Fore.CYAN + "Your redacted PDFs will be saved in the 'output_pdfs' folder.")
        click.echo()
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
        click.echo(Fore.GREEN + "✓ REDACTION COMPLETE")
        click.echo(Fore.GREEN + "="*80)
        click.echo(f"Files processed: {success_count}/{total_count}")
        click.echo(f"Total redactions: {total_redactions}")
        click.echo()
        click.echo(Fore.CYAN + Style.BRIGHT + f"REDACTED PDFs ARE IN: {output_dir}/")
        click.echo(Fore.CYAN + f"(Your original PDFs in {input_dir}/ are unchanged)")
        click.echo()

        if success_count < total_count:
            click.echo(Fore.YELLOW + f"Warning: {total_count - success_count} file(s) failed")

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


def configure_pii_redaction():
    """Interactive configuration of text redaction."""
    click.echo("What text do you want to redact?\n")

    # Simple text/names to redact
    click.echo("Enter text or names to redact (one per line).")
    click.echo("Examples: 'John Smith', 'Acme Corporation', 'CONFIDENTIAL'")
    click.echo("Type 'done' when finished.\n")

    custom_names = []
    custom_patterns = []

    while True:
        text = click.prompt("Text to redact", default="", show_default=False)
        if not text or text.lower() == 'done':
            break
        custom_names.append(text)
        click.echo(Fore.GREEN + f"✓ Will redact: {text}")

    # Ask about common patterns
    redact_emails = False
    redact_phones = False
    redact_addresses = False
    redact_ssn = False

    if custom_names:
        click.echo()

    if click.confirm("\nAlso redact email addresses? (e.g., john@example.com)", default=False):
        redact_emails = True
        click.echo(Fore.GREEN + "✓ Will redact email addresses")

    if click.confirm("Also redact phone numbers? (e.g., 555-123-4567)", default=False):
        redact_phones = True
        click.echo(Fore.GREEN + "✓ Will redact phone numbers")

    if click.confirm("Also redact street addresses? (e.g., 123 Main Street)", default=False):
        redact_addresses = True
        click.echo(Fore.GREEN + "✓ Will redact street addresses")

    return PIIRedactionConfig(
        redact_emails=redact_emails,
        redact_phone_numbers=redact_phones,
        redact_addresses=redact_addresses,
        redact_ssn=redact_ssn,
        custom_names=custom_names,
        custom_patterns=custom_patterns
    )


def auto_detect_logos():
    """Automatically detect all logo images in reference_logos folder."""
    from pathlib import Path

    templates = []
    logo_dir = Path('./reference_logos')

    if not logo_dir.exists():
        return templates

    # Find all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    for ext in image_extensions:
        for image_path in logo_dir.glob(f'*{ext}'):
            template = LogoTemplate(
                name=image_path.stem,
                image_path=str(image_path),
                confidence_threshold=0.85,
                scale_range=ScaleRange(min=0.5, max=2.0, step=0.1)
            )
            templates.append(template)

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
