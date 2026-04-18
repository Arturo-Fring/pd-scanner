"""Detector workflow tests."""

from __future__ import annotations

from pd_scanner.core.config import AppConfig
from pd_scanner.workflows.detector_workflow import run_detector_workflow


def test_detector_only_mode(tmp_path) -> None:
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_detector_workflow(config, text="Email: ivan.petrov@mail.ru")
    assert result.results
    assert result.results[0].category_counts["email"] >= 1


def test_detector_russian_context_keywords_are_not_garbled(tmp_path) -> None:
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_detector_workflow(config, text="Паспорт: 1234 567890\nТелефон: +7 999 123-45-67")

    assert result.results
    counts = result.results[0].category_counts
    assert counts["passport_rf"] >= 1
    assert counts["phone"] >= 1
