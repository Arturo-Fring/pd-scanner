"""Masking and sanitization helpers."""

from __future__ import annotations

import re

from pd_scanner.detectors.validators import mask_value


def sanitize_snippet(snippet: str) -> str:
    """Remove or mask risky values from a report snippet."""
    if not snippet:
        return ""
    cleaned = snippet
    cleaned = re.sub(
        r"\b[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]+\.[A-Za-z]{2,24}\b",
        lambda match: mask_value(match.group(0), "email"),
        cleaned,
    )
    cleaned = re.sub(
        r"(?<!\d)(?:\+7|7|8)?[\s\-()]*(?:\d[\s\-()]*){10,11}(?!\d)",
        lambda match: mask_value(match.group(0), "phone"),
        cleaned,
    )
    cleaned = re.sub(
        r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)",
        lambda match: mask_value(match.group(0), "bank_card"),
        cleaned,
    )
    cleaned = re.sub(r"\b\d{6,20}\b", lambda match: "*" * min(len(match.group(0)), 8), cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()

