"""Generate redaction reports in various formats."""

import json
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

from pdf_redact.config import RedactionConfig
from pdf_redact.core.text_redactor import RedactionArea
from pdf_redact.utils.geometry import rect_to_dict


class ReportGenerator:
    """Generates redaction reports."""

    def __init__(self, config: RedactionConfig):
        """
        Initialize the report generator.

        Args:
            config: Redaction configuration
        """
        self.config = config

    def generate_report(
        self,
        results: Dict[str, Any],
        output_path: str
    ) -> None:
        """
        Generate a redaction report.

        Args:
            results: Processing results dictionary
            output_path: Directory to save report
        """
        if not self.config.reporting.generate_report:
            return

        report_format = self.config.reporting.report_format
        report_filename = self.config.reporting.report_filename

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        if report_format == "json":
            self._generate_json_report(results, output_dir / report_filename)
        elif report_format == "html":
            self._generate_html_report(results, output_dir / "redaction_report.html")
        elif report_format == "txt":
            self._generate_text_report(results, output_dir / "redaction_report.txt")

    def _generate_json_report(self, results: Dict[str, Any], output_file: Path) -> None:
        """Generate JSON format report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self._generate_summary(results),
            "files": []
        }

        for input_file, result in results.items():
            file_report = {
                "input_file": input_file,
                "output_file": result["output"],
                "success": result["success"],
                "error": result["error"],
                "redaction_count": result["redaction_count"],
            }

            # Add redaction details if configured
            if self.config.reporting.include_coordinates and result["redactions"]:
                file_report["redactions"] = [
                    self._redaction_area_to_dict(area)
                    for area in result["redactions"]
                ]

            report["files"].append(file_report)

        # Save JSON
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {output_file}")

    def _generate_text_report(self, results: Dict[str, Any], output_file: Path) -> None:
        """Generate plain text format report."""
        lines = []
        lines.append("PDF Redaction Report")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary
        summary = self._generate_summary(results)
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total files processed: {summary['total_files']}")
        lines.append(f"Successful: {summary['successful']}")
        lines.append(f"Failed: {summary['failed']}")
        lines.append(f"Total redactions: {summary['total_redactions']}")
        lines.append("")

        # Per-file details
        lines.append("FILE DETAILS")
        lines.append("-" * 80)

        for input_file, result in results.items():
            lines.append(f"\nFile: {Path(input_file).name}")
            lines.append(f"  Status: {'SUCCESS' if result['success'] else 'FAILED'}")
            if result['error']:
                lines.append(f"  Error: {result['error']}")
            else:
                lines.append(f"  Output: {result['output']}")
                lines.append(f"  Redactions: {result['redaction_count']}")

                # Group by type
                if result['redactions']:
                    text_count = sum(1 for r in result['redactions'] if r.redaction_type == 'text')
                    logo_count = sum(1 for r in result['redactions'] if r.redaction_type == 'logo')
                    lines.append(f"    - Text: {text_count}")
                    lines.append(f"    - Logos: {logo_count}")

        # Save
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))

        print(f"\nReport saved to: {output_file}")

    def _generate_html_report(self, results: Dict[str, Any], output_file: Path) -> None:
        """Generate HTML format report."""
        summary = self._generate_summary(results)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>PDF Redaction Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
        }}
        .summary {{
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary-item {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .summary-label {{
            font-weight: bold;
            color: #2e7d32;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .success {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .failed {{
            color: #f44336;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>PDF Redaction Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <h2>Summary</h2>
            <div class="summary-item">
                <span class="summary-label">Total Files:</span> {summary['total_files']}
            </div>
            <div class="summary-item">
                <span class="summary-label">Successful:</span> {summary['successful']}
            </div>
            <div class="summary-item">
                <span class="summary-label">Failed:</span> {summary['failed']}
            </div>
            <div class="summary-item">
                <span class="summary-label">Total Redactions:</span> {summary['total_redactions']}
            </div>
        </div>

        <h2>File Details</h2>
        <table>
            <tr>
                <th>Input File</th>
                <th>Status</th>
                <th>Redactions</th>
                <th>Output File</th>
            </tr>
"""

        for input_file, result in results.items():
            status_class = "success" if result['success'] else "failed"
            status_text = "SUCCESS" if result['success'] else "FAILED"
            output_file_name = Path(result['output']).name if result['output'] else "N/A"

            html += f"""
            <tr>
                <td>{Path(input_file).name}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{result['redaction_count']}</td>
                <td>{output_file_name}</td>
            </tr>
"""

        html += """
        </table>
    </div>
</body>
</html>
"""

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"\nReport saved to: {output_file}")

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, int]:
        """Generate summary statistics."""
        total_files = len(results)
        successful = sum(1 for r in results.values() if r['success'])
        failed = total_files - successful
        total_redactions = sum(r['redaction_count'] for r in results.values())

        return {
            "total_files": total_files,
            "successful": successful,
            "failed": failed,
            "total_redactions": total_redactions
        }

    def _redaction_area_to_dict(self, area: RedactionArea) -> dict:
        """Convert RedactionArea to dictionary for serialization."""
        return {
            "page_number": area.page_number,
            "type": area.redaction_type,
            "pattern": area.matched_pattern,
            "confidence": area.confidence,
            "bbox": rect_to_dict(area.rect),
            "metadata": area.metadata
        }
