"""Shared service layer for CLI, GUI, and specialized workflows."""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pd_scanner.core.config import AppConfig
from pd_scanner.core.lifecycle import LIFECYCLE_MANAGER, ScanAlreadyRunningError
from pd_scanner.core.logging_utils import configure_logging
from pd_scanner.core.models import DetectedEntity, FileScanResult, GroupFlags, ReportArtifacts, ReportSummary
from pd_scanner.core.pipeline import ScanPipeline
from pd_scanner.core.utils import ensure_directory, safe_json_dump
from pd_scanner.extractors.ocr_service import OCRService

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ProgressEvent:
    """A single operator-facing progress event."""

    timestamp: str
    level: str
    message: str


@dataclass(slots=True)
class ScanProgressSnapshot:
    """Serializable progress snapshot for UI polling or state files."""

    is_running: bool
    scan_id: str | None
    workflow_type: str | None
    status: str
    total_count: int
    processed_count: int
    files_with_pd: int
    warnings_count: int
    errors_count: int
    unsupported_count: int
    current_file: str | None
    last_result_path: str | None
    current_file_type: str | None = None
    current_extractor_name: str | None = None
    ocr_backend: str | None = None
    ocr_device: str | None = None
    stop_requested: bool = False
    current_stage: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    recent_events: list[ProgressEvent] = field(default_factory=list)
    aggregated_warnings: dict[str, int] = field(default_factory=dict)
    queued_files: list[str] = field(default_factory=list)
    recent_results: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, str]] = field(default_factory=list)
    live_previews: list[dict[str, Any]] = field(default_factory=list)
    processed_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize snapshot."""
        return {
            "is_running": self.is_running,
            "scan_id": self.scan_id,
            "workflow_type": self.workflow_type,
            "status": self.status,
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "files_with_pd": self.files_with_pd,
            "warnings_count": self.warnings_count,
            "errors_count": self.errors_count,
            "unsupported_count": self.unsupported_count,
            "current_file": self.current_file,
            "last_result_path": self.last_result_path,
            "current_file_type": self.current_file_type,
            "current_extractor_name": self.current_extractor_name,
            "ocr_backend": self.ocr_backend,
            "ocr_device": self.ocr_device,
            "stop_requested": self.stop_requested,
            "current_stage": self.current_stage,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "recent_events": [asdict(event) for event in self.recent_events],
            "aggregated_warnings": self.aggregated_warnings,
            "queued_files": self.queued_files,
            "recent_results": self.recent_results,
            "artifacts": self.artifacts,
            "live_previews": self.live_previews,
            "processed_by_type": self.processed_by_type,
        }


class ScanProgressTracker:
    """Thread-safe progress tracker with warning aggregation."""

    def __init__(self, state_file: Path | None = None, max_events: int = 100) -> None:
        self._lock = threading.Lock()
        self._recent_events: deque[ProgressEvent] = deque(maxlen=max_events)
        self._recent_results: deque[dict[str, Any]] = deque(maxlen=20)
        self._live_previews: deque[dict[str, Any]] = deque(maxlen=8)
        self._state_file = state_file
        self._is_running = False
        self._scan_id: str | None = None
        self._workflow_type: str | None = None
        self._status = "idle"
        self._total_count = 0
        self._processed_count = 0
        self._files_with_pd = 0
        self._warnings_count = 0
        self._errors_count = 0
        self._unsupported_count = 0
        self._current_file: str | None = None
        self._last_result_path: str | None = None
        self._current_file_type: str | None = None
        self._current_extractor_name: str | None = None
        self._ocr_backend: str | None = None
        self._ocr_device: str | None = None
        self._stop_requested = False
        self._current_stage: str | None = None
        self._started_at: str | None = None
        self._finished_at: str | None = None
        self._warning_counts: dict[str, int] = {}
        self._queued_files: list[str] = []
        self._artifacts: dict[str, str] = {}
        self._processed_by_type: dict[str, int] = {}

    def start(self, *, scan_id: str, workflow_type: str) -> None:
        """Mark the scan as started."""
        with self._lock:
            self._is_running = True
            self._scan_id = scan_id
            self._workflow_type = workflow_type
            self._status = "running"
            self._stop_requested = False
            self._queued_files = []
            self._warning_counts = {}
            self._artifacts = {}
            self._recent_results.clear()
            self._live_previews.clear()
            self._current_stage = "initializing"
            self._processed_count = 0
            self._files_with_pd = 0
            self._warnings_count = 0
            self._errors_count = 0
            self._unsupported_count = 0
            self._last_result_path = None
            self._current_file = None
            self._current_file_type = None
            self._current_extractor_name = None
            self._ocr_backend = None
            self._ocr_device = None
            self._processed_by_type = {}
            self._started_at = datetime.now(timezone.utc).isoformat()
            self._finished_at = None
            self._append_event("INFO", f"{workflow_type} started.")
            self._persist_locked()

    def set_ocr_runtime(self, *, backend: str | None, device: str | None) -> None:
        """Expose active OCR backend/device for UI and state files."""
        with self._lock:
            self._ocr_backend = backend
            self._ocr_device = device
            self._persist_locked()

    def set_total_files(self, total_files: int) -> None:
        """Set total number of files to process."""
        with self._lock:
            self._total_count = total_files
            self._append_event("INFO", f"Discovered {total_files} files.")
            self._persist_locked()

    def set_queue_preview(self, files: list[Path], *, limit: int = 25) -> None:
        """Store a compact queue preview for the UI."""
        with self._lock:
            self._queued_files = [str(path) for path in files[:limit]]
            self._persist_locked()

    def set_stage(self, stage: str) -> None:
        """Set the current workflow stage."""
        with self._lock:
            self._current_stage = stage
            self._persist_locked()

    def request_stop(self) -> None:
        """Request cooperative cancellation for the running workflow."""
        with self._lock:
            if not self._is_running:
                return
            self._stop_requested = True
            self._status = "stopping"
            self._append_event("WARNING", "Stop requested. Waiting for the current step to finish.")
            self._persist_locked()

    def should_stop(self) -> bool:
        """Return True if a cooperative stop has been requested."""
        with self._lock:
            return self._stop_requested

    def register_artifact(self, label: str, path: str | Path) -> None:
        """Expose a workflow/debug artifact to the UI."""
        with self._lock:
            self._artifacts[label] = str(path)
            self._persist_locked()

    def publish_preview(self, title: str, items: list[dict[str, Any]]) -> None:
        """Publish a lightweight live preview payload for operator UI."""
        with self._lock:
            self._live_previews.appendleft({"title": title, "items": items[:5]})
            self._persist_locked()

    def on_file_started(
        self,
        path: Path,
        *,
        file_type: str | None = None,
        extractor_name: str | None = None,
    ) -> None:
        """Mark a file as currently being processed."""
        with self._lock:
            self._current_file = str(path)
            self._current_file_type = file_type
            self._current_extractor_name = extractor_name
            if file_type or extractor_name:
                handler = f"{file_type or 'unknown'} via {extractor_name or 'unknown extractor'}"
                self._append_event("INFO", f"Processing {path.name} ({handler}).")
            self._persist_locked()

    def on_file_completed(self, result: FileScanResult) -> None:
        """Update counters after a file is processed."""
        with self._lock:
            self._processed_count += 1
            self._last_result_path = result.path
            self._current_file = None
            self._current_file_type = None
            self._current_extractor_name = None
            if result.uz_level != "NO_PD":
                self._files_with_pd += 1
            if result.status == "error":
                self._errors_count += 1
            if result.status == "unsupported":
                self._unsupported_count += 1
            result_type = result.file_type or "unknown"
            self._processed_by_type[result_type] = self._processed_by_type.get(result_type, 0) + 1
            self._recent_results.appendleft(
                {
                    "path": result.path,
                    "file_type": result.file_type,
                    "status": result.status,
                    "uz_level": result.uz_level,
                    "categories": ", ".join(sorted(result.category_counts)) or "n/a",
                    "entities": sum(result.category_counts.values()),
                    "warnings": len(result.warnings),
                    "error_message": result.error_message or "",
                }
            )
            self._append_event("INFO", self._result_event_message(result))
            if self._processed_count == 1 or self._processed_count % 25 == 0:
                self._append_event(
                    "INFO",
                    f"Processed {self._processed_count}/{self._total_count or '?'} files.",
                )
            self._persist_locked()

    def on_warning(self, message: str, *, aggregate_key: str | None = None, operator_visible: bool = True) -> None:
        """Register a warning with optional aggregation."""
        with self._lock:
            self._warnings_count += 1
            key = aggregate_key or message
            self._warning_counts[key] = self._warning_counts.get(key, 0) + 1
            count = self._warning_counts[key]
            lowered = message.lower()
            if "ocr disabled for the remaining items" in lowered or "continuing without ocr" in lowered:
                self._current_stage = "continuing with warning"
            if operator_visible and count in {1, 10, 100}:
                suffix = "" if count == 1 else f" (repeated {count} times)"
                self._append_event("WARNING", f"{message}{suffix}")
            self._persist_locked()

    def on_error(self, message: str, *, operator_visible: bool = True) -> None:
        """Register an error."""
        with self._lock:
            self._errors_count += 1
            if operator_visible:
                self._append_event("ERROR", message)
            self._persist_locked()

    def log(self, level: str, message: str, *, operator_visible: bool = True) -> None:
        """Record a generic operator event."""
        with self._lock:
            if operator_visible:
                self._append_event(level, message)
            self._persist_locked()

    def finish(self, status: str = "completed") -> None:
        """Mark the scan as finished and emit aggregated warning summary."""
        with self._lock:
            self._is_running = False
            final_status = "cancelled" if self._stop_requested and status == "completed" else status
            self._status = final_status
            self._current_file = None
            self._current_stage = "finished"
            self._finished_at = datetime.now(timezone.utc).isoformat()
            for warning_message, count in sorted(self._warning_counts.items(), key=lambda item: (-item[1], item[0])):
                if count > 1:
                    self._append_event("WARNING", f"{warning_message} (repeated {count} times)")
            self._append_event("INFO", f"Scan finished with status={final_status}.")
            self._persist_locked()

    def snapshot(self) -> ScanProgressSnapshot:
        """Return a snapshot suitable for UI rendering."""
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> ScanProgressSnapshot:
        return ScanProgressSnapshot(
            is_running=self._is_running,
            scan_id=self._scan_id,
            workflow_type=self._workflow_type,
            status=self._status,
            total_count=self._total_count,
            processed_count=self._processed_count,
            files_with_pd=self._files_with_pd,
            warnings_count=self._warnings_count,
            errors_count=self._errors_count,
            unsupported_count=self._unsupported_count,
            current_file=self._current_file,
            last_result_path=self._last_result_path,
            current_file_type=self._current_file_type,
            current_extractor_name=self._current_extractor_name,
            ocr_backend=self._ocr_backend,
            ocr_device=self._ocr_device,
            stop_requested=self._stop_requested,
            current_stage=self._current_stage,
            started_at=self._started_at,
            finished_at=self._finished_at,
            recent_events=list(self._recent_events),
            aggregated_warnings=dict(sorted(self._warning_counts.items(), key=lambda item: (-item[1], item[0]))),
            queued_files=list(self._queued_files),
            recent_results=list(self._recent_results),
            artifacts=[{"label": key, "path": value} for key, value in self._artifacts.items()],
            live_previews=list(self._live_previews),
            processed_by_type=dict(sorted(self._processed_by_type.items())),
        )

    def _append_event(self, level: str, message: str) -> None:
        event = ProgressEvent(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            level=level,
            message=message,
        )
        self._recent_events.appendleft(event)

    def _result_event_message(self, result: FileScanResult) -> str:
        """Return an operator-friendly event label for a completed file."""
        name = Path(result.path).name
        file_type = (result.file_type or "unknown").lower()
        if result.status == "error":
            return f"{file_type.upper()} failed: {name}"
        if result.status == "unsupported":
            return f"Unsupported file skipped: {name}"
        if file_type == "docx":
            return f"DOCX extracted: {name}"
        if file_type == "rtf":
            return f"RTF parsed: {name}"
        if file_type == "txt":
            return f"TXT loaded: {name}"
        if file_type == "pdf":
            return f"PDF text extracted: {name}"
        if file_type in {"csv", "json", "jsonl", "parquet", "xls", "xlsx"}:
            return f"{file_type.upper()} structured scan completed: {name}"
        if file_type in {"jpg", "jpeg", "png", "gif", "tif", "tiff"}:
            return f"Image OCR processed: {name}"
        if file_type == "mp4":
            return f"Video scan completed: {name}"
        return f"{file_type.upper()} processed: {name}"

    def _persist_locked(self) -> None:
        if self._state_file is None:
            return
        safe_json_dump(self._snapshot_locked().to_dict(), self._state_file)


class ScanService:
    """High-level API shared by CLI and GUI entrypoints."""

    @staticmethod
    def build_artifacts(config: AppConfig) -> ReportArtifacts:
        """Build report artifact paths for a scan."""
        return ReportArtifacts(
            output_dir=str(config.output_path),
            csv_report=str(config.output_path / config.reporting.csv_filename),
            json_report=str(config.output_path / config.reporting.json_filename),
            markdown_report=str(config.output_path / config.reporting.markdown_filename),
            summary_report=str(config.output_path / config.reporting.summary_filename),
            log_file=str(config.output_path / config.reporting.log_filename),
            state_file=str(config.output_path / config.reporting.state_filename),
        )

    @staticmethod
    def probe_ocr(config: AppConfig) -> tuple[bool, str]:
        """Return OCR availability and user-facing explanation."""
        return OCRService(config).get_status()

    @staticmethod
    def run_scan(
        config: AppConfig,
        *,
        tracker: ScanProgressTracker | None = None,
        workflow_type: str = "full_scan",
    ) -> tuple[ReportSummary, list[FileScanResult], list[dict[str, str]], ReportArtifacts]:
        """Run a full scan and return summary, results, errors, and artifact paths."""
        ensure_directory(config.output_path)
        artifacts = ScanService.build_artifacts(config)
        tracker = tracker or ScanProgressTracker(Path(artifacts.state_file))
        scan_id = LIFECYCLE_MANAGER.start(workflow_type, Path(artifacts.state_file))
        tracker.start(scan_id=scan_id, workflow_type=workflow_type)
        tracker.register_artifact("Output directory", artifacts.output_dir)
        tracker.register_artifact("scan.log", artifacts.log_file)
        tracker.register_artifact("scan_state.json", artifacts.state_file)
        tracker.register_artifact("scan_report.json", artifacts.json_report)
        tracker.register_artifact("scan_report.csv", artifacts.csv_report)
        tracker.register_artifact("scan_report.md", artifacts.markdown_report)
        try:
            configure_logging(config.runtime.log_level, log_file=Path(artifacts.log_file))
            LOGGER.info("Running %s for %s", workflow_type, config.input_path)
            pipeline = ScanPipeline(config, progress_tracker=tracker)
            summary, results, errors = pipeline.run()
            tracker.finish("cancelled" if tracker.should_stop() else "completed")
            return summary, results, errors, artifacts
        except Exception as exc:
            tracker.on_error(f"Fatal scan error: {exc}", operator_visible=True)
            tracker.finish("failed")
            LOGGER.exception("Fatal scan failure")
            raise
        finally:
            LIFECYCLE_MANAGER.finish(scan_id)

    @staticmethod
    def load_scan_results(output_dir: str | Path) -> tuple[dict[str, Any] | None, ReportArtifacts | None]:
        """Load existing results from an output directory if present."""
        output_path = Path(output_dir).expanduser().resolve()
        if not output_path.exists():
            return None, None
        dummy_config = AppConfig.build(input_path=output_path, output_path=output_path)
        artifacts = ScanService.build_artifacts(dummy_config)
        json_report = Path(artifacts.json_report)
        if not json_report.exists():
            return None, artifacts
        payload = json.loads(json_report.read_text(encoding="utf-8"))
        return payload, artifacts

    @staticmethod
    def run_managed_workflow(
        config: AppConfig,
        *,
        workflow_type: str,
        runner: Callable[[], Any],
        tracker: ScanProgressTracker | None = None,
    ) -> Any:
        """Run a workflow under shared lifecycle/state control."""
        ensure_directory(config.output_path)
        artifacts = ScanService.build_artifacts(config)
        tracker = tracker or ScanProgressTracker(Path(artifacts.state_file))
        scan_id = LIFECYCLE_MANAGER.start(workflow_type, Path(artifacts.state_file))
        tracker.start(scan_id=scan_id, workflow_type=workflow_type)
        tracker.register_artifact("Output directory", artifacts.output_dir)
        tracker.register_artifact("scan.log", artifacts.log_file)
        tracker.register_artifact("scan_state.json", artifacts.state_file)
        try:
            configure_logging(config.runtime.log_level, log_file=Path(artifacts.log_file))
            result = runner()
            tracker.finish("cancelled" if tracker.should_stop() else "completed")
            return result
        except Exception as exc:
            tracker.on_error(f"Fatal workflow error: {exc}", operator_visible=True)
            tracker.finish("failed")
            raise
        finally:
            LIFECYCLE_MANAGER.finish(scan_id)

    @staticmethod
    def deserialize_summary(summary_payload: dict[str, Any]) -> ReportSummary:
        """Deserialize summary payload."""
        return ReportSummary(
            total_files=summary_payload.get("total_files", 0),
            processed_files=summary_payload.get("processed_files", 0),
            files_with_pd=summary_payload.get("files_with_pd", 0),
            files_by_uz=summary_payload.get("files_by_uz", {}),
            entity_stats=summary_payload.get("entity_stats", {}),
            errors_count=summary_payload.get("errors_count", 0),
            unsupported_count=summary_payload.get("unsupported_count", 0),
            warnings_count=summary_payload.get("warnings_count", 0),
            processing_time_total_sec=summary_payload.get("processing_time_total_sec", 0.0),
        )

    @staticmethod
    def deserialize_file_result(payload: dict[str, Any]) -> FileScanResult:
        """Deserialize file result payload."""
        return FileScanResult(
            path=payload["path"],
            file_type=payload["file_type"],
            status=payload["status"],
            error_message=payload.get("error_message"),
            detected_entities=[DetectedEntity(**item) for item in payload.get("detected_entities", [])],
            category_counts=payload.get("category_counts", {}),
            group_flags=GroupFlags(**payload.get("group_flags", {})),
            estimated_volume=payload.get("estimated_volume", "none"),
            volume_metric=payload.get("volume_metric", 0),
            uz_level=payload.get("uz_level", "NO_PD"),
            processing_time_sec=payload.get("processing_time_sec", 0.0),
            metadata=payload.get("metadata", {}),
            warnings=payload.get("warnings", []),
        )
