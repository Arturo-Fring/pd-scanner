"""Focused OCR service tests without real backend inference."""

from __future__ import annotations

import sys
import types
from pathlib import Path

from PIL import Image

from pd_scanner.core.config import AppConfig
from pd_scanner.extractors.ocr_service import OCRResult, OCRService, _BackendState


def build_config(tmp_path: Path, mode: str = "deep") -> AppConfig:
    return AppConfig.build(
        input_path=tmp_path,
        output_path=tmp_path / "out",
        mode=mode,
        workers=1,
    )


def clear_ocr_cache() -> None:
    OCRService._backend_cache.clear()
    OCRService._runtime_failure_cache.clear()


def test_ocr_service_reports_disabled_mode(tmp_path: Path) -> None:
    clear_ocr_cache()
    config = build_config(tmp_path, mode="fast")

    service = OCRService(config)
    available, message = service.get_status()

    assert available is False
    assert message == "OCR disabled by current mode."


def test_ocr_service_lazy_initialization_uses_cache(tmp_path: Path, monkeypatch) -> None:
    clear_ocr_cache()
    config = build_config(tmp_path, mode="deep")
    calls: list[str] = []

    def fake_build(self: OCRService, requested_lang: str, cache_key) -> _BackendState:
        calls.append(requested_lang)
        return _BackendState(True, "paddleocr", "OCR available via PaddleOCR (ru).", engine=object(), cache_key=cache_key)

    monkeypatch.setattr(OCRService, "_build_backend_state", fake_build)
    service = OCRService(config)

    first = service.get_status()
    second = service.get_status()

    assert first == second
    assert len(calls) == 1


def test_ocr_service_graceful_unavailable_behavior(tmp_path: Path, monkeypatch) -> None:
    clear_ocr_cache()
    config = build_config(tmp_path, mode="deep")

    monkeypatch.setattr(
        OCRService,
        "_build_backend_state",
        lambda self, requested_lang, cache_key: _BackendState(
            available=False,
            backend_name=None,
            message="OCR backend unavailable for test",
            cache_key=cache_key,
        ),
    )
    service = OCRService(config)

    result = service.extract_text_from_image(Image.new("RGB", (40, 20), color="white"))

    assert result.available is False
    assert result.text == ""
    assert result.warnings == ["OCR backend unavailable for test"]


def test_ocr_service_extract_text_wrapper_returns_normalized_text(tmp_path: Path, monkeypatch) -> None:
    clear_ocr_cache()
    config = build_config(tmp_path, mode="deep")

    monkeypatch.setattr(
        OCRService,
        "extract_text_from_image",
        lambda self, image, lang=None: OCRResult(
            text="wrapped text",
            available=True,
            backend="mock_ocr",
            warnings=[],
            metadata={},
        ),
    )
    service = OCRService(config)

    assert service.extract_text(Image.new("RGB", (20, 20), color="white")) == "wrapped text"


def test_ocr_service_builds_minimal_paddle_init_kwargs(tmp_path: Path, monkeypatch) -> None:
    clear_ocr_cache()
    config = build_config(tmp_path, mode="deep")
    service = OCRService(config)

    monkeypatch.setattr(
        OCRService,
        "_discover_local_paddle_models",
        lambda self, backend_lang: {
            "det_model_dir": "C:/models/det",
            "rec_model_dir": "C:/models/rec",
            "common_model_dirs": ["C:/models/doc_ori", "C:/models/uvdoc", "C:/models/textline_ori"],
        },
    )

    class FakePaddle:
        def __init__(self, lang=None) -> None:
            pass

    plan = service._build_paddle_kwargs(FakePaddle, "rus+eng")

    assert plan.unavailable_message is None
    assert plan.kwargs == {"lang": "ru"}
    assert plan.details["local_models"]["det_model_dir"] == "C:/models/det"
    assert plan.details["local_models"]["rec_model_dir"] == "C:/models/rec"


def test_ocr_service_marks_runtime_failure_and_degrades_backend(tmp_path: Path, monkeypatch) -> None:
    clear_ocr_cache()
    config = build_config(tmp_path, mode="deep")
    config.ocr.backend = "paddleocr"
    init_calls: list[dict[str, object]] = []

    class FakePaddle:
        def __init__(self, **kwargs) -> None:
            init_calls.append(kwargs)

        def ocr(self, payload) -> list[object]:
            raise RuntimeError(
                "ConvertPirAttribute2RuntimeAttribute not support "
                "[pir::ArrayAttribute<pir::DoubleAttribute>]"
            )

    monkeypatch.setitem(sys.modules, "paddleocr", types.SimpleNamespace(PaddleOCR=FakePaddle))
    monkeypatch.setattr(
        OCRService,
        "_discover_local_paddle_models",
        lambda self, backend_lang: {
            "det_model_dir": "C:/models/det",
            "rec_model_dir": "C:/models/rec",
            "common_model_dirs": ["C:/models/doc_ori", "C:/models/uvdoc", "C:/models/textline_ori"],
        },
    )
    monkeypatch.setattr(
        OCRService,
        "_try_init_tesseract_backend",
        lambda self, requested_lang, cache_key: _BackendState(
            available=False,
            backend_name="pytesseract",
            message="pytesseract unavailable for test",
            status="unavailable",
            cache_key=cache_key,
        ),
    )

    service = OCRService(config)
    result = service.extract_text_from_image(Image.new("RGB", (20, 20), color="white"))
    available, message = service.get_status()

    assert result.status == "runtime_failed"
    assert result.warnings == ["PaddleOCR inference runtime failed; OCR disabled for the remaining items."]
    assert available is False
    assert "disabled for the remaining items" in message
    assert len(init_calls) == 1
    assert init_calls[0] == {"lang": "ru"}


def test_ocr_service_offline_mode_does_not_init_paddle_without_local_models(tmp_path: Path, monkeypatch) -> None:
    clear_ocr_cache()
    config = build_config(tmp_path, mode="deep")
    config.ocr.backend = "paddleocr"
    init_calls: list[dict[str, object]] = []

    class FakePaddle:
        def __init__(self, **kwargs) -> None:
            init_calls.append(kwargs)

    monkeypatch.setitem(sys.modules, "paddleocr", types.SimpleNamespace(PaddleOCR=FakePaddle))
    monkeypatch.setattr(OCRService, "_discover_local_paddle_models", lambda self, backend_lang: None)
    monkeypatch.setattr(
        OCRService,
        "_try_init_tesseract_backend",
        lambda self, requested_lang, cache_key: _BackendState(
            available=False,
            backend_name="pytesseract",
            message="pytesseract unavailable for test",
            status="unavailable",
            cache_key=cache_key,
        ),
    )

    service = OCRService(config)
    available, message = service.get_status()

    assert available is False
    assert "offline mode" in message.lower()
    assert init_calls == []
