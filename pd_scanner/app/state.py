"""State helpers for the Streamlit application."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pd_scanner.core.config import AppConfig
from pd_scanner.core.lifecycle import ScanAlreadyRunningError
from pd_scanner.core.services import ScanProgressSnapshot, ScanProgressTracker, ScanService
from pd_scanner.core.workflow_models import WorkflowResult
from pd_scanner.workflows.detector_workflow import run_detector_workflow
from pd_scanner.workflows.full_scan_workflow import run_full_scan_workflow
from pd_scanner.workflows.image_workflow import run_image_workflow
from pd_scanner.workflows.pdf_workflow import run_pdf_workflow
from pd_scanner.workflows.reporting_workflow import run_reporting_workflow
from pd_scanner.workflows.structured_workflow import run_structured_workflow
from pd_scanner.workflows.text_workflow import run_text_workflow
from pd_scanner.workflows.video_workflow import run_video_workflow


WORKFLOW_RUNNERS: dict[str, Callable[..., WorkflowResult]] = {
    "full_scan": run_full_scan_workflow,
    "pdf_scan": run_pdf_workflow,
    "structured_scan": run_structured_workflow,
    "text_scan": run_text_workflow,
    "image_scan": run_image_workflow,
    "video_scan": run_video_workflow,
    "detector_lab": run_detector_workflow,
    "report_build": run_reporting_workflow,
}


@dataclass(slots=True)
class BackgroundScanState:
    """Thread-safe background state for Streamlit workflows."""

    tracker: ScanProgressTracker | None = None
    thread: threading.Thread | None = None
    config: AppConfig | None = None
    workflow_type: str | None = None
    workflow_result: WorkflowResult | None = None
    exception_message: str | None = None
    recent_input_paths: list[str] = field(default_factory=list)
    recent_output_paths: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _remember_paths_locked(self, input_value: str, output_value: str) -> None:
        self.recent_input_paths = [item for item in self.recent_input_paths if item != input_value]
        self.recent_output_paths = [item for item in self.recent_output_paths if item != output_value]
        self.recent_input_paths.insert(0, input_value)
        self.recent_output_paths.insert(0, output_value)
        self.recent_input_paths = self.recent_input_paths[:8]
        self.recent_output_paths = self.recent_output_paths[:8]

    def is_running(self) -> bool:
        """Return True if a background scan is currently running."""
        if self.thread is not None and not self.thread.is_alive():
            with self._lock:
                if self.thread is not None and not self.thread.is_alive():
                    self.thread = None
        return self.thread is not None and self.thread.is_alive()

    def remember_paths(self, input_path: str | Path, output_path: str | Path) -> None:
        """Remember recently used input/output paths for GUI presets."""
        input_value = str(Path(input_path).expanduser().resolve())
        output_value = str(Path(output_path).expanduser().resolve())
        with self._lock:
            self._remember_paths_locked(input_value, output_value)

    def start(self, workflow_type: str, config: AppConfig, **kwargs: object) -> None:
        """Start a background workflow with shared lifecycle rules."""
        with self._lock:
            if self.thread is not None and self.thread.is_alive():
                raise ScanAlreadyRunningError("A workflow is already running.")
            self.config = config
            self.workflow_type = workflow_type
            self.workflow_result = None
            self.exception_message = None
            self.tracker = ScanProgressTracker(config.output_path / config.reporting.state_filename)
            self._remember_paths_locked(str(config.input_path), str(config.output_path))
            self.thread = threading.Thread(
                target=self._run_workflow,
                kwargs={"workflow_type": workflow_type, "config": config, **kwargs},
                daemon=True,
            )
            self.thread.start()

    def request_stop(self) -> bool:
        """Request cooperative cancellation for the current workflow."""
        tracker = self.tracker
        if tracker is None or not self.is_running():
            return False
        tracker.request_stop()
        return True

    def run_sync(self, workflow_type: str, config: AppConfig, **kwargs: object) -> WorkflowResult:
        """Run a short workflow synchronously."""
        runner = WORKFLOW_RUNNERS[workflow_type]
        result = runner(config, **kwargs)
        with self._lock:
            self.workflow_result = result
            self.workflow_type = workflow_type
            self._remember_paths_locked(str(config.input_path), str(config.output_path))
        return result

    def snapshot(self) -> ScanProgressSnapshot | None:
        """Return a progress snapshot."""
        tracker = self.tracker
        if tracker is None:
            return None
        self.is_running()
        return tracker.snapshot()

    def load_existing_results(self, output_dir: str | Path) -> None:
        """Load reporting workflow from disk."""
        if self.config is None:
            config = AppConfig.build(input_path=output_dir, output_path=output_dir)
        else:
            config = AppConfig.build(input_path=self.config.input_path, output_path=output_dir)
        self.run_sync("report_build", config, output_dir=output_dir)

    def _run_workflow(self, workflow_type: str, config: AppConfig, **kwargs: object) -> None:
        runner = WORKFLOW_RUNNERS[workflow_type]
        try:
            if workflow_type == "full_scan":
                assert self.tracker is not None
                result = runner(config, tracker=self.tracker)
            else:
                assert self.tracker is not None
                result = ScanService.run_managed_workflow(
                    config,
                    workflow_type=workflow_type,
                    tracker=self.tracker,
                    runner=lambda: runner(config, tracker=self.tracker, **kwargs),
                )
            with self._lock:
                self.workflow_result = result
        except Exception as exc:
            with self._lock:
                self.exception_message = str(exc)
        finally:
            with self._lock:
                if self.thread is not None and not self.thread.is_alive():
                    self.thread = None
