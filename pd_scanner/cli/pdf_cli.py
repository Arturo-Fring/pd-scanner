"""CLI entry for PDF workflow."""

from __future__ import annotations

from pd_scanner.core.workflow_models import WorkflowResult
from pd_scanner.workflows.pdf_workflow import run_pdf_workflow


def run_pdf_cli(config, input_path: str) -> WorkflowResult:
    """Run the PDF workflow."""
    return run_pdf_workflow(config, input_path)
