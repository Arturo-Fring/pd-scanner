# Detectors

## Overview

Detection is organized as a composable pipeline, even though the current production logic is still rule-based.

Main modules:

- `base.py`
- `entity_detector.py`
- `model_detector.py`
- `detection_pipeline.py`
- `patterns.py`
- `validators.py`
- `maskers.py`
- `context_rules.py`

## Detector Stack

### `BaseDetector`

Defines the common contract:

```python
detect(chunks: list[ExtractedChunk]) -> list[RawFinding]
```

Use it when:

- adding a new detector implementation
- integrating ML-based detectors later

### `RuleBasedDetector`

Current main detector implementation.

Lives in:

- `pd_scanner/detectors/entity_detector.py`

Responsibilities:

- regex-driven matching
- context scoring
- validator calls
- explainable confidence construction
- chunk-level hit generation as `RawFinding`

### `ModelDetector`

Current status:

- placeholder / stub

Purpose:

- reserve architecture for ML detector integration
- allow future Presidio / GLiNER / local NER integration without redesigning the pipeline

### `DetectionPipeline`

Responsibilities:

- run multiple detectors in sequence
- merge duplicate findings
- preserve source detector provenance

## Current Runtime Behavior

At the moment:

- `EntityDetector` acts as a facade
- internally it builds a `DetectionPipeline`
- by default the pipeline uses `RuleBasedDetector`
- `ModelDetector` is added only if config enables it

This keeps backward compatibility for the rest of the codebase.

## Merge Logic

Duplicate findings are merged by:

- `entity_type`
- `row_key`
- `start`
- `end`

Fallback merge key if span is unavailable:

- `entity_type`
- `row_key`
- `normalized_value`

On merge:

- confidence becomes the max of conflicting findings
- `source_detector` names are combined
- context/validator flags are OR-merged
- longer or richer context may replace a weaker one
- explanations are appended instead of overwritten

## `RawFinding`

`RawFinding` is the detector-internal record before file-level aggregation.

Important fields:

- `entity_type`
- `group`
- `original_value`
- `normalized_value`
- `masked_value`
- `confidence`
- `explanation`
- `source_context`
- `row_key`
- `start` / `end`
- `source_detector`
- `chunk_source_type`
- `source_path`

This structure is the right place to preserve detector provenance for future hybrid pipelines.

## Aggregation Into `DetectedEntity`

After raw findings are produced:

- findings are grouped by `entity_type`
- examples are deduplicated
- explanations are deduplicated
- contexts are deduplicated
- average confidence is computed for the aggregated entity

The result is `DetectedEntity`, which is later stored in `FileScanResult`.

## Validators

Defined in:

- `pd_scanner/detectors/validators.py`

Examples:

- `normalize_phone`
- `luhn_check`
- `validate_snils`
- `validate_inn`
- `maybe_validate_bik`

Role:

- reduce false positives
- raise confidence when validation passes

## Maskers

Defined in:

- `pd_scanner/detectors/maskers.py`

Role:

- ensure reports and previews never expose raw sensitive values
- sanitize snippets before they reach output artifacts

Typical outputs:

- partial phone masking
- partial email masking
- last-4 card masking
- partial passport/SNILS/INN masking

## Context Rules

Defined in:

- `pd_scanner/detectors/context_rules.py`

Role:

- score regex hits using:
  - column/header hints
  - nearby keyword context
  - validation signals

This module is one of the main false-positive control points.

## Patterns

Defined in:

- `pd_scanner/detectors/patterns.py`

Contains:

- regexes for direct identifiers
- helper expressions for context-based entities

When adding a new entity type, this is usually the first file to touch.

## How to Add an ML Detector

Recommended path:

1. implement a new class inheriting `BaseDetector`
2. convert model predictions into `RawFinding`
3. set `source_detector` to the model name
4. preserve `start/end` if the model provides spans
5. enable it via config
6. append it to `DetectionPipeline`

Important:

- do not bypass the pipeline
- do not emit raw unmasked output into reports
- use `RawFinding` so merge logic and downstream aggregation continue to work

## Recommended Extension Boundaries

If you want to:

- add a regex: edit `patterns.py`
- add a validator: edit `validators.py`
- add masking rule: edit `maskers.py`
- change scoring: edit `context_rules.py`
- add a detector implementation: edit `base.py`, new detector module, and `detection_pipeline.py` / `entity_detector.py`

