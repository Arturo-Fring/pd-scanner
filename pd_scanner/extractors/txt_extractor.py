"""Plain-text extractor."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.core.models import ExtractionResult
from pd_scanner.core.utils import safe_read_text_details, sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor


class TXTExtractor(BaseExtractor):
    """Extract text from plain-text files."""

    file_type = "txt"

    def extract(self, path: Path) -> ExtractionResult:
        raw_text, encoding, looks_mojibake = safe_read_text_details(path)
        text = sanitize_whitespace(raw_text)
        chunks = [self.make_chunk(text, source_type="plain_text", source_path=str(path), location={"section": "body"})] if text else []
        warnings = ["TXT content still looks suspiciously garbled after decoding."] if looks_mojibake else []
        return self.build_result(
            chunks=chunks,
            metadata={
                "chunk_count": len(chunks),
                "extractor_name": self.__class__.__name__,
                "encoding": encoding,
                "structured": False,
            },
            warnings=warnings,
        )
