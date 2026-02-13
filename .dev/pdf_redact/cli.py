"""Command-line interface for PDF redaction tool."""

import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from pdf_redact.config import RedactionConfig, LogoTemplate, ScaleRange, PIIRedactionConfig
from pdf_redact.core.pdf_processor import PDFProcessor
from pdf_redact.utils.report_generator import ReportGenerator

console = Console()

# User-facing folders
INPUT_DIR = '1. original_pdfs'
OUTPUT_DIR = '3. outputs'
LOGO_DIR = '2. logos'

# Hidden program data
DATA_DIR = '.pdf_redact'


@click.command()
@click.version_option(version="1.0.0")
@click.option('--config', '-c', default=None, help='Config file path')
@click.option('--verbose', '-v', is_flag=True, help='Show logo detection debug output')
def main(config, verbose):
    """PDF Redaction Tool - Permanently remove text and logos from PDFs."""
    config_path = config or str(Path(DATA_DIR) / 'config.yaml')

    console.print()
    console.print(Panel(
        "[bold]PDF Redaction Tool[/bold]\n"
        "Permanently remove text, PII, and logos from PDFs",
        border_style="bright_blue",
        padding=(1, 2),
    ))

    # Create required folders
    for folder in [INPUT_DIR, OUTPUT_DIR, LOGO_DIR, DATA_DIR]:
        Path(folder).mkdir(exist_ok=True)

    console.print(f"[green]✓[/green] Ready\n")

    console.print(Panel(
        "[bold]Where to put your files:[/bold]\n\n"
        f"  PDFs to redact       →  [cyan]{INPUT_DIR}/[/cyan]\n"
        f"  Logo images (PNG/JPG) →  [cyan]{LOGO_DIR}/[/cyan]\n"
        f"  Redacted output      →  [cyan]{OUTPUT_DIR}/[/cyan]",
        border_style="dim",
        padding=(1, 2),
    ))

    Prompt.ask("\nPress Enter to continue", default="")
    console.print()

    # Create config
    redaction_config = RedactionConfig.create_default()

    # Text redaction setup
    console.rule("[bold bright_blue]Text Redaction[/bold bright_blue]")
    console.print()
    redaction_config.text_redaction.pii = configure_pii_redaction()

    # Logo redaction setup
    console.print()
    console.rule("[bold bright_blue]Logo Redaction[/bold bright_blue]")
    console.print()
    logo_templates = auto_detect_logos()
    if logo_templates:
        console.print(f"[green]✓[/green] Found {len(logo_templates)} logo(s) in {LOGO_DIR}/:")
        for template in logo_templates:
            console.print(f"  [dim]•[/dim] {template.name}")
        redaction_config.logo_redaction.templates = logo_templates
    else:
        console.print(f"[dim]No logo images found in {LOGO_DIR}/[/dim]")

    # Show config recap
    console.print()
    show_config_recap(redaction_config)

    # Save configuration
    try:
        redaction_config.to_yaml(config_path)
        console.print(f"\n[green]✓[/green] Configuration saved\n")

        # Process PDFs
        console.rule("[bold bright_blue]Processing[/bold bright_blue]")
        console.print()

        processor = PDFProcessor(redaction_config)
        if verbose:
            processor.image_redactor.verbose = True

        results = processor.process_directory(INPUT_DIR, OUTPUT_DIR, console=console)

        # Generate report
        if redaction_config.reporting.generate_report:
            with console.status("[bold]Generating report...[/bold]"):
                report_gen = ReportGenerator(redaction_config, console=console)
                report_gen.generate_report(results, DATA_DIR)

        # Show results
        show_results(results)

    except Exception as e:
        console.print(Panel(
            f"[bold]{e}[/bold]",
            title="Error",
            border_style="red",
            padding=(1, 2),
        ))


def show_config_recap(config: RedactionConfig):
    """Show a table summarizing the configuration."""
    table = Table(title="Configuration Summary", border_style="bright_blue", show_lines=True)
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    pii = config.text_redaction.pii

    # Words
    if pii.custom_names:
        table.add_row("Words to redact", ", ".join(pii.custom_names))
    else:
        table.add_row("Words to redact", "[dim]None[/dim]")

    # Textbox matches
    if pii.custom_textbox_matches:
        table.add_row("Textbox matches", ", ".join(pii.custom_textbox_matches))
    else:
        table.add_row("Textbox matches", "[dim]None[/dim]")

    # PII toggles
    pii_items = []
    if pii.redact_emails:
        pii_items.append("Emails")
    if pii.redact_phone_numbers:
        pii_items.append("Phone numbers")
    if pii.redact_addresses:
        pii_items.append("Addresses")
    if pii.redact_ssn:
        pii_items.append("SSNs")
    table.add_row("PII detection", ", ".join(pii_items) if pii_items else "[dim]None[/dim]")

    # Logos
    templates = config.logo_redaction.templates
    if templates:
        table.add_row("Logos", ", ".join(t.name for t in templates))
    else:
        table.add_row("Logos", "[dim]None[/dim]")

    console.print(table)


