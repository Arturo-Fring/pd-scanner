"""Plain-text extractor."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.models import ExtractionResult
from pd_scanner.core.utils import safe_read_text, sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor


class TXTExtractor(BaseExtractor):
    """Extract text from plain-text files."""

    file_type = "txt"

    def extract(self, path: Path) -> ExtractionResult:
        text = sanitize_whitespace(safe_read_text(path))
        chunks = [self.make_chunk(text, source_type="plain_text", source_path=str(path), location={"section": "body"})] if text else []
        return self.build_result(
            chunks=chunks,
            metadata={
                "chunk_count": len(chunks),
                "extractor_name": self.__class__.__name__,
                "structured": False,
            },
        )
