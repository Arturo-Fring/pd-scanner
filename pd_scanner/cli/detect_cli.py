"""CLI entry for detector lab."""

from __future__ import annotations

from pd_scanner.core.workflow_models import WorkflowResult
from pd_scanner.workflows.detector_workflow import run_detector_workflow


def run_detector_cli(config, *, text: str | None = None, text_file: str | None = None) -> WorkflowResult:
    """Run detector lab."""
    return run_detector_workflow(config, text=text, text_file=text_file)
