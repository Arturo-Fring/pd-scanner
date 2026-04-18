"""Logging helpers for CLI and GUI runs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable


class CallbackLogHandler(logging.Handler):
    """Forward formatted log messages to a callback."""

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """Send the formatted record to the callback."""
        try:
            self.callback(record.levelname, self.format(record))
        except Exception:
            return


def configure_logging(
    level: str = "INFO",
    *,
    log_file: Path | None = None,
    callback: Callable[[str, str], None] | None = None,
) -> None:
    """Configure root logging for the application."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if callback is not None:
        callback_handler = CallbackLogHandler(callback)
        callback_handler.setFormatter(formatter)
        root.addHandler(callback_handler)

    logging.captureWarnings(True)
