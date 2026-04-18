"""Map files to extractors."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from pd_scanner.core.config import AppConfig
from pd_scanner.extractors.base import BaseExtractor


EXTRACTOR_BY_SUFFIX: dict[str, tuple[str, str]] = {
    ".csv": ("pd_scanner.extractors.csv_extractor", "CSVExtractor"),
    ".json": ("pd_scanner.extractors.json_extractor", "JSONExtractor"),
    ".jsonl": ("pd_scanner.extractors.json_extractor", "JSONExtractor"),
    ".parquet": ("pd_scanner.extractors.parquet_extractor", "ParquetExtractor"),
    ".xls": ("pd_scanner.extractors.excel_extractor", "ExcelExtractor"),
    ".xlsx": ("pd_scanner.extractors.excel_extractor", "ExcelExtractor"),
    ".pdf": ("pd_scanner.extractors.pdf_extractor", "PDFExtractor"),
    ".docx": ("pd_scanner.extractors.docx_extractor", "DOCXExtractor"),
    ".rtf": ("pd_scanner.extractors.rtf_extractor", "RTFExtractor"),
    ".txt": ("pd_scanner.extractors.txt_extractor", "TXTExtractor"),
    ".doc": ("pd_scanner.extractors.doc_extractor", "DOCExtractor"),
    ".html": ("pd_scanner.extractors.html_extractor", "HTMLExtractor"),
    ".htm": ("pd_scanner.extractors.html_extractor", "HTMLExtractor"),
    ".jpg": ("pd_scanner.extractors.image_ocr_extractor", "ImageOCRExtractor"),
    ".jpeg": ("pd_scanner.extractors.image_ocr_extractor", "ImageOCRExtractor"),
    ".png": ("pd_scanner.extractors.image_ocr_extractor", "ImageOCRExtractor"),
    ".gif": ("pd_scanner.extractors.image_ocr_extractor", "ImageOCRExtractor"),
    ".tif": ("pd_scanner.extractors.image_ocr_extractor", "ImageOCRExtractor"),
    ".tiff": ("pd_scanner.extractors.image_ocr_extractor", "ImageOCRExtractor"),
    ".mp4": ("pd_scanner.extractors.video_extractor", "VideoExtractor"),
}


def get_extractor(path: Path, config: AppConfig) -> BaseExtractor | None:
    """Create an extractor for a given file path."""
    extractor_ref = EXTRACTOR_BY_SUFFIX.get(path.suffix.lower())
    if extractor_ref is None:
        return None
    module_name, class_name = extractor_ref
    try:
        module = import_module(module_name)
        extractor_cls = getattr(module, class_name)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Missing dependency for {path.suffix.lower()} extractor: {exc.name}"
        ) from exc
    return extractor_cls(config)
