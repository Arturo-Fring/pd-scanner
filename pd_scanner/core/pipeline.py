"""Main orchestration pipeline for scanning and reporting."""

from __future__ import annotations

import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - optional dependency import guard
    def tqdm(iterable, **_: object):  # type: ignore[no-redef]
        return iterable

from pd_scanner.classifiers.category_mapper import build_group_flags
from pd_scanner.classifiers.uz_classifier import classify_uz
from pd_scanner.classifiers.volume_estimator import estimate_volume
from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import FileScanResult, ReportSummary
from pd_scanner.core.utils import elapsed_seconds, ensure_directory, safe_json_dump, time_now
from pd_scanner.detectors.entity_detector import EntityDetector
from pd_scanner.reporting.csv_report import write_csv_report
from pd_scanner.reporting.json_report import write_json_report
from pd_scanner.reporting.markdown_report import write_markdown_report
from pd_scanner.scanner.file_dispatcher import get_extractor
from pd_scanner.scanner.walker import iter_files

if TYPE_CHECKING:
    from pd_scanner.core.services import ScanProgressTracker

LOGGER = logging.getLogger(__name__)


class ScanPipeline:
    """Coordinate extraction, detection, classification, and reporting."""

    def __init__(self, config: AppConfig, progress_tracker: "ScanProgressTracker | None" = None) -> None:
        self.config = config
        self.detector = EntityDetector(config)
        self.progress_tracker = progress_tracker

    def run(self) -> tuple[ReportSummary, list[FileScanResult], list[dict[str, str]]]:
        """Scan input directory and write reports."""
        ensure_directory(self.config.output_path)
        start = time_now()
        files = iter_files(self.config.input_path, self.config, progress_tracker=self.progress_tracker)
        if self.progress_tracker is not None:
            self.progress_tracker.set_total_files(len(files))
            self.progress_tracker.set_queue_preview(files)
            self.progress_tracker.set_stage("scan")
        LOGGER.info("Discovered %s files for scanning.", len(files))

        results: list[FileScanResult] = []
        use_sequential = self.config.runtime.workers <= 1 or self.progress_tracker is not None
        if use_sequential:
            iterator = tqdm(files, desc="Scanning", unit="file")
            for path in iterator:
                if self.progress_tracker is not None and self.progress_tracker.should_stop():
                    LOGGER.info("Stop requested. Ending scan after %s processed files.", len(results))
                    break
                results.append(self.process_file(path))
        else:
            with ThreadPoolExecutor(max_workers=self.config.runtime.workers) as executor:
                future_map = {executor.submit(self.process_file, path): path for path in files}
                for future in tqdm(as_completed(future_map), total=len(future_map), desc="Scanning", unit="file"):
                    results.append(future.result())

        results.sort(key=lambda result: result.path)
        errors = [
            {"path": result.path, "error_message": result.error_message or "unknown error"}
            for result in results
            if result.status == "error"
        ]
        summary = self._build_summary(results, elapsed_seconds(start))
        self._write_reports(summary, results, errors)
        LOGGER.info(
            "Scan finished. processed=%s, with_pd=%s, errors=%s, unsupported=%s",
            summary.processed_files,
            summary.files_with_pd,
            summary.errors_count,
            summary.unsupported_count,
        )
        return summary, results, errors

    def process_file(self, path: Path) -> FileScanResult:
        """Process a single file."""
        started = time_now()
        extractor = None
        result: FileScanResult
        try:
            extractor = get_extractor(path, self.config)
            if self.progress_tracker is not None:
                self.progress_tracker.on_file_started(
                    path,
                    file_type=extractor.file_type if extractor is not None else (path.suffix.lower().lstrip(".") or "unknown"),
                    extractor_name=extractor.__class__.__name__ if extractor is not None else "Unsupported",
                )
                self.progress_tracker.set_stage("extract-detect")
            if extractor is None:
                result = FileScanResult(
                    path=str(path),
                    file_type=path.suffix.lower().lstrip(".") or "unknown",
                    status="unsupported",
                    error_message="Unsupported file type",
                    processing_time_sec=elapsed_seconds(started),
                )
                LOGGER.info("Unsupported file type skipped: %s", path)
                return result

            extraction = extractor.extract(path)
            for warning in extraction.warnings:
                LOGGER.info("%s | %s", path, warning)
                if self.progress_tracker is not None:
                    aggregate_key = warning
                    operator_visible = "fast mode" not in warning.lower() and "best-effort" not in warning.lower()
                    self.progress_tracker.on_warning(
                        warning,
                        aggregate_key=aggregate_key,
                        operator_visible=operator_visible,
                    )

            findings, detected_entities, category_counts = self.detector.detect(extraction)
            group_flags = build_group_flags(set(category_counts))
            estimated_volume, volume_metric = estimate_volume(extraction, findings, self.config)
            uz_level = classify_uz(group_flags, estimated_volume)
            result = FileScanResult(
                path=str(path),
                file_type=extraction.file_type,
                status="ok",
                error_message=None,
                detected_entities=detected_entities,
                category_counts=category_counts,
                group_flags=group_flags,
                estimated_volume=estimated_volume,
                volume_metric=volume_metric,
                uz_level=uz_level,
                processing_time_sec=elapsed_seconds(started),
                metadata=extraction.metadata,
                warnings=extraction.warnings,
            )
        except Exception as exc:
            LOGGER.exception("Failed to process %s", path)
            if self.progress_tracker is not None:
                self.progress_tracker.on_error(f"{path.name}: {exc}")
            result = FileScanResult(
                path=str(path),
                file_type=extractor.file_type if extractor is not None else (path.suffix.lower().lstrip(".") or "unknown"),
                status="error",
                error_message=str(exc),
                processing_time_sec=elapsed_seconds(started),
            )
        finally:
            if self.progress_tracker is not None:
                self.progress_tracker.on_file_completed(result)
        return result

    def _build_summary(self, results: list[FileScanResult], total_time: float) -> ReportSummary:
        uz_counter = Counter(result.uz_level for result in results)
        entity_counter = Counter()
        warnings_count = 0
        for result in results:
            entity_counter.update(result.category_counts)
            warnings_count += len(result.warnings)
        return ReportSummary(
            total_files=len(results),
            processed_files=sum(result.status == "ok" for result in results),
            files_with_pd=sum(result.uz_level != "NO_PD" for result in results),
            files_by_uz=dict(sorted(uz_counter.items())),
            entity_stats=dict(sorted(entity_counter.items())),
            errors_count=sum(result.status == "error" for result in results),
            unsupported_count=sum(result.status == "unsupported" for result in results),
            warnings_count=warnings_count,
            processing_time_total_sec=total_time,
        )

    def _write_reports(
        self,
        summary: ReportSummary,
        results: list[FileScanResult],
        errors: list[dict[str, str]],
    ) -> None:
        csv_path = self.config.output_path / self.config.reporting.csv_filename
        json_path = self.config.output_path / self.config.reporting.json_filename
        markdown_path = self.config.output_path / self.config.reporting.markdown_filename
        summary_path = self.config.output_path / self.config.reporting.summary_filename
        write_csv_report(csv_path, results)
        write_json_report(json_path, summary, results, errors)
        write_markdown_report(markdown_path, summary, results, errors)
        safe_json_dump(asdict(summary), summary_path)
