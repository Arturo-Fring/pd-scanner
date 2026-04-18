"""Markdown report generation."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.models import FileScanResult, ReportSummary


def write_markdown_report(
    path: Path,
    summary: ReportSummary,
    results: list[FileScanResult],
    errors: list[dict[str, str]],
) -> None:
    """Write a human-readable Markdown report."""
    top_risky = sorted(
        [result for result in results if result.uz_level.startswith("UZ-")],
        key=lambda result: (result.uz_level, -result.volume_metric, result.path),
    )[:10]
    entity_ranking = sorted(summary.entity_stats.items(), key=lambda item: (-item[1], item[0]))[:10]
    sample_findings: list[str] = []
    for result in results:
        for entity in result.detected_entities[:2]:
            if entity.masked_examples:
                sample_findings.append(
                    f"- `{entity.entity_type}` in `{result.path}`: {', '.join(entity.masked_examples[:2])}"
                )
            if len(sample_findings) >= 10:
                break
        if len(sample_findings) >= 10:
            break

    lines = [
        "# PII Discovery Report",
        "",
        "## Summary",
        f"- Total files discovered: {summary.total_files}",
        f"- Files processed: {summary.processed_files}",
        f"- Files with personal data: {summary.files_with_pd}",
        f"- Errors: {summary.errors_count}",
        f"- Warnings: {summary.warnings_count}",
        f"- Unsupported files: {summary.unsupported_count}",
        f"- Total processing time, sec: {summary.processing_time_total_sec}",
        "",
        "## Distribution by UZ",
    ]
    for uz_level, count in sorted(summary.files_by_uz.items()):
        lines.append(f"- {uz_level}: {count}")

    lines.extend(["", "## Top Categories"])
    for entity_type, count in entity_ranking:
        lines.append(f"- {entity_type}: {count}")

    lines.extend(["", "## Top Risk Files"])
    if top_risky:
        for result in top_risky:
            lines.append(
                f"- `{result.path}` | {result.uz_level} | volume={result.estimated_volume} | "
                f"categories={', '.join(result.category_counts.keys()) or 'none'}"
            )
    else:
        lines.append("- No files with detected personal data.")

    lines.extend(["", "## Sample Masked Findings"])
    lines.extend(sample_findings or ["- No masked findings captured."])

    lines.extend(["", "## Errors"])
    if errors:
        for error in errors[:20]:
            lines.append(f"- `{error['path']}`: {error['error_message']}")
    else:
        lines.append("- No errors.")

    warning_lines: list[str] = []
    for result in results:
        for warning in result.warnings[:3]:
            warning_lines.append(f"- `{result.path}`: {warning}")
        if len(warning_lines) >= 20:
            break

    lines.extend(["", "## Warnings"])
    lines.extend(warning_lines or ["- No warnings."])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
