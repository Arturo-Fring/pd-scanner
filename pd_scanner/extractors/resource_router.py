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


@dataclass(slots=True)
class EmbeddedRouteResult:
    """Detailed routing result for observability and counter accounting."""

    chunks: list[ExtractedChunk] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    attempted_ocr: bool = False
    ocr_text_found: bool = False
    backend: str | None = None
    status: str | None = None
    text_chars: int = 0


class EmbeddedResourceRouter:
    """Route structural resources into normalized chunks."""

    def __init__(self, config: AppConfig, ocr_service: OCRService) -> None:
        self.config = config
        self.ocr_service = ocr_service

    def route(self, resource: EmbeddedResource) -> tuple[list[ExtractedChunk], list[str]]:
        """Normalize a resource into chunks plus warnings."""
        result = self.route_detailed(resource)
        return result.chunks, result.warnings

    def route_detailed(self, resource: EmbeddedResource) -> EmbeddedRouteResult:
        """Normalize a resource and keep OCR/runtime details for callers."""
        warnings: list[str] = []
        if resource.resource_type in {"text", "link", "metadata"}:
            text = sanitize_whitespace(str(resource.payload))
            if not text:
                return EmbeddedRouteResult(warnings=warnings)
            chunk = ExtractedChunk(
                text=text,
                source_type=resource.source_type,
                source_path=resource.source_path,
                location=resource.location,
                metadata=dict(resource.metadata),
            )
            return EmbeddedRouteResult(chunks=[chunk], warnings=warnings, text_chars=len(text))

        if resource.resource_type != "image":
            warnings.append(f"Unsupported embedded resource type: {resource.resource_type}")
            return EmbeddedRouteResult(warnings=warnings, status="unsupported_resource")

        if self.config.runtime.mode == "fast":
            warnings.append(f"{resource.source_type} skipped: OCR disabled in fast mode.")
            return EmbeddedRouteResult(warnings=warnings, status="disabled")

        status_payload = self.ocr_service.get_status_payload()
        if not status_payload["available"]:
            warnings.append(f"{resource.source_type} skipped: {status_payload['message']}")
            return EmbeddedRouteResult(
                warnings=warnings,
                backend=status_payload.get("backend"),
                status=str(status_payload.get("status") or "unavailable"),
            )

        ocr_result = self.ocr_service.extract_text_from_image(resource.payload)
        warnings.extend(ocr_result.warnings)
        text = sanitize_whitespace(ocr_result.text)
        base_result = EmbeddedRouteResult(
            warnings=warnings,
            attempted_ocr=True,
            ocr_text_found=bool(text),
            backend=ocr_result.backend,
            status=ocr_result.status,
            text_chars=len(text),
        )
        if not text:
            return base_result
        chunk = ExtractedChunk(
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
        base_result.chunks = [chunk]
        return base_result
