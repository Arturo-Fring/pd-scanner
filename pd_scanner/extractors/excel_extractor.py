"""Excel extractor for XLS/XLSX workbooks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pd_scanner.extractors.base import BaseExtractor


class ExcelExtractor(BaseExtractor):
    """Extract content from all workbook sheets."""

    file_type = "excel"

    def extract(self, path: Path):
        chunks = []
        sample_rows: list[dict[str, str]] = []
        total_rows = 0
        sheet_names: list[str] = []
        engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"

        try:
            workbook = pd.ExcelFile(path, engine=engine)
        except ImportError as exc:
            raise RuntimeError(f"Excel engine '{engine}' is not available for {path.suffix.lower()} files") from exc
        except ValueError as exc:
            raise RuntimeError(f"Unable to open Excel file with engine '{engine}': {exc}") from exc

        with workbook:
            for sheet_name in workbook.sheet_names:
                sheet_names.append(str(sheet_name))
                frame = workbook.parse(sheet_name=sheet_name, dtype=str).fillna("")
                for _, row in frame.iterrows():
                    if total_rows >= self.config.runtime.max_rows_per_structured_file:
                        break
                    row_dict = {
                        str(column): str(value).strip()
                        for column, value in row.items()
                        if str(value).strip()
                    }
                    if not row_dict:
                        total_rows += 1
                        continue
                    if len(sample_rows) < self.config.runtime.max_table_records_in_memory:
                        sample_rows.append({"_sheet": str(sheet_name), **row_dict})
                    chunks.append(
                        self.make_chunk(
                            f"sheet: {sheet_name} | " + " | ".join(f"{column}: {value}" for column, value in row_dict.items()),
                            source_type="table_row",
                            row_index=total_rows,
                            columns=tuple(str(column) for column in frame.columns),
                            metadata={"structured": True, "sheet": str(sheet_name)},
                        )
                    )
                    total_rows += 1
                if total_rows >= self.config.runtime.max_rows_per_structured_file:
                    break

        return self.build_result(
            chunks=chunks,
            table_records=sample_rows,
            metadata={
                "structured": True,
                "total_rows_scanned": total_rows,
                "sheet_names": sheet_names,
                "engine": engine,
                "truncated": total_rows >= self.config.runtime.max_rows_per_structured_file,
            },
        )
