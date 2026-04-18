"""CLI entry for image OCR workflow."""

from __future__ import annotations

from pd_scanner.core.workflow_models import WorkflowResult
from pd_scanner.workflows.image_workflow import run_image_workflow


def run_image_cli(config, input_path: str) -> WorkflowResult:
    """Run the image OCR workflow."""
    return run_image_workflow(config, input_path)
