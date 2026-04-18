"""Application configuration and runtime defaults."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class VolumeThresholds:
    """Thresholds for file volume estimation."""

    small_max: int = 10
    medium_max: int = 100

    def classify(self, value: int) -> str:
        """Return a volume label for a numeric metric."""
        if value <= 0:
            return "none"
        if value <= self.small_max:
            return "small"
        if value <= self.medium_max:
            return "medium"
        return "large"

    def to_dict(self) -> dict[str, int]:
        """Serialize threshold settings."""
        return asdict(self)


@dataclass(slots=True)
class OCRConfig:
    """OCR-related settings."""

    enabled: bool = True
    backend: str = "easyocr"
    lang: str = "rus+eng"
    tesseract_cmd: str | None = None
    use_angle_cls: bool = True
    suppress_backend_logs: bool = True
    use_gpu: bool = True
    offline_only: bool = True
    paddle_model_root: str | None = None
    min_pdf_text_chars: int = 80
    image_dpi: int = 200

    def to_dict(self) -> dict[str, Any]:
        """Serialize OCR settings."""
        return asdict(self)


@dataclass(slots=True)
class RuntimeConfig:
    """Runtime controls and resource limits."""

    mode: str = "deep"
    workers: int = 4
    log_level: str = "INFO"
    chunksize: int = 1000
    max_file_size_mb: int | None = None
    max_rows_per_structured_file: int = 50_000
    max_table_records_in_memory: int = 3_000
    video_frame_step_sec: int = 3
    max_pdf_ocr_pages: int = 20
    max_video_frames: int = 120
    max_embedded_images_per_file: int = 20
    max_ocr_calls_per_file: int = 40
    snippet_radius: int = 40

    def to_dict(self) -> dict[str, Any]:
        """Serialize runtime settings."""
        return asdict(self)


@dataclass(slots=True)
class ReportingConfig:
    """Output filenames for generated artifacts."""

    csv_filename: str = "scan_report.csv"
    json_filename: str = "scan_report.json"
    markdown_filename: str = "scan_report.md"
    summary_filename: str = "summary.json"
    log_filename: str = "scan.log"
    state_filename: str = "scan_state.json"

    def to_dict(self) -> dict[str, str]:
        """Serialize reporting settings."""
        return asdict(self)


@dataclass(slots=True)
class DetectionConfig:
    """Detection scoring knobs and context dictionaries."""

    min_confidence: float = 0.45
    enable_model_detector: bool = False
    column_context_boost: float = 0.25
    keyword_context_boost: float = 0.15
    validation_boost: float = 0.25
    special_keywords: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "biometric_keyword": (
                "биометрия",
                "биометрические данные",
                "отпечаток пальца",
                "отпечатки пальцев",
                "радужная оболочка",
                "voiceprint",
                "голосовой образец",
                "распознавание лица",
                "face recognition",
            ),
            "special_health": (
                "диагноз",
                "медицинская карта",
                "анамнез",
                "инвалидность",
                "здоровье",
                "заболевание",
                "группа крови",
                "медицинский",
            ),
            "special_religion": (
                "вероисповедание",
                "религия",
                "православ",
                "мусульман",
                "буддист",
                "иудаизм",
                "конфессия",
            ),
            "special_politics": (
                "политические взгляды",
                "политические убеждения",
                "партийная принадлежность",
                "член партии",
                "электоральные предпочтения",
            ),
            "special_race_nationality": (
                "национальность",
                "этническая принадлежность",
                "расовая принадлежность",
                "этнос",
                "раса",
            ),
        }
    )
    column_hints: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "fio": ("фио", "full name", "name", "surname", "lastname", "firstname"),
            "phone": ("телефон", "phone", "mobile", "contact"),
            "email": ("email", "e-mail", "почта"),
            "birth_date": ("дата рождения", "birth", "dob"),
            "birth_place": ("место рождения", "birth place"),
            "address": ("адрес", "registration", "residence", "location"),
            "passport_rf": ("паспорт", "passport", "серия", "номер паспорта"),
            "snils": ("снилс",),
            "inn": ("инн", "inn"),
            "driver_license": ("водитель", "driver", "license"),
            "bank_card": ("карта", "card", "pan"),
            "bank_account": ("счет", "р/с", "расчетный счет", "account"),
            "bik": ("бик", "bik"),
            "cvv": ("cvv", "cvc", "security code", "код безопасности"),
            "mrz": ("mrz", "машиносчитываемая зона"),
        }
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize detection settings."""
        return {
            "min_confidence": self.min_confidence,
            "enable_model_detector": self.enable_model_detector,
            "column_context_boost": self.column_context_boost,
            "keyword_context_boost": self.keyword_context_boost,
            "validation_boost": self.validation_boost,
            "special_keywords": {key: list(values) for key, values in self.special_keywords.items()},
            "column_hints": {key: list(values) for key, values in self.column_hints.items()},
        }


@dataclass(slots=True)
class AppConfig:
    """Top-level application configuration."""

    input_path: Path
    output_path: Path
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    volume_thresholds: VolumeThresholds = field(default_factory=VolumeThresholds)

    @classmethod
    def build(
        cls,
        *,
        input_path: str | Path,
        output_path: str | Path,
        mode: str = "deep",
        workers: int = 4,
        ocr_lang: str = "rus+eng",
        video_frame_step_sec: int = 3,
        max_file_size_mb: int | None = None,
        log_level: str = "INFO",
        tesseract_cmd: str | None = None,
    ) -> "AppConfig":
        """Build configuration from backend or GUI inputs."""
        runtime = RuntimeConfig(
            mode=mode,
            workers=workers,
            log_level=log_level,
            max_file_size_mb=max_file_size_mb,
            video_frame_step_sec=video_frame_step_sec,
        )
        ocr = OCRConfig(
            enabled=mode == "deep",
            lang=ocr_lang,
            tesseract_cmd=tesseract_cmd,
        )
        return cls(
            input_path=Path(input_path).expanduser().resolve(),
            output_path=Path(output_path).expanduser().resolve(),
            runtime=runtime,
            ocr=ocr,
        )

    @classmethod
    def from_cli_args(cls, args: Any) -> "AppConfig":
        """Build configuration from CLI arguments."""
        return cls.build(
            input_path=args.input,
            output_path=args.output,
            mode=args.mode,
            workers=args.workers,
            ocr_lang=args.ocr_lang,
            video_frame_step_sec=args.video_frame_step_sec,
            max_file_size_mb=args.max_file_size_mb,
            log_level=args.log_level,
            tesseract_cmd=getattr(args, "tesseract_cmd", None),
        )

    def mode_description(self) -> str:
        """Human-readable mode summary."""
        if self.runtime.mode == "fast":
            return "Fast mode skips OCR-heavy steps and favors speed over recall."
        return "Deep mode enables OCR for scanned PDFs, images, and video frames when OCR is available."

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to a JSON-friendly structure."""
        return {
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "runtime": self.runtime.to_dict(),
            "ocr": self.ocr.to_dict(),
            "reporting": self.reporting.to_dict(),
            "detection": self.detection.to_dict(),
            "volume_thresholds": self.volume_thresholds.to_dict(),
            "mode_description": self.mode_description(),
        }
