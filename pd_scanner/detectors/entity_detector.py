"""Explainable detector orchestration with a composable detector pipeline."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Callable

from pd_scanner.classifiers.category_mapper import entity_group
from pd_scanner.core.config import AppConfig
from pd_scanner.core.models import DetectedEntity, ExtractionResult, ExtractedChunk, RawFinding
from pd_scanner.core.utils import shorten
from pd_scanner.detectors import patterns
from pd_scanner.detectors.base import BaseDetector
from pd_scanner.detectors.context_rules import column_context_match, score_match, text_contains_keywords
from pd_scanner.detectors.detection_pipeline import DetectionPipeline
from pd_scanner.detectors.maskers import sanitize_snippet
from pd_scanner.detectors.model_detector import ModelDetector
from pd_scanner.detectors.validators import (
    digits_only,
    luhn_check,
    mask_value,
    maybe_validate_bik,
    normalize_phone,
    validate_inn,
    validate_snils,
)


class RuleBasedDetector(BaseDetector):
    """Existing regex/context detector packaged behind the BaseDetector interface."""

    name = "rule_based"

    def detect(self, chunks: list[ExtractedChunk]) -> list[RawFinding]:
        findings: list[RawFinding] = []
        for chunk in chunks:
            findings.extend(self._detect_in_chunk(chunk))
        return [finding for finding in findings if finding.confidence >= self.config.detection.min_confidence]

    def _detect_in_chunk(self, chunk: ExtractedChunk) -> list[RawFinding]:
        text = chunk.text or ""
        if not text.strip():
            return []
        findings: list[RawFinding] = []
        findings.extend(self._detect_regex(chunk, "email", patterns.EMAIL_RE, 0.68))
        findings.extend(
            self._detect_regex(
                chunk,
                "phone",
                patterns.PHONE_RE,
                0.55,
                normalizer=normalize_phone,
                validator=lambda value: normalize_phone(value) is not None,
                keyword_context=("С‚РµР»РµС„РѕРЅ", "phone", "mobile", "РєРѕРЅС‚Р°РєС‚"),
            )
        )
        findings.extend(
            self._detect_regex(
                chunk,
                "passport_rf",
                patterns.PASSPORT_RF_RE,
                0.5,
                normalizer=lambda value: digits_only(value),
                validator=lambda value: len(digits_only(value)) == 10,
                required_context=("РїР°СЃРїРѕСЂС‚", "passport", "СЃРµСЂРёСЏ", "РЅРѕРјРµСЂ РїР°СЃРїРѕСЂС‚Р°", "РєРѕРґ РїРѕРґСЂР°Р·РґРµР»РµРЅРёСЏ"),
            )
        )
        findings.extend(
            self._detect_regex(
                chunk,
                "snils",
                patterns.SNILS_RE,
                0.58,
                normalizer=lambda value: digits_only(value),
                validator=validate_snils,
            )
        )
        findings.extend(
            self._detect_regex(
                chunk,
                "inn",
                patterns.INN_RE,
                0.45,
                normalizer=lambda value: digits_only(value),
                validator=validate_inn,
            )
        )
        findings.extend(
            self._detect_regex(
                chunk,
                "bank_card",
                patterns.BANK_CARD_RE,
                0.52,
                normalizer=lambda value: digits_only(value),
                validator=luhn_check,
                keyword_context=("РєР°СЂС‚Р°", "card", "pan", "visa", "mastercard", "РјРёСЂ"),
            )
        )
        findings.extend(
            self._detect_regex(
                chunk,
                "bank_account",
                patterns.BANK_ACCOUNT_RE,
                0.42,
                normalizer=lambda value: digits_only(value),
                validator=lambda value: len(digits_only(value)) == 20,
                required_context=("СЃС‡РµС‚", "СЂ/СЃ", "СЂР°СЃС‡РµС‚РЅС‹Р№ СЃС‡РµС‚", "account"),
            )
        )
        findings.extend(
            self._detect_regex(
                chunk,
                "bik",
                patterns.BIK_RE,
                0.35,
                normalizer=lambda value: digits_only(value),
                validator=maybe_validate_bik,
                required_context=("Р±РёРє", "bik"),
            )
        )
        findings.extend(
            self._detect_regex(
                chunk,
                "driver_license",
                patterns.DRIVER_LICENSE_RE,
                0.4,
                normalizer=lambda value: digits_only(value),
                validator=lambda value: len(digits_only(value)) == 10,
                required_context=("РІРѕРґРёС‚РµР»СЊ", "driver", "license", "СѓРґРѕСЃС‚РѕРІРµСЂРµРЅРёРµ"),
            )
        )
        findings.extend(self._detect_cvv(chunk))
        findings.extend(self._detect_mrz(chunk))
        findings.extend(self._detect_dates(chunk))
        findings.extend(self._detect_fio(chunk))
        findings.extend(self._detect_address(chunk))
        findings.extend(self._detect_birth_place(chunk))
        findings.extend(self._detect_keyword_categories(chunk))
        return findings

    def _detect_regex(
        self,
        chunk: ExtractedChunk,
        entity_type: str,
        regex: object,
        base_score: float,
        *,
        normalizer: Callable[[str], str | None] | None = None,
        validator: Callable[[str], bool] | None = None,
        keyword_context: tuple[str, ...] = (),
        required_context: tuple[str, ...] = (),
    ) -> list[RawFinding]:
        findings: list[RawFinding] = []
        text = chunk.text
        has_column_context = column_context_match(entity_type, chunk.columns, self.config)
        global_keyword_context = text_contains_keywords(text, keyword_context or required_context)
        for match in regex.finditer(text):
            matched = match.group(1) if match.groups() else match.group(0)
            normalized = normalizer(matched) if normalizer else matched.strip()
            if not normalized:
                continue
            window_start = max(0, match.start() - self.config.runtime.snippet_radius)
            window_end = min(len(text), match.end() + self.config.runtime.snippet_radius)
            window = text[window_start:window_end]
            local_context = text_contains_keywords(window, keyword_context or required_context)
            has_keyword_context = global_keyword_context or local_context
            if required_context and not (has_column_context or has_keyword_context):
                continue
            validated = validator(matched) if validator else False
            score = score_match(
                base_score=base_score,
                config=self.config,
                has_column_context=has_column_context,
                has_keyword_context=has_keyword_context,
                validated=validated,
            )
            explanation = self._build_explanation(
                entity_type=entity_type,
                has_column_context=has_column_context,
                has_keyword_context=has_keyword_context,
                validated=validated,
            )
            findings.append(
                RawFinding(
                    entity_type=entity_type,
                    group=entity_group(entity_type),
                    original_value=matched,
                    normalized_value=normalized,
                    masked_value=mask_value(matched, entity_type),
                    confidence=score,
                    explanation=explanation,
                    source_context=sanitize_snippet(window.replace(matched, mask_value(matched, entity_type))),
                    row_key=self._row_key(chunk),
                    start=match.start(),
                    end=match.end(),
                    source_detector=self.name,
                    chunk_source_type=chunk.source_type,
                    source_path=chunk.source_path,
                    validator_passed=validated,
                    context_matched=has_column_context or has_keyword_context,
                )
            )
        return findings

    def _detect_dates(self, chunk: ExtractedChunk) -> list[RawFinding]:
        findings: list[RawFinding] = []
        entity_type = "birth_date"
        has_column_context = column_context_match(entity_type, chunk.columns, self.config)
        for match in patterns.DATE_RE.finditer(chunk.text):
            snippet = chunk.text[max(0, match.start() - 35) : min(len(chunk.text), match.end() + 35)]
            has_keyword_context = text_contains_keywords(
                snippet,
                ("РґР°С‚Р° СЂРѕР¶РґРµРЅРёСЏ", "СЂРѕРґРёР»СЃСЏ", "СЂРѕРґРёР»Р°СЃСЊ", "birth", "dob"),
            )
            if not (has_column_context or has_keyword_context):
                continue
            value = match.group(0)
            score = score_match(
                base_score=0.4,
                config=self.config,
                has_column_context=has_column_context,
                has_keyword_context=has_keyword_context,
                validated=False,
            )
            findings.append(
                RawFinding(
                    entity_type=entity_type,
                    group=entity_group(entity_type),
                    original_value=value,
                    normalized_value=value,
                    masked_value="**.**." + value[-4:],
                    confidence=score,
                    explanation=self._build_explanation(
                        entity_type=entity_type,
                        has_column_context=has_column_context,
                        has_keyword_context=has_keyword_context,
                        validated=False,
                    ),
                    source_context=sanitize_snippet(snippet.replace(value, "**.**." + value[-4:])),
                    row_key=self._row_key(chunk),
                    start=match.start(),
                    end=match.end(),
                    source_detector=self.name,
                    chunk_source_type=chunk.source_type,
                    source_path=chunk.source_path,
                    context_matched=has_column_context or has_keyword_context,
                )
            )
        return findings

    def _detect_fio(self, chunk: ExtractedChunk) -> list[RawFinding]:
        findings: list[RawFinding] = []
        has_column_context = column_context_match("fio", chunk.columns, self.config)
        for regex in (patterns.FIO_CONTEXT_RE, patterns.FIO_VALUE_RE):
            for match in regex.finditer(chunk.text):
                value = match.group(1) if match.groups() else match.group(0)
                if len(value.split()) < 2:
                    continue
                snippet = chunk.text[max(0, match.start() - 40) : min(len(chunk.text), match.end() + 40)]
                has_keyword_context = text_contains_keywords(
                    snippet, ("С„РёРѕ", "С„Р°РјРёР»РёСЏ", "РѕС‚С‡РµСЃС‚РІРѕ", "surname", "fullname")
                )
                if regex is patterns.FIO_VALUE_RE and not (has_column_context or has_keyword_context):
                    continue
                score = score_match(
                    base_score=0.35 if regex is patterns.FIO_VALUE_RE else 0.55,
                    config=self.config,
                    has_column_context=has_column_context,
                    has_keyword_context=has_keyword_context,
                    validated=False,
                )
                findings.append(
                    RawFinding(
                        entity_type="fio",
                        group=entity_group("fio"),
                        original_value=value,
                        normalized_value=value.lower(),
                        masked_value=mask_value(value, "fio"),
                        confidence=score,
                        explanation=self._build_explanation(
                            entity_type="fio",
                            has_column_context=has_column_context,
                            has_keyword_context=has_keyword_context,
                            validated=False,
                        ),
                        source_context=sanitize_snippet(snippet.replace(value, mask_value(value, "fio"))),
                        row_key=self._row_key(chunk),
                        start=match.start(),
                        end=match.end(),
                        source_detector=self.name,
                        chunk_source_type=chunk.source_type,
                        source_path=chunk.source_path,
                        context_matched=has_column_context or has_keyword_context,
                    )
                )
        return findings

    def _detect_address(self, chunk: ExtractedChunk) -> list[RawFinding]:
        findings: list[RawFinding] = []
        has_column_context = column_context_match("address", chunk.columns, self.config)
        for match in patterns.ADDRESS_RE.finditer(chunk.text):
            value = match.group(1).strip(" .,:;")
            if len(value) < 8:
                continue
            findings.append(
                RawFinding(
                    entity_type="address",
                    group=entity_group("address"),
                    original_value=value,
                    normalized_value=value.lower(),
                    masked_value=mask_value(value, "address"),
                    confidence=score_match(
                        base_score=0.5,
                        config=self.config,
                        has_column_context=has_column_context,
                        has_keyword_context=True,
                        validated=False,
                    ),
                    explanation=self._build_explanation(
                        entity_type="address",
                        has_column_context=has_column_context,
                        has_keyword_context=True,
                        validated=False,
                    ),
                    source_context=sanitize_snippet(shorten(match.group(0))),
                    row_key=self._row_key(chunk),
                    start=match.start(),
                    end=match.end(),
                    source_detector=self.name,
                    chunk_source_type=chunk.source_type,
                    source_path=chunk.source_path,
                    context_matched=True,
                )
            )
        return findings

    def _detect_birth_place(self, chunk: ExtractedChunk) -> list[RawFinding]:
        findings: list[RawFinding] = []
        has_column_context = column_context_match("birth_place", chunk.columns, self.config)
        for match in patterns.BIRTH_PLACE_RE.finditer(chunk.text):
            value = match.group(1).strip(" .,:;")
            findings.append(
                RawFinding(
                    entity_type="birth_place",
                    group=entity_group("birth_place"),
                    original_value=value,
                    normalized_value=value.lower(),
                    masked_value=mask_value(value, "birth_place"),
                    confidence=score_match(
                        base_score=0.5,
                        config=self.config,
                        has_column_context=has_column_context,
                        has_keyword_context=True,
                        validated=False,
                    ),
                    explanation=self._build_explanation(
                        entity_type="birth_place",
                        has_column_context=has_column_context,
                        has_keyword_context=True,
                        validated=False,
                    ),
                    source_context=sanitize_snippet(shorten(match.group(0))),
                    row_key=self._row_key(chunk),
                    start=match.start(),
                    end=match.end(),
                    source_detector=self.name,
                    chunk_source_type=chunk.source_type,
                    source_path=chunk.source_path,
                    context_matched=True,
                )
            )
        return findings

    def _detect_cvv(self, chunk: ExtractedChunk) -> list[RawFinding]:
        findings: list[RawFinding] = []
        has_column_context = column_context_match("cvv", chunk.columns, self.config)
        for match in patterns.CVV_CONTEXT_RE.finditer(chunk.text):
            value = match.group(1)
            findings.append(
                RawFinding(
                    entity_type="cvv",
                    group=entity_group("cvv"),
                    original_value=value,
                    normalized_value=value,
                    masked_value=mask_value(value, "cvv"),
                    confidence=score_match(
                        base_score=0.7,
                        config=self.config,
                        has_column_context=has_column_context,
                        has_keyword_context=True,
                        validated=len(value) in {3, 4},
                    ),
                    explanation=self._build_explanation(
                        entity_type="cvv",
                        has_column_context=has_column_context,
                        has_keyword_context=True,
                        validated=len(value) in {3, 4},
                    ),
                    source_context=sanitize_snippet(shorten(match.group(0).replace(value, "***"))),
                    row_key=self._row_key(chunk),
                    start=match.start(),
                    end=match.end(),
                    source_detector=self.name,
                    chunk_source_type=chunk.source_type,
                    source_path=chunk.source_path,
                    validator_passed=len(value) in {3, 4},
                    context_matched=True,
                )
            )
        return findings

    def _detect_mrz(self, chunk: ExtractedChunk) -> list[RawFinding]:
        findings: list[RawFinding] = []
        has_column_context = column_context_match("mrz", chunk.columns, self.config)
        for match in patterns.MRZ_LINE_RE.finditer(chunk.text):
            value = match.group(0)
            if value.count("<") < 2:
                continue
            findings.append(
                RawFinding(
                    entity_type="mrz",
                    group=entity_group("mrz"),
                    original_value=value,
                    normalized_value=value,
                    masked_value=mask_value(value, "mrz"),
                    confidence=score_match(
                        base_score=0.7,
                        config=self.config,
                        has_column_context=has_column_context,
                        has_keyword_context="<<" in value or value.startswith("P<"),
                        validated=True,
                    ),
                    explanation=self._build_explanation(
                        entity_type="mrz",
                        has_column_context=has_column_context,
                        has_keyword_context=True,
                        validated=True,
                    ),
                    source_context=sanitize_snippet(shorten(value)),
                    row_key=self._row_key(chunk),
                    start=match.start(),
                    end=match.end(),
                    source_detector=self.name,
                    chunk_source_type=chunk.source_type,
                    source_path=chunk.source_path,
                    validator_passed=True,
                    context_matched=True,
                )
            )
        return findings

    def _detect_keyword_categories(self, chunk: ExtractedChunk) -> list[RawFinding]:
        findings: list[RawFinding] = []
        lowered = chunk.text.lower()
        for entity_type, keywords in self.config.detection.special_keywords.items():
            for keyword in keywords:
                if keyword not in lowered:
                    continue
                index = lowered.index(keyword)
                snippet = chunk.text[max(0, index - 40) : min(len(chunk.text), index + len(keyword) + 40)]
                findings.append(
                    RawFinding(
                        entity_type=entity_type,
                        group=entity_group(entity_type),
                        original_value=keyword,
                        normalized_value=keyword,
                        masked_value=keyword,
                        confidence=0.88,
                        explanation=f"Keyword/context rule matched for {entity_type}.",
                        source_context=sanitize_snippet(shorten(snippet)),
                        row_key=self._row_key(chunk),
                        start=index,
                        end=index + len(keyword),
                        source_detector=self.name,
                        chunk_source_type=chunk.source_type,
                        source_path=chunk.source_path,
                        context_matched=True,
                    )
                )
        return findings

    def _build_explanation(
        self,
        *,
        entity_type: str,
        has_column_context: bool,
        has_keyword_context: bool,
        validated: bool,
    ) -> str:
        parts = [f"{entity_type}: regex/heuristic match"]
        if has_column_context:
            parts.append("column/header context matched")
        if has_keyword_context:
            parts.append("nearby text context matched")
        if validated:
            parts.append("validator passed")
        return "; ".join(parts)

    @staticmethod
    def _row_key(chunk: ExtractedChunk) -> str | None:
        if chunk.row_index is not None:
            return f"row:{chunk.row_index}"
        if chunk.location:
            if isinstance(chunk.location, str):
                return chunk.location
            return json.dumps(chunk.location, sort_keys=True, ensure_ascii=False)
        return None


class EntityDetector:
    """Facade preserving the existing API while delegating to the detection pipeline."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        detectors: list[BaseDetector] = [RuleBasedDetector(config)]
        if config.detection.enable_model_detector:
            detectors.append(ModelDetector(config))
        self.pipeline = DetectionPipeline(detectors)

    def detect(self, extraction: ExtractionResult) -> tuple[list[RawFinding], list[DetectedEntity], dict[str, int]]:
        """Run the configured detector pipeline over an extraction result."""
        findings = self.pipeline.detect(extraction.extracted_text_chunks)
        entities, counts = self._aggregate(findings)
        return findings, entities, counts

    def _aggregate(self, findings: list[RawFinding]) -> tuple[list[DetectedEntity], dict[str, int]]:
        grouped: dict[str, list[RawFinding]] = defaultdict(list)
        counts: dict[str, int] = defaultdict(int)
        for finding in findings:
            grouped[finding.entity_type].append(finding)
            counts[finding.entity_type] += 1

        entities: list[DetectedEntity] = []
        for entity_type, items in grouped.items():
            unique_examples: list[str] = []
            unique_contexts: list[str] = []
            unique_explanations: list[str] = []
            seen_examples: set[str] = set()
            seen_contexts: set[str] = set()
            seen_explanations: set[str] = set()
            for item in items:
                if item.masked_value not in seen_examples:
                    seen_examples.add(item.masked_value)
                    unique_examples.append(item.masked_value)
                if item.source_context and item.source_context not in seen_contexts:
                    seen_contexts.add(item.source_context)
                    unique_contexts.append(item.source_context)
                if item.explanation not in seen_explanations:
                    seen_explanations.add(item.explanation)
                    unique_explanations.append(item.explanation)
            entities.append(
                DetectedEntity(
                    entity_type=entity_type,
                    group=items[0].group,
                    count=len(items),
                    masked_examples=unique_examples[:5],
                    confidence=round(sum(item.confidence for item in items) / len(items), 3),
                    source_context=unique_contexts[:3],
                    explanations=unique_explanations[:3],
                )
            )
        entities.sort(key=lambda entity: (-entity.count, entity.entity_type))
        return entities, dict(counts)
