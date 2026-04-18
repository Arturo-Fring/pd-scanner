"""Best-effort extractor for legacy DOC files."""

from __future__ import annotations

import re
from pathlib import Path

from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor


class DOCExtractor(BaseExtractor):
    """Best-effort binary string extraction for DOC files."""

    file_type = "doc"

    def extract(self, path: Path):
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise RuntimeError(f"Unable to read DOC file: {exc}") from exc
        ascii_parts = re.findall(rb"[\x20-\x7E]{6,}", data)
        utf16_parts = re.findall(rb"(?:[\x20-\x7E]\x00){6,}", data)
        text_parts = [part.decode("latin-1", errors="ignore") for part in ascii_parts]
        text_parts.extend(part.decode("utf-16le", errors="ignore") for part in utf16_parts)
        text = sanitize_whitespace(" ".join(text_parts))
        warnings = ["DOC support is best-effort binary text extraction."]
        return self.build_result(
            chunks=[self.make_chunk(text, source_type="doc_best_effort")] if text else [],
            metadata={"structured": False, "ocr_used": False},
            warnings=warnings,
        )
