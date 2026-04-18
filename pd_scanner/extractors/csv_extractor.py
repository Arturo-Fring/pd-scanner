"""CSV extractor with chunked processing."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pd_scanner.core.models import ExtractedChunk, ExtractionResult
from pd_scanner.extractors.base import BaseExtractor


class CSVExtractor(BaseExtractor):
    """Extract text and sample rows from CSV files."""

    file_type = "csv"

    def extract(self, path: Path):
        warnings: list[str] = []
        chunks = []
        sample_rows: list[dict[str, str]] = []
        total_rows = 0
        encodings = ("utf-8", "utf-8-sig", "cp1251", "latin-1")
        last_error: Exception | None = None

        for encoding in encodings:
            try:
                for frame in pd.read_csv(
                    path,
                    chunksize=self.config.runtime.chunksize,
                    dtype=str,
                    keep_default_na=False,
                    encoding=encoding,
                    on_bad_lines="skip",
                ):
                    frame = frame.fillna("")
                    for _, row in frame.iterrows():
                        if total_rows >= self.config.runtime.max_rows_per_structured_file:
                            warnings.append("Structured row limit reached; remaining rows skipped.")
                            raise StopIteration
                        row_dict = {
                            str(column): str(value).strip()
                            for column, value in row.items()
                            if str(value).strip()
                        }
                        if not row_dict:
                            total_rows += 1
                            continue
                        if len(sample_rows) < self.config.runtime.max_table_records_in_memory:
                            sample_rows.append(row_dict)
                        text = " | ".join(f"{column}: {value}" for column, value in row_dict.items())
                        chunks.append(
                            self.make_chunk(
                                text=text,
                                source_type="table_row",
                                row_index=total_rows,
                                columns=tuple(str(column) for column in frame.columns),
                                metadata={"structured": True},
                            )
                        )
                        total_rows += 1
                return self.build_result(
                    chunks=chunks,
                    table_records=sample_rows,
                    metadata={"structured": True, "total_rows_scanned": total_rows, "encoding": encoding},
                    warnings=warnings,
                )
            except StopIteration:
                return self.build_result(
                    chunks=chunks,
                    table_records=sample_rows,
                    metadata={
                        "structured": True,
                        "total_rows_scanned": total_rows,
                        "truncated": True,
                        "encoding": encoding,
                    },
                    warnings=warnings,
                )
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"Unable to parse CSV file: {last_error}") from last_error
