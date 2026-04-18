"""Shared CLI helpers."""

from __future__ import annotations

import argparse
from pathlib import Path

from pd_scanner.core.config import AppConfig


def add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common runtime arguments."""
    parser.add_argument("--input", required=True, help="Input file or directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--mode", choices=("fast", "deep"), default="deep", help="Workflow mode")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads")
    parser.add_argument("--ocr-lang", default="rus+eng", help="Tesseract OCR language")
    parser.add_argument("--tesseract-cmd", default=None, help="Optional path to tesseract.exe")
    parser.add_argument("--video-frame-step-sec", type=int, default=3, help="Frame step for MP4 OCR")
    parser.add_argument("--max-file-size-mb", type=int, default=None, help="Optional maximum file size in MB")
    parser.add_argument("--log-level", default="INFO", help="Logging level")


def build_config_from_args(args: argparse.Namespace) -> AppConfig:
    """Create AppConfig from argparse namespace."""
    return AppConfig.build(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode,
        workers=args.workers,
        ocr_lang=args.ocr_lang,
        video_frame_step_sec=args.video_frame_step_sec,
        max_file_size_mb=args.max_file_size_mb,
        log_level=args.log_level,
        tesseract_cmd=args.tesseract_cmd,
    )


def validate_input_path(value: str) -> Path:
    """Validate an input path for CLI use."""
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Path does not exist: {path}")
    return path
