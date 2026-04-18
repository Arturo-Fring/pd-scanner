"""OCR helper functions with graceful fallbacks."""

from __future__ import annotations

import logging

from PIL import Image, ImageOps

from pd_scanner.core.config import AppConfig

LOGGER = logging.getLogger(__name__)

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency import guard
    pytesseract = None


def configure_tesseract(config: AppConfig) -> None:
    """Apply explicit Tesseract path if configured."""
    if pytesseract is None:
        return
    if config.ocr.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = config.ocr.tesseract_cmd


def get_ocr_status(config: AppConfig) -> tuple[bool, str]:
    """Return OCR availability and a user-facing message."""
    if not config.ocr.enabled:
        return False, "OCR disabled by current mode."
    if pytesseract is None:
        return False, "pytesseract is not installed."
    configure_tesseract(config)
    try:
        pytesseract.get_tesseract_version()
        return True, f"OCR available ({config.ocr.lang})."
    except Exception as exc:
        return False, f"OCR unavailable: {exc}"


def is_ocr_available(config: AppConfig) -> bool:
    """Return True when OCR can run locally."""
    available, _ = get_ocr_status(config)
    return available


def preprocess_image(image: Image.Image) -> Image.Image:
    """Apply a lightweight OCR-friendly preprocessing pipeline."""
    normalized = ImageOps.exif_transpose(image)
    grayscale = ImageOps.grayscale(normalized)
    grayscale = ImageOps.autocontrast(grayscale)
    return grayscale.point(lambda value: 0 if value < 160 else 255, mode="1")


def ocr_image(image: Image.Image, config: AppConfig) -> str:
    """Run OCR on an image."""
    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed")
    configure_tesseract(config)
    processed = preprocess_image(image)
    return pytesseract.image_to_string(processed, lang=config.ocr.lang)
