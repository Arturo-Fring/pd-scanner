"""JSON and JSONL extractor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pd_scanner.core.utils import flatten_json
from pd_scanner.extractors.base import BaseExtractor

try:
    import ijson
except Exception:  # pragma: no cover - optional dependency import guard
    ijson = None


class JSONExtractor(BaseExtractor):
    """Extract data from JSON and JSONL files."""

    file_type = "json"

    def extract(self, path: Path):
        if path.suffix.lower() == ".jsonl":
            return self._extract_jsonl(path)
        try:
            with path.open("rb") as handle:
                if ijson is not None:
                    try:
                        return self._extract_streaming_json(handle)
                    except Exception:
                        handle.seek(0)
                data = json.load(handle)
            return self._extract_from_object(data)
        except Exception as exc:
            raise RuntimeError(f"Unable to parse JSON: {exc}") from exc

    def _extract_jsonl(self, path: Path):
        chunks = []
        sample_rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        total_rows = 0
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line_number, line in enumerate(handle, start=1):
                if total_rows >= self.config.runtime.max_rows_per_structured_file:
                    warnings.append("Structured row limit reached; remaining JSONL rows skipped.")
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    warnings.append(f"Skipping malformed JSONL line {line_number}: {exc}")
                    continue
                flat = dict(flatten_json(record))
                if len(sample_rows) < self.config.runtime.max_table_records_in_memory:
                    sample_rows.append(flat)
                chunks.append(self._record_to_chunk(flat, total_rows))
                total_rows += 1
        return self.build_result(
            chunks=chunks,
            table_records=sample_rows,
            metadata={"structured": True, "total_rows_scanned": total_rows, "kind": "jsonl"},
            warnings=warnings,
        )

    def _extract_streaming_json(self, handle: Any):
        chunks = []
        sample_rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        total_rows = 0
        objects = ijson.items(handle, "item")
        for record in objects:
            flat = dict(flatten_json(record))
            if len(sample_rows) < self.config.runtime.max_table_records_in_memory:
                sample_rows.append(flat)
            chunks.append(self._record_to_chunk(flat, total_rows))
            total_rows += 1
            if total_rows >= self.config.runtime.max_rows_per_structured_file:
                warnings.append("Structured row limit reached during streaming JSON parsing.")
                break
        if total_rows:
            return self.build_result(
                chunks=chunks,
                table_records=sample_rows,
                metadata={"structured": True, "total_rows_scanned": total_rows, "kind": "json_array"},
                warnings=warnings,
            )
        raise ValueError("Streaming parser did not yield records")

    def _extract_from_object(self, data: Any):
        if isinstance(data, list):
            chunks = []
            sample_rows: list[dict[str, Any]] = []
            for index, item in enumerate(data[: self.config.runtime.max_rows_per_structured_file]):
                flat = dict(flatten_json(item))
                if len(sample_rows) < self.config.runtime.max_table_records_in_memory:
                    sample_rows.append(flat)
                chunks.append(self._record_to_chunk(flat, index))
            return self.build_result(
                chunks=chunks,
                table_records=sample_rows,
                metadata={"structured": True, "total_rows_scanned": len(chunks), "kind": "json_array"},
            )
        flat = dict(flatten_json(data))
        return self.build_result(
            chunks=[self._record_to_chunk(flat, 0)],
            table_records=[flat],
            metadata={"structured": True, "total_rows_scanned": 1, "kind": "json_object"},
        )

    def _record_to_chunk(self, record: dict[str, Any], row_index: int):
        return self.make_chunk(
            " | ".join(f"{key}: {value}" for key, value in record.items()),
            source_type="table_row",
            row_index=row_index,
            columns=tuple(record.keys()),
            metadata={"structured": True},
        )
