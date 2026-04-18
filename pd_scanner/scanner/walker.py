"""Recursive file discovery with size-limit and permission safeguards."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pd_scanner.core.config import AppConfig

if TYPE_CHECKING:
    from pd_scanner.core.services import ScanProgressTracker

LOGGER = logging.getLogger(__name__)


def iter_files(
    root: Path,
    config: AppConfig,
    *,
    progress_tracker: "ScanProgressTracker | None" = None,
) -> list[Path]:
    """Return discovered files under the input directory respecting size limits."""
    files: list[Path] = []
    max_bytes = None
    if config.runtime.max_file_size_mb is not None:
        max_bytes = config.runtime.max_file_size_mb * 1024 * 1024

    for path in root.rglob("*"):
        try:
            if not path.is_file():
                continue
            if max_bytes is not None and path.stat().st_size > max_bytes:
                message = f"Skipped by size limit: {path}"
                LOGGER.info(message)
                if progress_tracker is not None:
                    progress_tracker.log("INFO", message)
                continue
            files.append(path)
        except OSError as exc:
            message = f"Failed to inspect {path}: {exc}"
            LOGGER.warning(message)
            if progress_tracker is not None:
                progress_tracker.on_warning(message)
    return sorted(files)
