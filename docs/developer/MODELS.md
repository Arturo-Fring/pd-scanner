# Models

## Core Models

Defined mainly in:

- `pd_scanner/core/models.py`
- `pd_scanner/core/workflow_models.py`

## `ExtractedChunk`

Used between extraction and detection.

Fields:

- `text`
- `source_type`
- `source_path`
- `location`
- `row_index`
- `columns`
- `metadata`

Compatibility note:

- `.context` is preserved as a backward-compatible alias to `metadata`

## `ExtractionResult`

Used as extractor output.

Fields:

- `file_type`
- `extracted_text_chunks`
- `table_records`
- `metadata`
- `warnings`

## `RawFinding`

Used between detection and aggregation.

Fields:

- entity identity and group
- raw/normalized/masked values
- confidence
- explanation
- source context
- `row_key`
- `start` / `end`
- `source_detector`
- `chunk_source_type`
- `source_path`
- validation and context flags

## `DetectedEntity`

Used as aggregated file-level entity statistics.

Fields:

- `entity_type`
- `group`
- `count`
- `masked_examples`
- `confidence`
- `source_context`
- `explanations`

## `FileScanResult`

One per processed file.

Fields:

- path
- file type
- status
- error message
- detected entities
- category counts
- group flags
- volume estimate
- UZ
- processing time
- metadata
- warnings

## `ReportSummary`

Aggregated run-level summary.

Fields:

- total files
- processed files
- files with PD
- files by UZ
- entity stats
- errors
- unsupported count
- warnings count
- total processing time

## `ReportArtifacts`

Holds resolved paths to:

- output dir
- CSV report
- JSON report
- Markdown report
- summary file
- log file
- state file

## Workflow Models

### `WorkflowPreview`

Compact debug/preview payload.

### `WorkflowResult`

Unified return type for workflow entrypoints.

Fields:

- `workflow_type`
- `status`
- `summary`
- `results`
- `errors`
- `artifacts`
- `previews`
- `metadata`

