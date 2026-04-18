"""Shared helpers for workflow implementations."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import ExtractedChunk, ExtractionResult, FileScanResult, ReportSummary
from pd_scanner.core.utils import ensure_directory, safe_json_dump
from pd_scanner.core.workflow_models import WorkflowPreview


def _display_location(chunk: ExtractedChunk) -> str:
    """Render a chunk location consistently for previews/debug artifacts."""
    if chunk.location:
        if isinstance(chunk.location, str):
            return chunk.location
        return json.dumps(chunk.location, ensure_ascii=False, sort_keys=True)
    if chunk.row_index is not None:
        return f"row:{chunk.row_index}"
    return "n/a"


def build_summary_from_results(results: list[FileScanResult], total_time: float) -> ReportSummary:
    """Build summary for workflow-specific results."""
    uz_counter = Counter(result.uz_level for result in results)
    entity_counter = Counter()
    warnings_count = 0
    for result in results:
        entity_counter.update(result.category_counts)
        warnings_count += len(result.warnings)
    return ReportSummary(
        total_files=len(results),
        processed_files=sum(result.status == "ok" for result in results),
        files_with_pd=sum(result.uz_level != "NO_PD" for result in results),
        files_by_uz=dict(sorted(uz_counter.items())),
        entity_stats=dict(sorted(entity_counter.items())),
        errors_count=sum(result.status == "error" for result in results),
        unsupported_count=sum(result.status == "unsupported" for result in results),
        warnings_count=warnings_count,
        processing_time_total_sec=round(total_time, 4),
    )


def extraction_preview(path: Path, extraction: ExtractionResult) -> WorkflowPreview:
    """Build a compact preview from extraction results."""
    chunk_samples = [
        {
            "location": _display_location(chunk),
            "source_type": chunk.source_type,
            "source_path": chunk.source_path or str(path),
            "text": chunk.text[:240],
            "columns": list(chunk.columns[:10]),
            "metadata": chunk.metadata,
        }
        for chunk in extraction.extracted_text_chunks[:5]
    ]
    return WorkflowPreview(
        title=f"Extraction Preview: {path.name}",
        items=[
            {
                "path": str(path),
                "file_type": extraction.file_type,
                "metadata": extraction.metadata,
                "warnings": extraction.warnings[:10],
                "sample_chunks": chunk_samples,
                "sample_rows": extraction.table_records[:5],
            }
        ],
    )


def write_debug_artifact(
    config: AppConfig,
    workflow_type: str,
    stem: str,
    payload: dict[str, Any],
) -> str:
    """Write workflow debug artifact."""
    debug_dir = config.output_path / "debug" / workflow_type
    ensure_directory(debug_dir)
    path = debug_dir / f"{stem}.json"
    safe_json_dump(payload, path)
    return str(path)
