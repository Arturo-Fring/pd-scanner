"""Tests for Streamlit background state helpers."""

from __future__ import annotations

import time
from pathlib import Path

from pd_scanner.app import state as app_state_module
from pd_scanner.app.state import BackgroundScanState
from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import FileScanResult
from pd_scanner.core.workflow_models import WorkflowResult


def test_background_state_stop_request(monkeypatch, tmp_path: Path) -> None:
    def fake_pdf_runner(config, tracker=None, **kwargs):
        assert tracker is not None
        tracker.set_total_files(5)
        for index in range(5):
            if tracker.should_stop():
                break
            file_path = tmp_path / f"file_{index}.pdf"
            tracker.on_file_started(file_path)
            time.sleep(0.02)
            tracker.on_file_completed(
                FileScanResult(
                    path=str(file_path),
                    file_type="pdf",
                    status="ok",
                    error_message=None,
                )
            )
        return WorkflowResult(
            workflow_type="pdf_scan",
            status="cancelled" if tracker.should_stop() else "completed",
        )

    monkeypatch.setitem(app_state_module.WORKFLOW_RUNNERS, "pdf_scan", fake_pdf_runner)
    state = BackgroundScanState()
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    state.start("pdf_scan", config, input_path=tmp_path)
    time.sleep(0.05)
    assert state.request_stop() is True
    for _ in range(100):
        if not state.is_running():
            break
        time.sleep(0.02)
    snapshot = state.snapshot()
    assert snapshot is not None
    assert snapshot.status == "cancelled"
    assert snapshot.processed_count >= 1


def test_recent_path_history_is_deduplicated(tmp_path: Path) -> None:
    state = BackgroundScanState()
    input_path = tmp_path / "input"
    output_path = tmp_path / "output"
    input_path.mkdir()
    output_path.mkdir()
    state.remember_paths(input_path, output_path)
    state.remember_paths(input_path, output_path)
    assert state.recent_input_paths == [str(input_path.resolve())]
    assert state.recent_output_paths == [str(output_path.resolve())]
