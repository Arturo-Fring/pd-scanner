"""CSV report generation."""

from __future__ import annotations

import csv
from pathlib import Path

from pd_scanner.core.models import FileScanResult


def write_csv_report(path: Path, results: list[FileScanResult]) -> None:
    """Write a compact CSV report."""
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "path",
                "file_type",
                "status",
                "categories_pd",
                "counts_by_category",
                "uz_level",
                "estimated_volume",
                "processing_time_sec",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "path": result.path,
                    "file_type": result.file_type,
                    "status": result.status,
                    "categories_pd": "; ".join(result.category_counts.keys()),
                    "counts_by_category": "; ".join(
                        f"{category}:{count}" for category, count in result.category_counts.items()
                    ),
                    "uz_level": result.uz_level,
                    "estimated_volume": result.estimated_volume,
                    "processing_time_sec": result.processing_time_sec,
                }
            )

