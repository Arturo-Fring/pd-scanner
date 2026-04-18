"""CLI entry for text-document workflow."""

from __future__ import annotations

from pd_scanner.core.workflow_models import WorkflowResult
from pd_scanner.workflows.text_workflow import run_text_workflow


def run_text_cli(config, input_path: str) -> WorkflowResult:
    """Run the text-document workflow."""
    return run_text_workflow(config, input_path)
