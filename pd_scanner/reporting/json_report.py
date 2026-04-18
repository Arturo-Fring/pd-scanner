"""JSON report generation."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.models import FileScanResult, ReportSummary
from pd_scanner.core.utils import safe_json_dump


def write_json_report(
    path: Path,
    summary: ReportSummary,
    results: list[FileScanResult],
    errors: list[dict[str, str]],
) -> None:
    """Write full structured JSON report."""
    safe_json_dump(
        {
            "summary": summary.to_dict(),
            "files": [result.to_dict() for result in results],
            "errors": errors,
        },
        path,
    )

