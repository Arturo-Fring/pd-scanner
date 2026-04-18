"""RTF extractor."""

from __future__ import annotations

import re
from pathlib import Path

from pd_scanner.core.models import ExtractedChunk, ExtractionResult
from pd_scanner.core.utils import safe_read_text_details, sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor

try:
    from striprtf.striprtf import rtf_to_text
except Exception:  # pragma: no cover - optional dependency import guard
    rtf_to_text = None

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency import guard
    BeautifulSoup = None


class RTFExtractor(BaseExtractor):
    """Extract text from RTF files."""

    file_type = "rtf"

    def extract(self, path: Path) -> ExtractionResult:
        raw, encoding, looks_mojibake = safe_read_text_details(path)
        warnings: list[str] = []
        metadata = {
            "structured": False,
            "encoding": encoding,
        }
        lowered = raw.lstrip().lower()
        source_type = "rtf_text"

        if lowered.startswith("{\\rtf"):
            if rtf_to_text is None:
                warnings.append("Missing dependency for .rtf extractor: striprtf; using raw-text fallback.")
                text = self._fallback_plain_text(raw)
                metadata["fallback_used"] = "raw_text"
            else:
                try:
                    text = sanitize_whitespace(rtf_to_text(raw))
                except Exception as exc:
                    warnings.append(f"RTF parser failed; using raw-text fallback: {exc}")
                    text = self._fallback_plain_text(raw)
                    metadata["fallback_used"] = "raw_text"
        elif self._looks_like_html(lowered):
            warnings.append("File has .rtf extension but content looks like HTML; used HTML-like fallback extraction.")
            text = self._extract_html_like_text(raw)
            source_type = "rtf_html_fallback"
            metadata["fallback_used"] = "html_like"
        else:
            warnings.append("File has .rtf extension but content does not look like valid RTF; used raw-text fallback.")
            text = self._fallback_plain_text(raw)
            source_type = "rtf_raw_fallback"
            metadata["fallback_used"] = "raw_text"

        if looks_mojibake:
            warnings.append("Decoded RTF content still looks suspiciously garbled; review source encoding.")
            metadata["mojibake_suspected"] = True

        chunks = [
            ExtractedChunk(text=text, source_type=source_type, source_path=str(path), location={"section": "body"})
        ] if text else []
        return self.build_result(
            chunks=chunks,
            metadata={**metadata, "chunk_count": len(chunks)},
            warnings=warnings,
        )

    @staticmethod
    def _looks_like_html(text: str) -> bool:
        markers = ("<!doctype", "<html", "<body", "<head", "<div", "<meta", "<title")
        return any(marker in text for marker in markers)

    @staticmethod
    def _extract_html_like_text(text: str) -> str:
        if BeautifulSoup is None:
            return RTFExtractor._fallback_plain_text(text)
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return sanitize_whitespace(soup.get_text(separator=" "))

    @staticmethod
    def _fallback_plain_text(text: str) -> str:
        cleaned = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
        cleaned = cleaned.replace("{", " ").replace("}", " ")
        return sanitize_whitespace(cleaned)
