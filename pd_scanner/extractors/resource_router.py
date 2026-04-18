"""Composable resource router for multimodal extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import ExtractedChunk
from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.ocr_service import OCRService


@dataclass(slots=True)
class EmbeddedResource:
    """A structural resource extracted from a document before chunk normalization."""

    resource_type: str
    payload: str | Image.Image
    source_type: str
    source_path: str
    location: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class EmbeddedResourceRouter:
    """Route structural resources into normalized chunks."""

    def __init__(self, config: AppConfig, ocr_service: OCRService) -> None:
        self.config = config
        self.ocr_service = ocr_service

    def route(self, resource: EmbeddedResource) -> tuple[list[ExtractedChunk], list[str]]:
        """Normalize a resource into chunks plus warnings."""
        warnings: list[str] = []
        if resource.resource_type in {"text", "link", "metadata"}:
            text = sanitize_whitespace(str(resource.payload))
            if not text:
                return [], warnings
            return [
                ExtractedChunk(
                    text=text,
                    source_type=resource.source_type,
                    source_path=resource.source_path,
                    location=resource.location,
                    metadata=dict(resource.metadata),
                )
            ], warnings

        if resource.resource_type != "image":
            warnings.append(f"Unsupported embedded resource type: {resource.resource_type}")
            return [], warnings

        if self.config.runtime.mode == "fast":
            warnings.append(f"{resource.source_type} skipped: OCR disabled in fast mode.")
            return [], warnings

        available, status = self.ocr_service.get_status()
        if not available:
            warnings.append(f"{resource.source_type} skipped: {status}")
            return [], warnings

        ocr_result = self.ocr_service.extract_text_from_image(resource.payload)
        warnings.extend(ocr_result.warnings)
        text = sanitize_whitespace(ocr_result.text)
        if not text:
            return [], warnings
        return [
            ExtractedChunk(
                text=text,
                source_type=resource.source_type,
                source_path=resource.source_path,
                location=resource.location,
                metadata={
                    **resource.metadata,
                    "ocr": True,
                    "ocr_backend": ocr_result.backend,
                    "ocr_metadata": ocr_result.metadata,
                },
            )
        ], warnings
