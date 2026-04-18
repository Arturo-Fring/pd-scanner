"""Synthetic extractor and fallback tests."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
from PIL import Image

from pd_scanner.core.config import AppConfig
from pd_scanner.extractors.csv_extractor import CSVExtractor
from pd_scanner.extractors.image_ocr_extractor import ImageOCRExtractor
from pd_scanner.extractors.json_extractor import JSONExtractor
from pd_scanner.extractors.pdf_extractor import PDFExtractor


def build_config(tmp_path: Path, mode: str = "fast") -> AppConfig:
    return AppConfig.build(
        input_path=tmp_path,
        output_path=tmp_path / "out",
        mode=mode,
        workers=1,
    )


def test_pdf_extractor_regression_document_closed(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Email: ivan.petrov@mail.ru")
    document.save(pdf_path)
    document.close()

    extractor = PDFExtractor(build_config(tmp_path, mode="fast"))
    result = extractor.extract(pdf_path)

    assert result.file_type == "pdf"
    assert result.metadata["page_count"] == 1
    assert result.extracted_text_chunks


def test_json_extractor_handles_nested_records(tmp_path: Path) -> None:
    json_path = tmp_path / "nested.json"
    payload = [{"user": {"email": "ivan.petrov@mail.ru", "phone": "+7 999 123-45-67"}}]
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    extractor = JSONExtractor(build_config(tmp_path))
    result = extractor.extract(json_path)

    assert result.metadata["structured"] is True
    assert result.metadata["total_rows_scanned"] == 1
    assert "user.email" in result.extracted_text_chunks[0].text


def test_csv_extractor_reads_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("email,phone\nivan.petrov@mail.ru,+79991234567\n", encoding="utf-8")

    extractor = CSVExtractor(build_config(tmp_path))
    result = extractor.extract(csv_path)

    assert result.metadata["structured"] is True
    assert result.metadata["total_rows_scanned"] == 1
    assert result.extracted_text_chunks[0].columns == ("email", "phone")


def test_image_extractor_graceful_fallback_without_ocr(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (40, 40), color="white").save(image_path)
    monkeypatch.setattr(
        "pd_scanner.extractors.ocr_service.OCRService.get_status",
        lambda self: (False, "OCR unavailable for test"),
    )
    extractor = ImageOCRExtractor(build_config(tmp_path, mode="deep"))

    result = extractor.extract(image_path)

    assert not result.extracted_text_chunks
    assert "OCR unavailable for test" in result.warnings[0]
