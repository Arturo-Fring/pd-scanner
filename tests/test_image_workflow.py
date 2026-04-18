"""Image workflow tests."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from pd_scanner.core.config import AppConfig
from pd_scanner.workflows.image_workflow import run_image_workflow


def test_image_workflow_reports_ocr_unavailable(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (40, 40), color="white").save(image_path)
    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="deep", workers=1)
    result = run_image_workflow(config, image_path)
    assert "ocr_status" in result.metadata
