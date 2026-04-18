"""Detector workflow tests."""

from __future__ import annotations

from pd_scanner.core.config import AppConfig
from pd_scanner.workflows.detector_workflow import run_detector_workflow


def test_detector_only_mode(tmp_path) -> None:
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_detector_workflow(config, text="Email: ivan.petrov@mail.ru")
    assert result.results
    assert result.results[0].category_counts["email"] >= 1
