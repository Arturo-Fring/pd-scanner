"""Full recursive scan workflow."""

from __future__ import annotations

from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanProgressTracker, ScanService
from pd_scanner.core.workflow_models import WorkflowResult


def run_full_scan_workflow(config: AppConfig, tracker: ScanProgressTracker | None = None) -> WorkflowResult:
    """Run the full recursive scan workflow."""
    summary, results, errors, artifacts = ScanService.run_scan(
        config,
        tracker=tracker,
        workflow_type="full_scan",
    )
    return WorkflowResult(
        workflow_type="full_scan",
        status="cancelled" if tracker is not None and tracker.should_stop() else "completed",
        summary=summary,
        results=results,
        errors=errors,
        artifacts=artifacts,
        metadata={"mode": config.runtime.mode},
    )
