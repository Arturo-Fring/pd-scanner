"""Context heuristics for explainable scoring."""

from __future__ import annotations

from pd_scanner.core.config import AppConfig


def column_context_match(entity_type: str, columns: tuple[str, ...], config: AppConfig) -> bool:
    """Return True when column headers support an entity type."""
    hints = config.detection.column_hints.get(entity_type, ())
    lowered_columns = [column.lower() for column in columns]
    return any(any(hint in column for hint in hints) for column in lowered_columns)


def text_contains_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    """Return True when any keyword is present."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def score_match(
    *,
    base_score: float,
    config: AppConfig,
    has_column_context: bool,
    has_keyword_context: bool,
    validated: bool,
) -> float:
    """Combine explainable score components."""
    score = base_score
    if has_column_context:
        score += config.detection.column_context_boost
    if has_keyword_context:
        score += config.detection.keyword_context_boost
    if validated:
        score += config.detection.validation_boost
    return min(score, 0.99)

