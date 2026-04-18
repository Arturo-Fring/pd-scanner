"""Image OCR extractor."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from pd_scanner.core.utils import sanitize_whitespace
from pd_scanner.extractors.base import BaseExtractor


class ImageOCRExtractor(BaseExtractor):
    """Run OCR on supported image formats."""

    file_type = "image"

    def extract(self, path: Path):
        warnings: list[str] = []
        if self.config.runtime.mode == "fast":
            warnings.append("Image OCR skipped in fast mode.")
            return self.build_result(metadata={"ocr_used": False, "structured": False}, warnings=warnings)
        try:
            with Image.open(path) as image:
                ocr_result = self.ocr_service.extract_text_from_image(image)
                warnings.extend(ocr_result.warnings)
                text = sanitize_whitespace(ocr_result.text)
        except UnidentifiedImageError as exc:
            raise RuntimeError(f"Unable to decode image: {exc}") from exc
        return self.build_result(
            chunks=[self.make_chunk(text, source_type="image_ocr", source_path=str(path), location={"image": 1})] if text else [],
            metadata={
                "ocr_used": bool(text),
                "structured": False,
                "ocr_backend": ocr_result.backend,
                "ocr_status": ocr_result.status,
                "ocr_warning_count": len(ocr_result.warnings),
            },
            warnings=warnings,
        )
