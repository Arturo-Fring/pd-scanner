"""Unified OCR service with EasyOCR as the primary backend."""

from __future__ import annotations

import inspect
import io
import logging
import os
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from pd_scanner.core.config import AppConfig
from pd_scanner.extractors import ocr_utils

LOGGER = logging.getLogger(__name__)

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency import guard
    np = None


@dataclass(slots=True)
class OCRResult:
    """Normalized OCR output returned by OCRService."""

    text: str
    available: bool
    backend: str | None
    status: str = "ok"
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _BackendState:
    """Cached OCR backend state."""

    available: bool
    backend_name: str | None
    message: str
    engine: Any = None
    status: str = "ready"
    cache_key: tuple[Any, ...] | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _PaddleInitPlan:
    """Initialization plan for PaddleOCR."""

    kwargs: dict[str, Any]
    details: dict[str, Any] = field(default_factory=dict)
    unavailable_message: str | None = None


class OCRService:
    """Single OCR entrypoint shared by extractors, workflows, and UI."""

    _backend_lock = threading.Lock()
    _backend_cache: dict[tuple[Any, ...], _BackendState] = {}
    _runtime_failure_cache: dict[tuple[Any, ...], dict[str, Any]] = {}
    _PADDLE_DETECTION_MODELS: dict[str, str] = {
        "ru": "PP-OCRv5_server_det",
        "en": "PP-OCRv5_server_det",
    }
    _PADDLE_RECOGNITION_MODELS: dict[str, str] = {
        "ru": "eslav_PP-OCRv5_mobile_rec",
        "en": "en_PP-OCRv5_mobile_rec",
    }
    _PADDLE_COMMON_MODELS: tuple[str, ...] = (
        "PP-LCNet_x1_0_doc_ori",
        "UVDoc",
        "PP-LCNet_x1_0_textline_ori",
    )

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def is_available(self) -> bool:
        """Return True when some OCR backend is available for the current config."""
        return self._resolve_backend().available

    def get_backend_name(self) -> str | None:
        """Return the active OCR backend name."""
        return self._resolve_backend().backend_name

    def get_status(self) -> tuple[bool, str]:
        """Return OCR availability plus a short operator-facing explanation."""
        state = self._resolve_backend()
        return state.available, state.message

    def get_status_payload(self) -> dict[str, Any]:
        """Return structured OCR status for GUI and workflow reporting."""
        state = self._resolve_backend()
        return {
            "available": state.available,
            "backend": state.backend_name,
            "device": state.details.get("device"),
            "status": state.status,
            "message": state.message,
            "details": dict(state.details),
        }

    def extract_text_from_image(
        self,
        image: Image.Image | "np.ndarray[Any, Any]" | str | Path | bytes,
        *,
        lang: str | None = None,
    ) -> OCRResult:
        """Run OCR against a supported image input and return normalized output."""
        requested_lang = lang or self.config.ocr.lang
        if not self.config.ocr.enabled:
            return OCRResult(
                text="",
                available=False,
                backend=None,
                status="disabled",
                warnings=["OCR disabled by current mode."],
                metadata={"requested_backend": self.config.ocr.backend, "requested_lang": requested_lang},
            )

        try:
            normalized_image = self._normalize_input(image)
        except Exception as exc:
            return OCRResult(
                text="",
                available=False,
                backend=None,
                status="input_error",
                warnings=[f"OCR input normalization failed: {exc}"],
                metadata={"requested_backend": self.config.ocr.backend, "requested_lang": requested_lang},
            )

        state = self._resolve_backend(lang=requested_lang)
        metadata = {
            "requested_backend": self.config.ocr.backend,
            "requested_lang": requested_lang,
            **state.details,
        }
        if not state.available:
            return OCRResult(
                text="",
                available=False,
                backend=state.backend_name,
                status=state.status,
                warnings=[state.message],
                metadata=metadata,
            )

        try:
            if state.backend_name == "easyocr":
                text, backend_metadata = self._run_easyocr(normalized_image, state, lang=requested_lang)
            elif state.backend_name == "paddleocr":
                text, backend_metadata = self._run_paddle_ocr(normalized_image, state, lang=requested_lang)
            elif state.backend_name == "pytesseract":
                text, backend_metadata = self._run_tesseract_ocr(normalized_image, lang=requested_lang)
            else:
                return OCRResult(
                    text="",
                    available=False,
                    backend=state.backend_name,
                    status=state.status,
                    warnings=[state.message],
                    metadata=metadata,
                )
        except Exception as exc:
            LOGGER.debug("OCR backend %s failed during extraction", state.backend_name, exc_info=True)
            warning_message, status_code, runtime_fatal = self._normalize_backend_error(state.backend_name, exc)
            if state.backend_name in {"easyocr", "paddleocr"} and runtime_fatal:
                self._record_runtime_failure(state, warning_message, exc)
            return OCRResult(
                text="",
                available=True,
                backend=state.backend_name,
                status=status_code,
                warnings=[warning_message],
                metadata={
                    **metadata,
                    "error": str(exc),
                    "runtime_fatal": runtime_fatal,
                },
            )

        return OCRResult(
            text=text,
            available=True,
            backend=state.backend_name,
            status="ok",
            warnings=[],
            metadata={**metadata, **backend_metadata},
        )

    def extract_text(self, image: Image.Image | "np.ndarray[Any, Any]" | str | Path | bytes) -> str:
        """Backward-compatible plain-text OCR API."""
        return self.extract_text_from_image(image).text

    def extract_bytes(self, payload: bytes) -> str:
        """Backward-compatible bytes OCR API."""
        return self.extract_text_from_image(payload).text

    def extract_path(self, path: str | Path) -> str:
        """Backward-compatible path OCR API."""
        return self.extract_text_from_image(path).text

    def _resolve_backend(self, *, lang: str | None = None) -> _BackendState:
        requested_lang = lang or self.config.ocr.lang
        if not self.config.ocr.enabled:
            return _BackendState(
                available=False,
                backend_name=None,
                message="OCR disabled by current mode.",
                status="disabled",
                details={
                    "requested_backend": self.config.ocr.backend,
                    "requested_lang": requested_lang,
                },
            )

        cache_key = (
            (self.config.ocr.backend or "easyocr").lower(),
            requested_lang,
            self.config.ocr.use_angle_cls,
            self.config.ocr.use_gpu,
            self.config.ocr.suppress_backend_logs,
            self.config.ocr.tesseract_cmd,
            self.config.ocr.enabled,
            getattr(self.config.ocr, "offline_only", True),
            getattr(self.config.ocr, "paddle_model_root", None),
        )
        with self._backend_lock:
            cached = self._backend_cache.get(cache_key)
            if cached is not None:
                return cached
        state = self._build_backend_state(requested_lang, cache_key)
        with self._backend_lock:
            self._backend_cache[cache_key] = state
        return state

    def _build_backend_state(self, requested_lang: str, cache_key: tuple[Any, ...]) -> _BackendState:
        requested_backend = (self.config.ocr.backend or "easyocr").lower()
        failures: list[str] = []

        if requested_backend in {"easy", "easyocr", "auto"}:
            easy_state = self._try_init_easyocr_backend(requested_lang, cache_key)
            if easy_state.available:
                return easy_state
            failures.append(easy_state.message)

        if requested_backend in {"paddle", "paddleocr", "auto"}:
            paddle_state = self._try_init_paddle_backend(requested_lang, cache_key)
            if paddle_state.available:
                return paddle_state
            failures.append(paddle_state.message)

        if requested_backend in {"tesseract", "pytesseract", "auto", "easy", "easyocr", "paddle", "paddleocr"}:
            tesseract_state = self._try_init_tesseract_backend(requested_lang, cache_key)
            if tesseract_state.available:
                if failures:
                    tesseract_state.message = (
                        f"OCR available via pytesseract fallback ({requested_lang}). "
                        f"Primary OCR unavailable: {failures[0]}"
                    )
                    tesseract_state.details["fallback_from"] = requested_backend
                return tesseract_state
            failures.append(tesseract_state.message)

        if not failures:
            failures.append(f"Unsupported OCR backend requested: {requested_backend}")
        return _BackendState(
            available=False,
            backend_name=None,
            message=failures[0] if len(failures) == 1 else "; ".join(failures[:2]),
            status="unavailable",
            cache_key=cache_key,
            details={"requested_backend": requested_backend, "requested_lang": requested_lang},
        )

    def _try_init_easyocr_backend(self, requested_lang: str, cache_key: tuple[Any, ...]) -> _BackendState:
        runtime_failure = self._runtime_failure_cache.get(cache_key)
        if runtime_failure is not None:
            return _BackendState(
                available=False,
                backend_name="easyocr",
                message=str(runtime_failure.get("message", "EasyOCR runtime failed.")),
                status="runtime_failed",
                cache_key=cache_key,
                details={
                    "requested_lang": requested_lang,
                    "runtime_failure": runtime_failure,
                    "device": runtime_failure.get("device"),
                },
            )

        try:
            import easyocr
        except Exception as exc:
            LOGGER.info("EasyOCR import failed: %s", exc)
            return _BackendState(
                available=False,
                backend_name="easyocr",
                message=f"EasyOCR unavailable: {exc}",
                status="import_failed",
                cache_key=cache_key,
                details={"requested_lang": requested_lang},
            )

        lang_list = self._map_easyocr_langs(requested_lang)
        device = self._detect_ocr_device()
        init_kwargs = self._build_easyocr_kwargs(easyocr.Reader, device=device)
        try:
            engine = easyocr.Reader(lang_list, **init_kwargs)
        except Exception as exc:
            message = str(exc)
            status = "models_missing" if self._is_easyocr_model_missing_error(message) else "init_failed"
            LOGGER.warning("EasyOCR initialization failed with args=%s: %s", init_kwargs, exc)
            return _BackendState(
                available=False,
                backend_name="easyocr",
                message=f"EasyOCR unavailable: {exc}",
                status=status,
                cache_key=cache_key,
                details={
                    "requested_lang": requested_lang,
                    "backend_langs": lang_list,
                    "device": device,
                    "init_args": dict(init_kwargs),
                },
            )

        LOGGER.info("EasyOCR initialized successfully with langs=%s device=%s args=%s", lang_list, device, init_kwargs)
        return _BackendState(
            available=True,
            backend_name="easyocr",
            message=f"OCR available via EasyOCR ({'+'.join(lang_list)}, {device.upper()}).",
            engine=engine,
            status="ready",
            cache_key=cache_key,
            details={
                "requested_lang": requested_lang,
                "backend_langs": lang_list,
                "device": device,
                "init_args": dict(init_kwargs),
            },
        )

    def _try_init_paddle_backend(self, requested_lang: str, cache_key: tuple[Any, ...]) -> _BackendState:
        runtime_failure = self._runtime_failure_cache.get(cache_key)
        if runtime_failure is not None:
            return _BackendState(
                available=False,
                backend_name="paddleocr",
                message=str(runtime_failure.get("message", "PaddleOCR runtime failed.")),
                status="runtime_failed",
                cache_key=cache_key,
                details={
                    "requested_lang": requested_lang,
                    "runtime_failure": runtime_failure,
                },
            )
        self._prepare_paddle_environment()
        try:
            from paddleocr import PaddleOCR
        except Exception as exc:
            LOGGER.info("PaddleOCR import failed: %s", exc)
            return _BackendState(
                available=False,
                backend_name="paddleocr",
                message=f"PaddleOCR unavailable: {exc}",
                status="import_failed",
                cache_key=cache_key,
                details={"requested_lang": requested_lang},
            )

        init_plan = self._build_paddle_kwargs(PaddleOCR, requested_lang)
        if init_plan.unavailable_message is not None:
            LOGGER.warning("PaddleOCR offline initialization skipped: %s", init_plan.unavailable_message)
            return _BackendState(
                available=False,
                backend_name="paddleocr",
                message=init_plan.unavailable_message,
                status="models_missing",
                cache_key=cache_key,
                details={**init_plan.details, "requested_lang": requested_lang},
            )
        init_kwargs = init_plan.kwargs
        try:
            engine = PaddleOCR(**init_kwargs)
        except Exception as exc:
            LOGGER.warning("PaddleOCR initialization failed with args=%s: %s", init_kwargs, exc)
            return _BackendState(
                available=False,
                backend_name="paddleocr",
                message=f"PaddleOCR unavailable: {exc}",
                status="init_failed",
                cache_key=cache_key,
                details={
                    "requested_lang": requested_lang,
                    "backend_lang": init_kwargs.get("lang", requested_lang),
                    "init_args": dict(init_kwargs),
                    **init_plan.details,
                },
            )

        backend_lang = str(init_kwargs.get("lang", requested_lang))
        LOGGER.info("PaddleOCR initialized successfully with args=%s", init_kwargs)
        return _BackendState(
            available=True,
            backend_name="paddleocr",
            message=f"OCR available via PaddleOCR ({backend_lang}).",
            engine=engine,
            status="ready",
            cache_key=cache_key,
            details={
                "requested_lang": requested_lang,
                "backend_lang": backend_lang,
                "device": "cpu",
                "init_args": dict(init_kwargs),
                **init_plan.details,
            },
        )

    def _try_init_tesseract_backend(self, requested_lang: str, cache_key: tuple[Any, ...]) -> _BackendState:
        pytesseract_module = getattr(ocr_utils, "pytesseract", None)
        if pytesseract_module is None:
            return _BackendState(
                available=False,
                backend_name="pytesseract",
                message="pytesseract is not installed.",
                status="import_failed",
                cache_key=cache_key,
                details={"requested_lang": requested_lang, "device": "cpu"},
            )

        try:
            ocr_utils.configure_tesseract(self.config)
            pytesseract_module.get_tesseract_version()
            return _BackendState(
                available=True,
                backend_name="pytesseract",
                message=f"OCR available via pytesseract ({requested_lang}, CPU).",
                status="ready",
                cache_key=cache_key,
                details={"requested_lang": requested_lang, "device": "cpu"},
            )
        except Exception as exc:
            LOGGER.info("pytesseract availability check failed: %s", exc)
            return _BackendState(
                available=False,
                backend_name="pytesseract",
                message=f"pytesseract unavailable: {exc}",
                status="unavailable",
                cache_key=cache_key,
                details={"requested_lang": requested_lang, "device": "cpu"},
            )

    def _build_easyocr_kwargs(self, reader_cls: type[Any], *, device: str) -> dict[str, Any]:
        """Build minimal offline-safe EasyOCR init kwargs."""
        supported_params = set(inspect.signature(reader_cls.__init__).parameters)
        kwargs: dict[str, Any] = {}
        if "gpu" in supported_params:
            kwargs["gpu"] = device == "cuda"
        if "download_enabled" in supported_params:
            kwargs["download_enabled"] = False
        if "verbose" in supported_params:
            kwargs["verbose"] = not self.config.ocr.suppress_backend_logs
        return kwargs

    def _build_paddle_kwargs(self, paddle_cls: type[Any], requested_lang: str) -> _PaddleInitPlan:
        _ = paddle_cls
        backend_lang = self._map_paddle_lang(requested_lang)
        kwargs: dict[str, Any] = {"lang": backend_lang}
        details: dict[str, Any] = {"backend_lang": backend_lang}

        model_check = self._discover_local_paddle_models(backend_lang)
        if self.config.ocr.offline_only:
            if model_check is None:
                return _PaddleInitPlan(
                    kwargs=kwargs,
                    details=details,
                    unavailable_message=(
                        f"PaddleOCR local models for '{backend_lang}' were not found. "
                        "OCR is unavailable in offline mode."
                    ),
                )
            details["local_models"] = model_check
        elif model_check is not None:
            details["local_models"] = model_check
        LOGGER.info(
            "Resolved PaddleOCR cache for lang=%s: det=%s rec=%s common=%s",
            backend_lang,
            model_check.get("det_model_dir") if model_check else "n/a",
            model_check.get("rec_model_dir") if model_check else "n/a",
            ", ".join(model_check.get("common_model_dirs", [])) if model_check else "n/a",
        )
        return _PaddleInitPlan(kwargs=kwargs, details=details)

    def _run_easyocr(
        self,
        image: Image.Image,
        state: _BackendState,
        *,
        lang: str,
    ) -> tuple[str, dict[str, Any]]:
        if np is None:
            raise RuntimeError("numpy is required for EasyOCR input normalization")
        if state.engine is None:
            raise RuntimeError("EasyOCR backend was not initialized")

        payload = np.array(ImageOps.exif_transpose(image).convert("RGB"))
        raw = state.engine.readtext(payload, detail=0)
        lines = self._parse_easyocr_output(raw)
        text = "\n".join(lines).strip()
        return text, {
            "backend": "easyocr",
            "line_count": len(lines),
            "requested_lang": lang,
            "device": state.details.get("device"),
        }

    def _run_paddle_ocr(
        self,
        image: Image.Image,
        state: _BackendState,
        *,
        lang: str,
    ) -> tuple[str, dict[str, Any]]:
        if np is None:
            raise RuntimeError("numpy is required for PaddleOCR input normalization")
        if state.engine is None:
            raise RuntimeError("PaddleOCR backend was not initialized")

        prepared = self._prepare_image_for_paddle(image)
        payload = np.array(prepared.convert("RGB"))
        if getattr(payload, "ndim", 0) == 3:
            payload = payload[:, :, ::-1]
        raw = state.engine.ocr(payload)

        lines, scores = self._parse_paddle_output(raw)
        text = "\n".join(lines).strip()
        metadata: dict[str, Any] = {
            "backend": "paddleocr",
            "line_count": len(lines),
            "requested_lang": lang,
            "device": state.details.get("device", "cpu"),
        }
        if scores:
            metadata["avg_confidence"] = round(sum(scores) / len(scores), 4)
        return text, metadata

    def _run_tesseract_ocr(self, image: Image.Image, *, lang: str) -> tuple[str, dict[str, Any]]:
        text = ocr_utils.ocr_image(image, self.config, lang=lang)
        return text, {"backend": "pytesseract", "requested_lang": lang, "device": "cpu"}

    @staticmethod
    def _prepare_image_for_paddle(image: Image.Image) -> Image.Image:
        normalized = ImageOps.exif_transpose(image)
        normalized = normalized.convert("RGB")
        return ImageOps.autocontrast(normalized)

    def _normalize_input(
        self,
        image: Image.Image | "np.ndarray[Any, Any]" | str | Path | bytes,
    ) -> Image.Image:
        if isinstance(image, Image.Image):
            return ImageOps.exif_transpose(image.copy())

        if isinstance(image, (str, Path)):
            with Image.open(image) as opened:
                return ImageOps.exif_transpose(opened.copy())

        if isinstance(image, bytes):
            with Image.open(io.BytesIO(image)) as opened:
                return ImageOps.exif_transpose(opened.copy())

        if np is not None and isinstance(image, np.ndarray):
            if image.ndim == 2:
                pil_image = Image.fromarray(image)
            elif image.ndim == 3 and image.shape[2] == 3:
                pil_image = Image.fromarray(image[:, :, ::-1])
            elif image.ndim == 3 and image.shape[2] == 4:
                pil_image = Image.fromarray(image[:, :, [2, 1, 0, 3]], mode="RGBA")
            else:
                raise TypeError(f"Unsupported numpy image shape: {image.shape}")
            return ImageOps.exif_transpose(pil_image)

        raise TypeError(f"Unsupported OCR input type: {type(image).__name__}")

    @staticmethod
    def _map_paddle_lang(lang: str | None) -> str:
        if not lang:
            return "en"
        lowered = lang.lower().replace("-", "_")
        tokens = {token for token in lowered.replace(",", "+").split("+") if token}
        if {"rus", "ru"} & tokens:
            return "ru"
        if {"eng", "en"} & tokens:
            return "en"
        return next(iter(tokens), "en")

    @staticmethod
    def _map_easyocr_langs(lang: str | None) -> list[str]:
        if not lang:
            return ["en"]
        lowered = lang.lower().replace("-", "_")
        tokens = {token for token in lowered.replace(",", "+").split("+") if token}
        mapped: list[str] = []
        if {"rus", "ru"} & tokens:
            mapped.append("ru")
        if {"eng", "en"} & tokens:
            mapped.append("en")
        return mapped or ["en"]

    def _detect_ocr_device(self) -> str:
        if not self.config.ocr.use_gpu:
            return "cpu"
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    @staticmethod
    def _parse_paddle_output(raw_output: Any) -> tuple[list[str], list[float]]:
        texts: list[str] = []
        scores: list[float] = []

        def visit(node: Any) -> None:
            if node is None:
                return

            if isinstance(node, dict):
                rec_texts = node.get("rec_texts")
                rec_scores = node.get("rec_scores")
                if isinstance(rec_texts, list):
                    for index, value in enumerate(rec_texts):
                        OCRService._append_text(texts, value)
                        if isinstance(rec_scores, list) and index < len(rec_scores):
                            OCRService._append_score(scores, rec_scores[index])
                for key in ("result", "res", "data", "items"):
                    if key in node:
                        visit(node[key])
                return

            if isinstance(node, (list, tuple)):
                if len(node) == 2 and isinstance(node[0], str):
                    OCRService._append_text(texts, node[0])
                    OCRService._append_score(scores, node[1])
                    return
                if len(node) == 2 and isinstance(node[1], (list, tuple)) and node[1]:
                    candidate_text = node[1][0]
                    if isinstance(candidate_text, str):
                        OCRService._append_text(texts, candidate_text)
                        if len(node[1]) > 1:
                            OCRService._append_score(scores, node[1][1])
                        return
                for item in node:
                    visit(item)

        visit(raw_output)
        deduped_texts = list(dict.fromkeys(texts))
        return deduped_texts, scores

    @staticmethod
    def _parse_easyocr_output(raw_output: Any) -> list[str]:
        texts: list[str] = []
        if isinstance(raw_output, list):
            for item in raw_output:
                if isinstance(item, str):
                    OCRService._append_text(texts, item)
                elif isinstance(item, (list, tuple)):
                    for candidate in item:
                        if isinstance(candidate, str):
                            OCRService._append_text(texts, candidate)
                            break
        return list(dict.fromkeys(texts))

    @staticmethod
    def _append_text(bucket: list[str], value: Any) -> None:
        if isinstance(value, str):
            text = value.strip()
            if text:
                bucket.append(text)

    @staticmethod
    def _append_score(bucket: list[float], value: Any) -> None:
        if isinstance(value, (int, float)):
            bucket.append(float(value))

    @staticmethod
    def is_runtime_failure_warning(message: str) -> bool:
        """Return True if a warning means OCR runtime was degraded for subsequent items."""
        lowered = message.lower()
        return "ocr disabled for the remaining items" in lowered or "runtime failed" in lowered

    def _record_runtime_failure(self, state: _BackendState, message: str, exc: Exception) -> None:
        if state.cache_key is None:
            return
        failure_payload = {
            "message": message,
            "error": str(exc),
            "backend": state.backend_name,
            "device": state.details.get("device"),
        }
        with self._backend_lock:
            self._runtime_failure_cache[state.cache_key] = failure_payload
            self._backend_cache.pop(state.cache_key, None)
        LOGGER.warning("OCR backend degraded for cache_key=%s: %s", state.cache_key, exc)

    @staticmethod
    def _normalize_backend_error(backend_name: str | None, exc: Exception) -> tuple[str, str, bool]:
        raw_message = str(exc)
        lowered = raw_message.lower()
        if backend_name == "easyocr":
            if "cuda" in lowered or "cudnn" in lowered or "out of memory" in lowered:
                return (
                    "EasyOCR runtime failed; OCR disabled for the remaining items.",
                    "runtime_failed",
                    True,
                )
            return (
                "EasyOCR inference failed; continuing without OCR for this item.",
                "inference_failed",
                False,
            )
        if backend_name == "paddleocr":
            fatal_patterns = (
                "convertpirattribute2runtimeattribute",
                "onednn_instruction.cc",
                "pir::arrayattribute",
            )
            if any(pattern in lowered for pattern in fatal_patterns):
                return (
                    "PaddleOCR inference runtime failed; OCR disabled for the remaining items.",
                    "runtime_failed",
                    True,
                )
            return (
                "PaddleOCR inference failed; continuing without OCR for this item.",
                "inference_failed",
                False,
            )
        if backend_name == "pytesseract":
            return ("Tesseract OCR failed for this item.", "inference_failed", False)
        return (f"OCR failed: {raw_message}", "inference_failed", False)

    def _discover_local_paddle_models(self, backend_lang: str) -> dict[str, str] | None:
        recognition_model = self._PADDLE_RECOGNITION_MODELS.get(backend_lang)
        detection_model = self._PADDLE_DETECTION_MODELS.get(backend_lang)
        if recognition_model is None or detection_model is None:
            return None

        candidate_roots: list[Path] = []
        configured_root = getattr(self.config.ocr, "paddle_model_root", None)
        if configured_root:
            candidate_roots.append(Path(configured_root).expanduser())
        candidate_roots.extend(
            [
                Path.home() / ".paddlex" / "official_models",
                Path(os.environ.get("PADDLE_HOME", "")) / "official_models" if os.environ.get("PADDLE_HOME") else None,
                self.config.output_path / ".paddle_cache" / "official_models",
                Path.cwd() / ".paddle_cache" / "official_models",
            ]
        )
        filtered_roots = [root.resolve() for root in candidate_roots if root is not None and str(root)]
        for root in filtered_roots:
            detection_dir = root / detection_model
            recognition_dir = root / recognition_model
            common_dirs = [root / model_name for model_name in self._PADDLE_COMMON_MODELS]
            missing_parts = [
                label
                for label, candidate in (
                    ("det_model_dir", detection_dir),
                    ("rec_model_dir", recognition_dir),
                    *[(f"common:{candidate.name}", candidate) for candidate in common_dirs],
                )
                if not candidate.exists()
            ]
            if not missing_parts:
                resolved_models = {
                    "det_model_dir": str(detection_dir),
                    "rec_model_dir": str(recognition_dir),
                    "common_model_dirs": [str(candidate) for candidate in common_dirs],
                }
                LOGGER.info(
                    "Using PaddleOCR cached models from %s: det=%s rec=%s common=%s",
                    root,
                    resolved_models["det_model_dir"],
                    resolved_models["rec_model_dir"],
                    ", ".join(resolved_models["common_model_dirs"]),
                )
                return resolved_models
            LOGGER.debug(
                "Skipping PaddleOCR cache root %s due to missing components: %s",
                root,
                ", ".join(missing_parts),
            )
        LOGGER.warning(
            "PaddleOCR cached models not resolved for lang=%s. Expected cached folders: det=%s rec=%s common=%s",
            backend_lang,
            detection_model,
            recognition_model,
            ", ".join(self._PADDLE_COMMON_MODELS),
        )
        return None

    @staticmethod
    def _is_easyocr_model_missing_error(message: str) -> bool:
        lowered = message.lower()
        markers = (
            "download_enabled",
            "missing",
            "not found",
            "no such file",
            "model",
        )
        return any(marker in lowered for marker in markers)

    def _prepare_paddle_environment(self) -> None:
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
        os.environ.setdefault("PADDLE_PDX_DISABLE_DEVICE_FALLBACK", "True")
        if getattr(self.config.ocr, "offline_only", True):
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
        if self.config.ocr.suppress_backend_logs:
            os.environ.setdefault("GLOG_minloglevel", "2")
            logging.getLogger("paddle").setLevel(logging.ERROR)
            logging.getLogger("paddleocr").setLevel(logging.ERROR)
            logging.getLogger("ppocr").setLevel(logging.ERROR)

        preferred_dirs = [
            self.config.output_path / ".paddle_cache",
            Path.cwd() / ".paddle_cache",
            Path(tempfile.gettempdir()) / "pd_scanner_paddle",
        ]
        cache_dir = preferred_dirs[-1]
        for candidate in preferred_dirs:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                cache_dir = candidate
                break
            except Exception:
                continue
        os.environ.setdefault("PADDLE_HOME", str(cache_dir))
