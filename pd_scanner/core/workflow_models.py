"""Workflow-specific models for previews, progress, and reporting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pd_scanner.core.models import FileScanResult, ReportArtifacts, ReportSummary


@dataclass(slots=True)
class WorkflowPreview:
    """Workflow-specific preview payload."""

    title: str
    items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize preview payload."""
        return asdict(self)


@dataclass(slots=True)
class WorkflowResult:
    """Unified result returned by workflow entrypoints."""

    workflow_type: str
    status: str = "completed"
    summary: ReportSummary | None = None
    results: list[FileScanResult] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    artifacts: ReportArtifacts | None = None
    previews: list[WorkflowPreview] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize workflow result."""
        return {
            "workflow_type": self.workflow_type,
            "status": self.status,
            "summary": self.summary.to_dict() if self.summary else None,
            "results": [result.to_dict() for result in self.results],
            "errors": self.errors,
            "artifacts": self.artifacts.to_dict() if self.artifacts else None,
            "previews": [preview.to_dict() for preview in self.previews],
            "metadata": self.metadata,
        }
