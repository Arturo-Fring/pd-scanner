"""Lifecycle and progress tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pd_scanner.core.lifecycle import LIFECYCLE_MANAGER, ScanAlreadyRunningError
from pd_scanner.core.models import FileScanResult
from pd_scanner.core.services import ScanProgressTracker


def test_single_active_scan_policy(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    scan_id = LIFECYCLE_MANAGER.start("full_scan", state_file)
    try:
        with pytest.raises(ScanAlreadyRunningError):
            LIFECYCLE_MANAGER.start("pdf_scan", state_file)
    finally:
        LIFECYCLE_MANAGER.finish(scan_id)


def test_state_reset_after_completion(tmp_path: Path) -> None:
    tracker = ScanProgressTracker(tmp_path / "scan_state.json")
    tracker.start(scan_id="scan-1", workflow_type="full_scan")
    tracker.set_total_files(2)
    tracker.on_file_completed(
        FileScanResult(path="a.txt", file_type="txt", status="ok", error_message=None)
    )
    tracker.finish("completed")
    snapshot = tracker.snapshot()
    assert snapshot.is_running is False
    assert snapshot.status == "completed"
    assert snapshot.finished_at is not None


def test_tracker_cancellation_sets_cancelled_status(tmp_path: Path) -> None:
    tracker = ScanProgressTracker(tmp_path / "scan_state.json")
    tracker.start(scan_id="scan-3", workflow_type="pdf_scan")
    tracker.request_stop()
    tracker.finish("completed")
    snapshot = tracker.snapshot()
    assert snapshot.is_running is False
    assert snapshot.stop_requested is True
    assert snapshot.status == "cancelled"


def test_aggregated_repeated_warnings(tmp_path: Path) -> None:
    tracker = ScanProgressTracker(tmp_path / "scan_state.json")
    tracker.start(scan_id="scan-2", workflow_type="image_scan")
    for _ in range(3):
        tracker.on_warning("Image OCR skipped in fast mode.", aggregate_key="image_fast_skip", operator_visible=False)
    tracker.finish("completed")
    snapshot = tracker.snapshot()
    assert snapshot.aggregated_warnings["image_fast_skip"] == 3


def test_tracker_keeps_recent_results(tmp_path: Path) -> None:
    tracker = ScanProgressTracker(tmp_path / "scan_state.json")
    tracker.start(scan_id="scan-4", workflow_type="structured_scan")
    tracker.on_file_completed(
        FileScanResult(
            path="table.csv",
            file_type="csv",
            status="ok",
            error_message=None,
            uz_level="UZ-4",
            category_counts={"email": 2},
        )
    )
    snapshot = tracker.snapshot()
    assert snapshot.recent_results
    assert snapshot.recent_results[0]["path"] == "table.csv"
