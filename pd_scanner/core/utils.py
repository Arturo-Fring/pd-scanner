"""Shared utility helpers."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def time_now() -> float:
    """Return a monotonic timestamp."""
    return time.perf_counter()


def elapsed_seconds(start: float) -> float:
    """Return elapsed seconds from a monotonic timestamp."""
    return round(time.perf_counter() - start, 4)


def chunked(iterable: Iterable[Any], size: int) -> Iterable[list[Any]]:
    """Yield fixed-size chunks from an iterable."""
    batch: list[Any] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def flatten_json(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Flatten nested JSON-like structures into key/value pairs."""
    items: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.extend(flatten_json(value, new_prefix))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            new_prefix = f"{prefix}[{index}]"
            items.extend(flatten_json(value, new_prefix))
    else:
        items.append((prefix, data))
    return items


def safe_read_text(path: Path, encoding: str = "utf-8") -> str:
    """Read text with graceful fallback."""
    try:
        return path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def sanitize_whitespace(text: str) -> str:
    """Normalize whitespace in extracted text."""
    return re.sub(r"\s+", " ", text or "").strip()


def safe_json_dump(data: Any, path: Path) -> None:
    """Write JSON with UTF-8 and pretty formatting."""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ensure_directory(path: Path) -> None:
    """Create a directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def shorten(text: str, max_length: int = 160) -> str:
    """Trim text for report snippets."""
    cleaned = sanitize_whitespace(text)
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 3]}..."

