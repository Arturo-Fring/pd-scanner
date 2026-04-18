"""CLI tests for text-document workflow wiring."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.cli import main as cli_main
from pd_scanner.core.workflow_models import WorkflowResult


def test_cli_text_scan(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_text_cli(config, input_path: str) -> WorkflowResult:
        captured["input_path"] = input_path
        captured["output_path"] = str(config.output_path)
        return WorkflowResult(workflow_type="text_scan", status="completed")

    monkeypatch.setattr(cli_main, "run_text_cli", fake_run_text_cli)
    exit_code = cli_main.main(
        [
            "text-scan",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path / "out"),
            "--mode",
            "fast",
            "--workers",
            "1",
        ]
    )

    assert exit_code == 0
    assert captured["input_path"] == str(tmp_path)
    assert captured["output_path"] == str((tmp_path / "out").resolve())
