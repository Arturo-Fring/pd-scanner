"""Structured workflow tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.extractors.excel_extractor import ExcelExtractor
from pd_scanner.workflows.structured_workflow import run_structured_workflow


def test_structured_workflow_basic_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("email,phone\nivan.petrov@mail.ru,+79991234567\n", encoding="utf-8")
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_structured_workflow(config, tmp_path)
    assert result.summary is not None
    assert result.summary.total_files == 1
    assert result.metadata["structured_stats"][0]["rows"] == 1


def test_xls_engine_selection_graceful_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xls_path = tmp_path / "legacy.xls"
    xls_path.write_bytes(b"fake-xls")
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)

    def raise_import(*args, **kwargs):
        raise ImportError("xlrd missing")

    monkeypatch.setattr(pd, "ExcelFile", raise_import)
    extractor = ExcelExtractor(config)
    with pytest.raises(RuntimeError) as exc:
        extractor.extract(xls_path)
    assert "xlrd" in str(exc.value)


def test_structured_workflow_preview_mode_limits_files(tmp_path: Path) -> None:
    (tmp_path / "a.csv").write_text("email\none@example.com\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("email\ntwo@example.com\n", encoding="utf-8")
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    tracker = ScanProgressTracker(tmp_path / "state.json")
    tracker.start(scan_id="structured-1", workflow_type="structured_scan")
    result = run_structured_workflow(config, tmp_path, preview_only=True, preview_limit=1, tracker=tracker)
    tracker.finish("completed")
    snapshot = tracker.snapshot()
    assert result.summary is not None
    assert result.summary.total_files == 1
    assert result.metadata["preview_only"] is True
    assert snapshot.total_count == 1
    assert len(snapshot.recent_results) == 1
