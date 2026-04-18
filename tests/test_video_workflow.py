"""Video workflow tests."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.workflows.video_workflow import run_video_workflow


def test_video_workflow_empty_dir(tmp_path: Path) -> None:
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_video_workflow(config, tmp_path)
    assert result.summary is not None
    assert result.summary.total_files == 0
