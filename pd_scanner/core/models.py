"""Dataclasses used across the scanning pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ExtractedChunk:
    """A normalized text fragment extracted from a file."""

    text: str
    source_type: str
    source_path: str | None = None
    location: dict[str, Any] | str | None = None
    row_index: int | None = None
    columns: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def context(self) -> dict[str, Any]:
        """Backward-compatible alias for chunk-level metadata."""
        return self.metadata

    @context.setter
    def context(self, value: dict[str, Any]) -> None:
        """Allow workflows to assign context-style metadata explicitly."""
        self.metadata = value


@dataclass(slots=True)
class ExtractionResult:
    """Extractor output in a format-agnostic representation."""

    file_type: str
    extracted_text_chunks: list[ExtractedChunk] = field(default_factory=list)
    table_records: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RawFinding:
    """A single detector hit before aggregation."""

    entity_type: str
    group: str
    original_value: str
    normalized_value: str
    masked_value: str
    confidence: float
    explanation: str
    source_context: str | None = None
    row_key: str | None = None
    start: int | None = None
    end: int | None = None
    source_detector: str = "rule_based"
    chunk_source_type: str | None = None
    source_path: str | None = None
    validator_passed: bool = False
    context_matched: bool = False


@dataclass(slots=True)
class DetectedEntity:
    """Aggregated entity statistics for a file."""

    entity_type: str
    group: str
    count: int
    masked_examples: list[str]
    confidence: float
    source_context: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GroupFlags:
    """High-level group flags for UZ classification."""

    has_common_pd: bool = False
    has_state_ids: bool = False
    has_payment: bool = False
    has_biometric: bool = False
    has_special: bool = False


@dataclass(slots=True)
class FileScanResult:
    """Scan result for a single file."""

    path: str
    file_type: str
    status: str
    error_message: str | None
    detected_entities: list[DetectedEntity] = field(default_factory=list)
    category_counts: dict[str, int] = field(default_factory=dict)
    group_flags: GroupFlags = field(default_factory=GroupFlags)
    estimated_volume: str = "none"
    volume_metric: int = 0
    uz_level: str = "NO_PD"
    processing_time_sec: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to a JSON-friendly structure."""
        return asdict(self)


@dataclass(slots=True)
class ReportSummary:
    """Aggregated summary across processed files."""

    total_files: int
    processed_files: int
    files_with_pd: int
    files_by_uz: dict[str, int]
    entity_stats: dict[str, int]
    errors_count: int
    unsupported_count: int
    warnings_count: int
    processing_time_total_sec: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize summary to a JSON-friendly structure."""
        return asdict(self)


@dataclass(slots=True)
class ReportArtifacts:
    """Paths to generated scan artifacts."""

    output_dir: str
    csv_report: str
    json_report: str
    markdown_report: str
    summary_report: str
    log_file: str
    state_file: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact paths."""
        return asdict(self)
