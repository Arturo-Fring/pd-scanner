"""CLI entry for structured workflow."""

from __future__ import annotations

from pd_scanner.core.workflow_models import WorkflowResult
from pd_scanner.workflows.structured_workflow import run_structured_workflow


def run_structured_cli(config, input_path: str) -> WorkflowResult:
    """Run the structured workflow."""
    return run_structured_workflow(config, input_path)
