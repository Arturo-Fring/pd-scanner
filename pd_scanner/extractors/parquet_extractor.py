"""Parquet extractor."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pd_scanner.core.models import ExtractedChunk, ExtractionResult
from pd_scanner.extractors.base import BaseExtractor


class ParquetExtractor(BaseExtractor):
    """Extract rows from parquet files."""

    file_type = "parquet"

    def extract(self, path: Path) -> ExtractionResult:
        frame = pd.read_parquet(path)
        frame = frame.fillna("").astype(str)
        chunks: list[ExtractedChunk] = []
        sample_rows: list[dict[str, str]] = []
        for index, (_, row) in enumerate(frame.iterrows()):
            if index >= self.config.runtime.max_rows_per_structured_file:
                break
            row_dict = {str(column): str(value).strip() for column, value in row.items() if str(value).strip()}
            if not row_dict:
                continue
            if len(sample_rows) < self.config.runtime.max_table_records_in_memory:
                sample_rows.append(row_dict)
            chunks.append(
                ExtractedChunk(
                    text=" | ".join(f"{column}: {value}" for column, value in row_dict.items()),
                    source_type="table_row",
                    row_index=index,
                    columns=tuple(frame.columns.astype(str)),
                    metadata={"structured": True},
                )
            )
        return ExtractionResult(
            file_type=self.file_type,
            extracted_text_chunks=chunks,
            table_records=sample_rows,
            metadata={"structured": True, "total_rows_scanned": len(chunks)},
        )

