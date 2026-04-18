"""CLI entry for video workflow."""

from __future__ import annotations

from pd_scanner.core.workflow_models import WorkflowResult
from pd_scanner.workflows.video_workflow import run_video_workflow


def run_video_cli(config, input_path: str) -> WorkflowResult:
    """Run the video workflow."""
    return run_video_workflow(config, input_path)
