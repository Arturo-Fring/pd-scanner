"""Shared OCR service used by extractors and embedded-resource routing."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from pd_scanner.core.config import AppConfig
from pd_scanner.extractors.ocr_utils import get_ocr_status, ocr_image


class OCRService:
    """Small service wrapper around local OCR utilities."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def get_status(self) -> tuple[bool, str]:
        """Return OCR availability and a user-facing message."""
        return get_ocr_status(self.config)

    def extract_text(self, image: Image.Image) -> str:
        """Extract OCR text from a PIL image."""
        return ocr_image(image, self.config)

    def extract_bytes(self, image_bytes: bytes) -> str:
        """Extract OCR text from image bytes."""
        with Image.open(io.BytesIO(image_bytes)) as image:
            return self.extract_text(image)

    def extract_path(self, path: str | Path) -> str:
        """Extract OCR text from a file path."""
        with Image.open(Path(path)) as image:
            return self.extract_text(image)
