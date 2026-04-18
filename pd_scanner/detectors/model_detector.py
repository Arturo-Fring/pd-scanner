"""Model-detector placeholder for future ML-based detectors."""

from __future__ import annotations

from pd_scanner.core.models import ExtractedChunk, RawFinding
from pd_scanner.detectors.base import BaseDetector


class ModelDetector(BaseDetector):
    """Stub detector reserved for future Presidio/GLiNER integration."""

    name = "model_stub"

    def detect(self, chunks: list[ExtractedChunk]) -> list[RawFinding]:
        """Return no findings until a model-backed detector is wired in."""
        _ = chunks
        return []

