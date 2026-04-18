"""Reporting workflow tests."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.core.utils import safe_json_dump
from pd_scanner.workflows.reporting_workflow import run_reporting_workflow


def test_reporting_workflow_loads_existing_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    safe_json_dump(
        {
            "summary": {
                "total_files": 1,
                "processed_files": 1,
                "files_with_pd": 0,
                "files_by_uz": {"NO_PD": 1},
                "entity_stats": {},
                "errors_count": 0,
                "unsupported_count": 0,
                "warnings_count": 0,
                "processing_time_total_sec": 0.1,
            },
            "files": [],
            "errors": [],
        },
        output_dir / "scan_report.json",
    )
    config = AppConfig.build(input_path=output_dir, output_path=output_dir)
    result = run_reporting_workflow(config, output_dir)
    assert result.summary is not None
    assert result.summary.total_files == 1
