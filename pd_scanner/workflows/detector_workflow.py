"""Detector-only workflow."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.classifiers.category_mapper import build_group_flags
from pd_scanner.classifiers.uz_classifier import classify_uz
from pd_scanner.classifiers.volume_estimator import estimate_volume
from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import ExtractionResult
from pd_scanner.core.utils import elapsed_seconds, ensure_directory, safe_read_text, time_now
from pd_scanner.core.workflow_models import WorkflowPreview, WorkflowResult
from pd_scanner.detectors.entity_detector import EntityDetector
from pd_scanner.extractors.base import BaseExtractor
from pd_scanner.workflows.helpers import build_summary_from_results, write_debug_artifact


def run_detector_workflow(
    config: AppConfig,
    *,
    text: str | None = None,
    text_file: str | Path | None = None,
) -> WorkflowResult:
    """Run detector-only flow against text or a text file."""
    started = time_now()
    source_text = text or ""
    source_name = "manual_input"
    if text_file:
        source_name = str(Path(text_file).expanduser().resolve())
        source_text = safe_read_text(Path(text_file).expanduser().resolve())

    extraction = ExtractionResult(
        file_type="detector_lab",
        extracted_text_chunks=[BaseExtractor.make_chunk(source_text, source_type="detector_lab_text")],
        metadata={"structured": False},
    )
    detector = EntityDetector(config)
    findings, entities, category_counts = detector.detect(extraction)
    group_flags = build_group_flags(set(category_counts))
    estimated_volume, volume_metric = estimate_volume(extraction, findings, config)
    from pd_scanner.core.models import FileScanResult

    result = FileScanResult(
        path=source_name,
        file_type="detector_lab",
        status="ok",
        error_message=None,
        detected_entities=entities,
        category_counts=category_counts,
        group_flags=group_flags,
        estimated_volume=estimated_volume,
        volume_metric=volume_metric,
        uz_level=classify_uz(group_flags, estimated_volume),
        processing_time_sec=elapsed_seconds(started),
        metadata={"findings_count": len(findings)},
    )
    summary = build_summary_from_results([result], elapsed_seconds(started))
    debug_path = write_debug_artifact(
        config,
        "detector_lab",
        "detector_findings",
        {
            "source": source_name,
            "findings": [
                {
                    "entity_type": finding.entity_type,
                    "masked_value": finding.masked_value,
                    "confidence": finding.confidence,
                    "explanation": finding.explanation,
                    "source_context": finding.source_context,
                }
                for finding in findings[:100]
            ],
        },
    )
    return WorkflowResult(
        workflow_type="detector_lab",
        summary=summary,
        results=[result],
        previews=[WorkflowPreview(title="Detector Findings", items=[{"source": source_name, "findings_count": len(findings)}])],
        metadata={"debug_artifact": debug_path},
    )
