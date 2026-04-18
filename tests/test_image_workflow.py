"""Image workflow tests."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import ExtractedChunk, ExtractionResult, FileScanResult
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.workflows.image_workflow import run_image_workflow


def test_image_workflow_reports_ocr_unavailable(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (40, 40), color="white").save(image_path)
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="deep", workers=1)
    monkeypatch.setattr(
        "pd_scanner.extractors.ocr_service.OCRService.get_status",
        lambda self: (False, "OCR unavailable for workflow test"),
    )
    result = run_image_workflow(config, image_path)
    assert "ocr_status" in result.metadata
    assert result.metadata["ocr_status"] == "OCR unavailable for workflow test"


def test_image_workflow_publishes_progress_snapshot(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (40, 40), color="white").save(image_path)
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="deep", workers=1)
    tracker = ScanProgressTracker()

    monkeypatch.setattr(
        "pd_scanner.workflows.image_workflow.scan_single_path",
        lambda path, config, tracker=None, stage="processing file": (
            FileScanResult(
                path=str(path),
                file_type="image",
                status="ok",
                error_message=None,
                warnings=["PaddleOCR inference runtime failed; OCR disabled for the remaining items."],
                metadata={"ocr_status": "runtime_failed", "ocr_used": False},
            ),
            ExtractionResult(
                file_type="image",
                extracted_text_chunks=[
                    ExtractedChunk(
                        text="sample chunk",
                        source_type="image_ocr",
                        source_path=str(path),
                    )
                ],
            ),
        ),
    )
    monkeypatch.setattr(
        "pd_scanner.extractors.ocr_service.OCRService.get_status",
        lambda self: (True, "OCR available via PaddleOCR (ru)."),
    )

    run_image_workflow(config, image_path, tracker=tracker)
    snapshot = tracker.snapshot()

    assert snapshot.total_count == 1
    assert snapshot.aggregated_warnings["PaddleOCR inference runtime failed; OCR disabled for the remaining items."] == 1
    assert snapshot.live_previews
    assert snapshot.current_stage == "continuing with warning"
