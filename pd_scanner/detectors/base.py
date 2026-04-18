"""Base abstractions for composable detector pipelines."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import ExtractedChunk, RawFinding


class BaseDetector(ABC):
    """Interface for chunk-level detectors."""

    name = "base"

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    @abstractmethod
    def detect(self, chunks: list[ExtractedChunk]) -> list[RawFinding]:
        """Detect entities from normalized chunks."""

