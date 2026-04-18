"""Base extractor interface and convenience helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import ExtractedChunk, ExtractionResult
from pd_scanner.extractors.ocr_service import OCRService
from pd_scanner.extractors.resource_router import EmbeddedResource, EmbeddedResourceRouter, EmbeddedRouteResult


class BaseExtractor(ABC):
    """Abstract file extractor."""

    file_type: str = "unknown"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.ocr_service = OCRService(config)
        self.resource_router = EmbeddedResourceRouter(config, self.ocr_service)

    @abstractmethod
    def extract(self, path: Path) -> ExtractionResult:
        """Extract normalized content from a file."""

    def build_result(
        self,
        *,
        chunks: list[ExtractedChunk] | None = None,
        table_records: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> ExtractionResult:
        """Build a normalized extraction result."""
        return ExtractionResult(
            file_type=self.file_type,
            extracted_text_chunks=chunks or [],
            table_records=table_records or [],
            metadata={"extractor_name": self.__class__.__name__, **(metadata or {})},
            warnings=warnings or [],
        )

    @staticmethod
    def make_chunk(
        text: str,
        *,
        source_type: str,
        source_path: str | None = None,
        location: dict[str, Any] | str | None = None,
        row_index: int | None = None,
        columns: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ExtractedChunk:
        """Construct a normalized text chunk."""
        return ExtractedChunk(
            text=text,
            source_type=source_type,
            source_path=source_path,
            location=location,
            row_index=row_index,
            columns=columns,
            metadata=metadata or {},
        )

    def route_resource(self, resource: EmbeddedResource) -> tuple[list[ExtractedChunk], list[str]]:
        """Route a structural resource through the multimodal router."""
        return self.resource_router.route(resource)

    def route_resource_detailed(self, resource: EmbeddedResource) -> EmbeddedRouteResult:
        """Route a structural resource and keep OCR/runtime details."""
        return self.resource_router.route_detailed(resource)
