"""Image OCR workflow."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.core.utils import elapsed_seconds, time_now
from pd_scanner.core.workflow_models import WorkflowPreview, WorkflowResult
from pd_scanner.extractors.ocr_utils import get_ocr_status
from pd_scanner.scanner.walker import iter_files
from pd_scanner.workflows.helpers import build_summary_from_results, extraction_preview, write_debug_artifact
from pd_scanner.workflows.single_file_workflow import scan_single_path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"}


def run_image_workflow(
    config: AppConfig,
    input_path: str | Path,
    tracker: ScanProgressTracker | None = None,
) -> WorkflowResult:
    """Scan only image OCR files."""
    started = time_now()
    input_root = Path(input_path).expanduser().resolve()
    files = [input_root] if input_root.is_file() else [
        path for path in iter_files(input_root, config) if path.suffix.lower() in IMAGE_SUFFIXES
    ]
    debug_artifact = config.output_path / "debug" / "image_scan" / "image_preview.json"
    results = []
    errors = []
    previews: list[WorkflowPreview] = []
    available, message = get_ocr_status(config)
    if tracker is not None:
        tracker.set_stage("discovery")
        tracker.set_total_files(len(files))
        tracker.set_queue_preview(files)
        tracker.register_artifact("Image OCR debug artifact", debug_artifact)
        tracker.log("INFO", f"Queued {len(files)} image files.")
    skipped = 0
    for path in files:
        if tracker is not None and tracker.should_stop():
            tracker.log("WARNING", "Image OCR workflow stopping after the current batch.")
            break
        result, extraction = scan_single_path(path, config, tracker=tracker)
        results.append(result)
        if result.status == "error":
            errors.append({"path": result.path, "error_message": result.error_message or "unknown error"})
        if result.metadata.get("ocr_used") is False and not result.detected_entities:
            skipped += 1
        if extraction is not None:
            preview = extraction_preview(path, extraction)
            previews.append(preview)
            if tracker is not None:
                tracker.publish_preview(preview.title, preview.items)
    summary = build_summary_from_results(results, elapsed_seconds(started))
    debug_path = write_debug_artifact(
        config,
        "image_scan",
        "image_preview",
        {"ocr_available": available, "ocr_status": message, "previews": [preview.to_dict() for preview in previews[:10]]},
    )
    return WorkflowResult(
        workflow_type="image_scan",
        status="cancelled" if tracker is not None and tracker.should_stop() else "completed",
        summary=summary,
        results=results,
        errors=errors,
        previews=previews[:10],
        metadata={"ocr_available": available, "ocr_status": message, "skipped_files": skipped, "debug_artifact": debug_path},
    )
