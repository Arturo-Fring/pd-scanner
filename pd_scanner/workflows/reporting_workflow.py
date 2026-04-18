"""Reporting workflow for existing artifacts."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanService
from pd_scanner.core.workflow_models import WorkflowPreview, WorkflowResult


def run_reporting_workflow(config: AppConfig, output_dir: str | Path) -> WorkflowResult:
    """Load and view existing reports/artifacts."""
    payload, artifacts = ScanService.load_scan_results(output_dir)
    if payload is None:
        return WorkflowResult(
            workflow_type="report_build",
            previews=[WorkflowPreview(title="Reports", items=[{"message": "No report artifacts found."}])],
        )
    summary = ScanService.deserialize_summary(payload.get("summary") or {})
    results = [ScanService.deserialize_file_result(item) for item in payload.get("files", [])]
    errors = payload.get("errors", [])
    return WorkflowResult(
        workflow_type="report_build",
        summary=summary,
        results=results,
        errors=errors,
        artifacts=artifacts,
        previews=[WorkflowPreview(title="Report Payload", items=[{"summary": payload.get("summary", {})}])],
    )