def show_results(results: dict):
    """Show a results table and final summary."""
    if not results:
        console.print("[yellow]No PDF files found to process.[/yellow]")
        return

    success_count = sum(1 for r in results.values() if r['success'])
    total_count = len(results)
    total_redactions = sum(r['redaction_count'] for r in results.values())

    # Per-file results table
    console.print()
    table = Table(border_style="bright_blue")
    table.add_column("File", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Redactions", justify="right")
    table.add_column("Audit", justify="center")

    for input_file, result in results.items():
        filename = Path(input_file).name
        if result['success']:
            status = "[green]✓[/green]"
        else:
            status = "[red]✗[/red]"
        audit = "[green]✓[/green]" if result.get('audit_output') else "[dim]—[/dim]"
        table.add_row(filename, status, str(result['redaction_count']), audit)

    console.print(table)

    # Final summary panel
    audit_count = sum(1 for r in results.values() if r.get('audit_output'))

    if success_count < total_count:
        failed = total_count - success_count
        summary_text = (
            f"[bold]Files processed:[/bold] {success_count}/{total_count}\n"
            f"[bold]Total redactions:[/bold] {total_redactions}\n"
            f"[yellow]⚠ {failed} file(s) failed[/yellow]\n\n"
            f"Redacted PDFs are in: [bold cyan]{OUTPUT_DIR}/[/bold cyan]\n"
        )
    else:
        summary_text = (
            f"[bold]Files processed:[/bold] {success_count}/{total_count}\n"
            f"[bold]Total redactions:[/bold] {total_redactions}\n\n"
            f"Redacted PDFs are in: [bold cyan]{OUTPUT_DIR}/[/bold cyan]\n"
        )

    if audit_count:
        summary_text += f"Audit PDFs ({audit_count}): [bold cyan]{OUTPUT_DIR}/*_audit.pdf[/bold cyan]\n"
    summary_text += f"[dim]Your originals in {INPUT_DIR}/ are unchanged[/dim]"

    console.print()
    console.print(Panel(
        summary_text,
        title="[bold green]Done[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()


def configure_pii_redaction():
    """Interactive configuration of text redaction."""
    console.print("What text do you want to redact?\n")

    # Word-level redaction
    console.print("[bold yellow]OPTION 1:[/bold yellow] Redact individual [bold]WORDS[/bold] (precise, word-level redaction)")
    console.print("Enter specific words or names to redact. Only those exact words will be redacted,")
    console.print("not the entire text box they appear in.")
    console.print("[dim]Examples: 'John Smith', 'CONFIDENTIAL', 'Proprietary'[/dim]")
    console.print("[dim]Type 'done' when finished.[/dim]\n")

    custom_names = []
    while True:
        text = Prompt.ask("Word to redact", default="")
        if not text or text.lower() == 'done':
            break
        custom_names.append(text)
        console.print(f"  [green]✓[/green] Will redact word: [bold]{text}[/bold]")

    console.print()

    # Textbox-level redaction
    console.print("[bold yellow]OPTION 2:[/bold yellow] Redact [bold]ENTIRE TEXT BOXES[/bold] containing certain text")
    console.print("Enter text to search for. When found, the ENTIRE text box containing it will be redacted.")
    console.print("[dim]Examples: company names, specific identifiers that should remove surrounding context[/dim]")
    console.print("[dim]Type 'done' when finished.[/dim]\n")

    custom_textbox_matches = []
    while True:
        text = Prompt.ask("Text to find (redacts whole textbox)", default="")
        if not text or text.lower() == 'done':
            break
        custom_textbox_matches.append(text)
        console.print(f"  [green]✓[/green] Will redact entire textbox containing: [bold]{text}[/bold]")

    # PII patterns
    redact_emails = False
    redact_phones = False
    redact_addresses = False
    redact_ssn = False

    console.print()

    if Confirm.ask("Also redact email addresses?", default=False):
        redact_emails = True
        console.print("  [green]✓[/green] Will redact email addresses")

    if Confirm.ask("Also redact phone numbers?", default=False):
        redact_phones = True
        console.print("  [green]✓[/green] Will redact phone numbers")

    if Confirm.ask("Also redact street addresses?", default=False):
        redact_addresses = True
        console.print("  [green]✓[/green] Will redact street addresses")

    return PIIRedactionConfig(
        redact_emails=redact_emails,
        redact_phone_numbers=redact_phones,
        redact_addresses=redact_addresses,
        redact_ssn=redact_ssn,
        custom_names=custom_names,
        custom_textbox_matches=custom_textbox_matches,
        custom_patterns=[]
    )


def auto_detect_logos():
    """Automatically detect all logo images in logos folder."""
    templates = []
    logo_dir = (Path.cwd() / LOGO_DIR).resolve()

    if not logo_dir.exists():
        return templates

    for image_path in logo_dir.iterdir():
        if image_path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            template = LogoTemplate(
                name=image_path.stem,
                image_path=str(image_path.resolve()),
                confidence_threshold=0.65,
                scale_range=ScaleRange(min=0.5, max=3.0, step=0.1)
            )
            templates.append(template)

    return templates


if __name__ == "__main__":
    main()
