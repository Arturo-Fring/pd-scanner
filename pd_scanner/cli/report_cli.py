"""CLI entry for report viewing/building."""

from __future__ import annotations

from pd_scanner.core.workflow_models import WorkflowResult
from pd_scanner.workflows.reporting_workflow import run_reporting_workflow


def run_report_cli(config, output_dir: str) -> WorkflowResult:
    """Run reporting workflow."""
    return run_reporting_workflow(config, output_dir)
