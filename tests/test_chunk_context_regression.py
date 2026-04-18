"""Regression coverage for ExtractedChunk context compatibility."""

from __future__ import annotations

from pd_scanner.core.models import ExtractedChunk


def test_extracted_chunk_context_alias_roundtrip() -> None:
    chunk = ExtractedChunk(
        text="value",
        source_type="structured_row",
        metadata={"column_hint:email": True},
    )

    assert chunk.context["column_hint:email"] is True
    chunk.context = {"column_hint:phone": True}
    assert chunk.metadata["column_hint:phone"] is True
