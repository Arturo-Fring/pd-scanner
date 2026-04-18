"""Video workflow tests."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import ExtractionResult, FileScanResult
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.workflows.video_workflow import run_video_workflow


def test_video_workflow_empty_dir(tmp_path: Path) -> None:
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_video_workflow(config, tmp_path)
    assert result.summary is not None
    assert result.summary.total_files == 0


def test_video_workflow_aggregates_ocr_warning_summary(tmp_path: Path, monkeypatch) -> None:
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"not-a-real-video")
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="deep", workers=1)
    tracker = ScanProgressTracker()

    monkeypatch.setattr(
        "pd_scanner.extractors.ocr_service.OCRService.get_status_payload",
        lambda self: {
            "available": True,
            "backend": "easyocr",
            "device": "cuda",
            "status": "ready",
            "message": "OCR available via EasyOCR (ru+en, CUDA).",
            "details": {},
        },
    )
    def fake_scan_single_path(path, config, tracker=None, stage="processing file"):
        warning_a = "PaddleOCR inference runtime failed; OCR disabled for the remaining items."
        warning_b = "Video OCR disabled for remaining frames after backend issue."
        if tracker is not None:
            tracker.on_warning(warning_a, aggregate_key=warning_a, operator_visible=True)
            tracker.on_warning(warning_b, aggregate_key=warning_b, operator_visible=True)
        return (
            FileScanResult(
                path=str(path),
                file_type="mp4",
                status="ok",
                error_message=None,
                warnings=[warning_a, warning_b],
                metadata={"ocr_runtime_failed": True, "sampled_frames": 3},
            ),
            ExtractionResult(file_type="video"),
        )

    monkeypatch.setattr("pd_scanner.workflows.video_workflow.scan_single_path", fake_scan_single_path)

    result = run_video_workflow(config, video_path, tracker=tracker)
    snapshot = tracker.snapshot()

    assert result.metadata["ocr_failures"] == 1
    assert snapshot.aggregated_warnings["PaddleOCR inference runtime failed; OCR disabled for the remaining items."] == 1
    assert snapshot.current_stage == "continuing with warning"
    assert snapshot.ocr_backend == "easyocr"
    assert snapshot.ocr_device == "cuda"
