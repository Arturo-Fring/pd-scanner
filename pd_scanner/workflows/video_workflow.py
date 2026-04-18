"""Video workflow."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.core.utils import elapsed_seconds, time_now
from pd_scanner.core.workflow_models import WorkflowPreview, WorkflowResult
from pd_scanner.extractors.ocr_service import OCRService
from pd_scanner.scanner.walker import iter_files
from pd_scanner.workflows.helpers import build_summary_from_results, extraction_preview, write_debug_artifact
from pd_scanner.workflows.single_file_workflow import scan_single_path


def run_video_workflow(
    config: AppConfig,
    input_path: str | Path,
    tracker: ScanProgressTracker | None = None,
) -> WorkflowResult:
    """Scan only video files."""
    started = time_now()
    input_root = Path(input_path).expanduser().resolve()
    files = [input_root] if input_root.is_file() else [
        path for path in iter_files(input_root, config) if path.suffix.lower() == ".mp4"
    ]
    debug_artifact = config.output_path / "debug" / "video_scan" / "video_preview.json"
    results = []
    errors = []
    previews: list[WorkflowPreview] = []
    ocr_service = OCRService(config)
    if tracker is not None:
        tracker.set_stage("discovering files")
        tracker.set_total_files(len(files))
        tracker.set_queue_preview(files)
        tracker.register_artifact("Video debug artifact", debug_artifact)
        tracker.log("INFO", f"Queued {len(files)} video files.")
        tracker.set_stage("initializing OCR backend")
    status_payload = ocr_service.get_status_payload()
    available = bool(status_payload["available"])
    message = str(status_payload["message"])
    if tracker is not None:
        tracker.set_ocr_runtime(
            backend=status_payload.get("backend"),
            device=status_payload.get("device"),
        )
        tracker.set_stage("checking OCR availability")
        tracker.log("INFO", message)
    for path in files:
        if tracker is not None and tracker.should_stop():
            tracker.log("WARNING", "Video workflow stopping after the current batch.")
            break
        if tracker is not None:
            tracker.set_stage("running OCR")
        result, extraction = scan_single_path(path, config, tracker=tracker, stage="running OCR")
        results.append(result)
        if result.status == "error":
            errors.append({"path": result.path, "error_message": result.error_message or "unknown error"})
        if extraction is not None:
            preview = extraction_preview(path, extraction)
            previews.append(preview)
            if tracker is not None:
                tracker.publish_preview(preview.title, preview.items)
        if tracker is not None and result.warnings:
            tracker.set_stage("continuing with warning")
    summary = build_summary_from_results(results, elapsed_seconds(started))
    debug_path = write_debug_artifact(
        config,
        "video_scan",
        "video_preview",
        {
            "ocr_available": available,
            "ocr_status": message,
            "previews": [preview.to_dict() for preview in previews[:10]],
            "results": [
                {
                    "path": item.path,
                    "status": item.status,
                    "warnings": item.warnings[:5],
                    "sampled_frames": item.metadata.get("sampled_frames"),
                    "ocr_runtime_failed": item.metadata.get("ocr_runtime_failed", False),
                }
                for item in results[:50]
            ],
        },
    )
    return WorkflowResult(
        workflow_type="video_scan",
        status="cancelled" if tracker is not None and tracker.should_stop() else "completed",
        summary=summary,
        results=results,
        errors=errors,
        previews=previews[:10],
        metadata={
            "ocr_available": available,
            "ocr_status": message,
            "ocr_backend": status_payload.get("backend"),
            "ocr_device": status_payload.get("device"),
            "ocr_failures": sum(1 for item in results if item.metadata.get("ocr_runtime_failed")),
            "debug_artifact": debug_path,
        },
    )
