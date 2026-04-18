"""Estimate the PII volume for a scanned file."""

from __future__ import annotations

from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import ExtractionResult, RawFinding


def estimate_volume(
    extraction: ExtractionResult,
    findings: list[RawFinding],
    config: AppConfig,
) -> tuple[str, int]:
    """Estimate volume label and numeric metric."""
    if not findings:
        return "none", 0

    structured_rows = {
        finding.row_key for finding in findings if finding.row_key and finding.row_key.startswith("row:")
    }
    if extraction.metadata.get("structured"):
        metric = len(structured_rows) or len({finding.normalized_value for finding in findings})
    elif extraction.file_type in {"image", "video"}:
        metric = len(findings)
    else:
        metric = len({finding.normalized_value for finding in findings})
    return config.volume_thresholds.classify(metric), metric

