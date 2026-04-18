"""Shared building blocks for specialized file workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from pd_scanner.classifiers.category_mapper import build_group_flags
from pd_scanner.classifiers.uz_classifier import classify_uz
from pd_scanner.classifiers.volume_estimator import estimate_volume
from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import FileScanResult
from pd_scanner.core.utils import elapsed_seconds, time_now
from pd_scanner.core.services import ScanProgressTracker
from pd_scanner.detectors.entity_detector import EntityDetector
from pd_scanner.scanner.file_dispatcher import get_extractor


def scan_single_path(
    path: Path,
    config: AppConfig,
    tracker: ScanProgressTracker | None = None,
) -> tuple[FileScanResult, object | None]:
    """Extract and detect entities for one file path."""
    started = time_now()
    extractor = get_extractor(path, config)
    if tracker is not None:
        tracker.on_file_started(
            path,
            file_type=extractor.file_type if extractor is not None else (path.suffix.lower().lstrip(".") or "unknown"),
            extractor_name=extractor.__class__.__name__ if extractor is not None else "Unsupported",
        )
        tracker.set_stage("extract-detect")
    if extractor is None:
        result = FileScanResult(
            path=str(path),
            file_type=path.suffix.lower().lstrip(".") or "unknown",
            status="unsupported",
            error_message="Unsupported file type",
            processing_time_sec=elapsed_seconds(started),
        )
        if tracker is not None:
            tracker.on_file_completed(result)
        return (
            result,
            None,
        )

    detector = EntityDetector(config)
    result: FileScanResult
    try:
        extraction = extractor.extract(path)
        for warning in extraction.warnings:
            if tracker is not None:
                operator_visible = "fast mode" not in warning.lower() and "best-effort" not in warning.lower()
                tracker.on_warning(
                    warning,
                    aggregate_key=warning,
                    operator_visible=operator_visible,
                )
        findings, detected_entities, category_counts = detector.detect(extraction)
        group_flags = build_group_flags(set(category_counts))
        estimated_volume, volume_metric = estimate_volume(extraction, findings, config)
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
            uz_level=classify_uz(group_flags, estimated_volume),
            processing_time_sec=elapsed_seconds(started),
            metadata=extraction.metadata,
            warnings=extraction.warnings,
        )
        return result, extraction
    except Exception as exc:
        if tracker is not None:
            tracker.on_error(f"{path.name}: {exc}")
        result = FileScanResult(
            path=str(path),
            file_type=extractor.file_type,
            status="error",
            error_message=str(exc),
            processing_time_sec=elapsed_seconds(started),
        )
        return result, None
    finally:
        if tracker is not None:
            tracker.on_file_completed(result)
