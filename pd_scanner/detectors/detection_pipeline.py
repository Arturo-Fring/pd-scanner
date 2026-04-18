"""Composable detection pipeline with duplicate-merge logic."""

from __future__ import annotations

from pd_scanner.core.models import RawFinding
from pd_scanner.detectors.base import BaseDetector


class DetectionPipeline:
    """Run multiple detectors and merge overlapping findings."""

    def __init__(self, detectors: list[BaseDetector]) -> None:
        self.detectors = detectors

    def detect(self, chunks) -> list[RawFinding]:
        """Run detectors and merge duplicate findings."""
        merged: dict[tuple[object, ...], RawFinding] = {}
        order: list[tuple[object, ...]] = []
        for detector in self.detectors:
            for finding in detector.detect(chunks):
                key = self._merge_key(finding)
                existing = merged.get(key)
                if existing is None:
                    merged[key] = finding
                    order.append(key)
                    continue
                self._merge_into(existing, finding)
        return [merged[key] for key in order]

    @staticmethod
    def _merge_key(finding: RawFinding) -> tuple[object, ...]:
        if finding.start is not None and finding.end is not None:
            return ("span", finding.entity_type, finding.row_key, finding.start, finding.end)
        return ("value", finding.entity_type, finding.row_key, finding.normalized_value)

    @staticmethod
    def _merge_into(target: RawFinding, incoming: RawFinding) -> None:
        target.confidence = round(max(target.confidence, incoming.confidence), 3)
        detector_names = sorted(
            {
                name.strip()
                for source in (target.source_detector, incoming.source_detector)
                for name in source.split(",")
                if name.strip()
            }
        )
        target.source_detector = ",".join(detector_names) or target.source_detector
        target.validator_passed = target.validator_passed or incoming.validator_passed
        target.context_matched = target.context_matched or incoming.context_matched

        if incoming.source_context and (
            not target.source_context or len(incoming.source_context) > len(target.source_context)
        ):
            target.source_context = incoming.source_context

        if incoming.explanation:
            target_explanations = [part.strip() for part in target.explanation.split(" | ") if part.strip()]
            if incoming.explanation not in target_explanations:
                target.explanation = " | ".join(target_explanations + [incoming.explanation])

        if not target.chunk_source_type and incoming.chunk_source_type:
            target.chunk_source_type = incoming.chunk_source_type
        if not target.source_path and incoming.source_path:
            target.source_path = incoming.source_path
