"""Lifecycle and single-active-scan control."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pd_scanner.core.utils import safe_json_dump


@dataclass(slots=True)
class ActiveScanRecord:
    """Single active scan state."""

    scan_id: str
    workflow_type: str
    started_at: str
    state_file: Path


class ScanAlreadyRunningError(RuntimeError):
    """Raised when a second scan is attempted while one is active."""


class ScanLifecycleManager:
    """Process-local lifecycle manager with a single-active-scan policy."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: ActiveScanRecord | None = None

    def start(self, workflow_type: str, state_file: Path) -> str:
        """Register a new active scan or raise if one is already running."""
        with self._lock:
            if self._active is not None:
                raise ScanAlreadyRunningError(
                    f"Scan already in progress: {self._active.workflow_type} ({self._active.scan_id})"
                )
            scan_id = uuid.uuid4().hex
            self._active = ActiveScanRecord(
                scan_id=scan_id,
                workflow_type=workflow_type,
                started_at=datetime.now(timezone.utc).isoformat(),
                state_file=state_file,
            )
            return scan_id

    def finish(self, scan_id: str) -> None:
        """Clear the active scan when the owner finishes."""
        with self._lock:
            if self._active is not None and self._active.scan_id == scan_id:
                self._active = None

    def get_active(self) -> ActiveScanRecord | None:
        """Return the current active scan, if any."""
        with self._lock:
            return self._active


LIFECYCLE_MANAGER = ScanLifecycleManager()
