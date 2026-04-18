"""Text-document workflow for DOCX, RTF, and TXT files."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.core.utils import elapsed_seconds, time_now
from pd_scanner.core.workflow_models import WorkflowPreview, WorkflowResult
from pd_scanner.extractors.ocr_service import OCRService
from pd_scanner.scanner.walker import iter_files
from pd_scanner.workflows.helpers import build_summary_from_results, extraction_preview, write_debug_artifact
from pd_scanner.workflows.single_file_workflow import scan_single_path

TEXT_SUFFIXES = {".docx", ".rtf", ".txt"}


def run_text_workflow(
    config: AppConfig,
    input_path: str | Path,
    tracker: ScanProgressTracker | None = None,
) -> WorkflowResult:
    """Scan only text-document formats and emit text-oriented previews."""
    started = time_now()
    input_root = Path(input_path).expanduser().resolve()
    files = [input_root] if input_root.is_file() else [
        path for path in iter_files(input_root, config) if path.suffix.lower() in TEXT_SUFFIXES
    ]
    debug_artifact = config.output_path / "debug" / "text_scan" / "preview.json"
    if tracker is not None:
        tracker.set_stage("discovering files")
        tracker.set_total_files(len(files))
        tracker.set_queue_preview(files)
        tracker.register_artifact("Text debug artifact", debug_artifact)
        tracker.log("INFO", f"Queued {len(files)} text documents.")
        tracker.set_stage("initializing OCR backend")
    available, message = OCRService(config).get_status()
    if tracker is not None:
        tracker.set_stage("checking OCR availability")
        tracker.log("INFO", message)

    results = []
    errors = []
    previews: list[WorkflowPreview] = []
    text_stats = []
    type_counter: Counter[str] = Counter()

    for path in files:
        if tracker is not None and tracker.should_stop():
            tracker.log("WARNING", "Text workflow stopping after the current batch.")
            break
        result, extraction = scan_single_path(path, config, tracker=tracker, stage="processing file")
        results.append(result)
        type_counter[result.file_type] += 1
        if result.status == "error":
            errors.append({"path": result.path, "error_message": result.error_message or "unknown error"})
        if extraction is not None:
            preview = extraction_preview(path, extraction)
            previews.append(preview)
            if tracker is not None:
                tracker.publish_preview(preview.title, preview.items)
            text_stats.append(
                {
                    "path": str(path),
                    "file_type": extraction.file_type,
                    "chunk_count": len(extraction.extracted_text_chunks),
                    "extractor_name": extraction.metadata.get("extractor_name"),
                    "sample_text": extraction.extracted_text_chunks[0].text[:180] if extraction.extracted_text_chunks else "",
                    "warnings": extraction.warnings[:5],
                }
            )
        if tracker is not None and result.warnings:
            tracker.set_stage("continuing with warning")

    summary = build_summary_from_results(results, elapsed_seconds(started))
    debug_path = write_debug_artifact(
        config,
        "text_scan",
        "preview",
        {
            "counts_by_type": dict(sorted(type_counter.items())),
            "stats": text_stats[:50],
            "previews": [preview.to_dict() for preview in previews[:10]],
        },
    )
    return WorkflowResult(
        workflow_type="text_scan",
        status="cancelled" if tracker is not None and tracker.should_stop() else "completed",
        summary=summary,
        results=results,
        errors=errors,
        previews=previews[:10],
        metadata={
            "counts_by_type": dict(sorted(type_counter.items())),
            "text_stats": text_stats[:50],
            "debug_artifact": debug_path,
            "files_scanned": len(results),
            "ocr_available": available,
            "ocr_status": message,
            "ocr_failures": sum(1 for item in results if any("ocr" in warning.lower() for warning in item.warnings)),
        },
    )
