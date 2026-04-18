"""PDF workflow tests."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.workflows.pdf_workflow import run_pdf_workflow


def test_pdf_workflow_handles_invalid_pdf(tmp_path: Path) -> None:
    invalid_pdf = tmp_path / "broken.pdf"
    invalid_pdf.write_text("not a real pdf", encoding="utf-8")
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_pdf_workflow(config, invalid_pdf)
    assert result.results[0].status == "error"
    assert "Invalid PDF" in (result.results[0].error_message or "")


def test_pdf_workflow_updates_progress_snapshot(tmp_path: Path) -> None:
    invalid_pdf = tmp_path / "broken.pdf"
    invalid_pdf.write_text("not a real pdf", encoding="utf-8")
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    tracker = ScanProgressTracker(tmp_path / "state.json")
    tracker.start(scan_id="pdf-1", workflow_type="pdf_scan")
    result = run_pdf_workflow(config, tmp_path, tracker=tracker)
    tracker.finish("completed")
    snapshot = tracker.snapshot()
    assert result.results
    assert snapshot.total_count == 1
    assert snapshot.queued_files[0].endswith("broken.pdf")
    assert snapshot.recent_results[0]["file_type"] == "pdf"
