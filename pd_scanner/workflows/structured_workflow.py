"""Structured-data workflow for CSV/JSON/JSONL/Parquet/Excel."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.core.utils import elapsed_seconds, time_now
from pd_scanner.core.workflow_models import WorkflowPreview, WorkflowResult
from pd_scanner.scanner.walker import iter_files
from pd_scanner.workflows.helpers import build_summary_from_results, extraction_preview, write_debug_artifact
from pd_scanner.workflows.single_file_workflow import scan_single_path

STRUCTURED_SUFFIXES = {".csv", ".json", ".jsonl", ".parquet", ".xls", ".xlsx"}


def run_structured_workflow(
    config: AppConfig,
    input_path: str | Path,
    *,
    preview_only: bool = False,
    preview_limit: int = 5,
    tracker: ScanProgressTracker | None = None,
) -> WorkflowResult:
    """Scan only structured files and emit structured previews."""
    started = time_now()
    input_root = Path(input_path).expanduser().resolve()
    files = [input_root] if input_root.is_file() else [
        path for path in iter_files(input_root, config) if path.suffix.lower() in STRUCTURED_SUFFIXES
    ]
    if preview_only:
        files = files[:preview_limit]
    debug_artifact = config.output_path / "debug" / "structured_scan" / "structured_preview.json"
    if tracker is not None:
        tracker.set_stage("discovery")
        tracker.set_total_files(len(files))
        tracker.set_queue_preview(files)
        tracker.register_artifact("Structured debug artifact", debug_artifact)
        mode_label = "preview" if preview_only else "full"
        tracker.log("INFO", f"Queued {len(files)} structured files ({mode_label} mode).")
    results = []
    errors = []
    previews: list[WorkflowPreview] = []
    structured_stats = []
    for path in files:
        if tracker is not None and tracker.should_stop():
            tracker.log("WARNING", "Structured workflow stopping after the current batch.")
            break
        result, extraction = scan_single_path(path, config, tracker=tracker)
        results.append(result)
        if result.status == "error":
            errors.append({"path": result.path, "error_message": result.error_message or "unknown error"})
        if extraction is not None:
            preview = extraction_preview(path, extraction)
            previews.append(preview)
            if tracker is not None:
                tracker.publish_preview(preview.title, preview.items)
            structured_stats.append(
                {
                    "path": str(path),
                    "rows": extraction.metadata.get("total_rows_scanned", 0),
                    "columns": list(extraction.extracted_text_chunks[0].columns[:20]) if extraction.extracted_text_chunks else [],
                    "warnings": extraction.warnings[:5],
                    "column_hints": sorted(
                        {
                            key
                            for chunk in extraction.extracted_text_chunks[:50]
                            for key in chunk.metadata.keys()
                            if key.startswith("column_hint:")
                        }
                    ),
                }
            )
    summary = build_summary_from_results(results, elapsed_seconds(started))
    debug_path = write_debug_artifact(
        config,
        "structured_scan",
        "structured_preview",
        {"stats": structured_stats[:50], "previews": [preview.to_dict() for preview in previews[:10]]},
    )
    return WorkflowResult(
        workflow_type="structured_scan",
        status="cancelled" if tracker is not None and tracker.should_stop() else "completed",
        summary=summary,
        results=results,
        errors=errors,
        previews=previews[:10],
        metadata={
            "structured_stats": structured_stats[:50],
            "debug_artifact": debug_path,
            "preview_only": preview_only,
            "files_scanned": len(results),
        },
    )
