"""RTF extractor."""

from __future__ import annotations

from pathlib import Path

from striprtf.striprtf import rtf_to_text

from pd_scanner.core.models import ExtractedChunk, ExtractionResult
from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor


class RTFExtractor(BaseExtractor):
    """Extract text from RTF files."""

    file_type = "rtf"

    def extract(self, path: Path) -> ExtractionResult:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = sanitize_whitespace(rtf_to_text(raw))
        chunks = [ExtractedChunk(text=text, source_type="rtf_text", source_path=str(path), location={"section": "body"})] if text else []
        return self.build_result(
            chunks=chunks,
            metadata={
                "chunk_count": len(chunks),
                "structured": False,
            },
        )
