# Developer Guide

## Purpose

This is the practical “where do I go next?” guide for contributors.

Use this file when you want to change behavior rather than just understand the architecture.

## If You Want To Work On PDF Extraction

Open:

- `pd_scanner/extractors/pdf_extractor.py`
- `pd_scanner/extractors/ocr_service.py`
- `pd_scanner/extractors/resource_router.py`
- `pd_scanner/workflows/pdf_workflow.py`
- `pd_scanner/tests/test_extractors.py`
- `pd_scanner/tests/test_multimodal_extraction.py`

Run:

```bash
python -m pd_scanner.cli.main pdf-scan --input "<path>" --output "<out>" --mode deep
```

Or use GUI:

- `PDF Scan` page

Look at:

- `output/debug/pdf_scan/pdf_workflow_preview.json`
- `scan.log`

What to inspect:

- `pdf_text` vs `pdf_image_ocr` vs `pdf_page_ocr`
- sparse-page OCR fallback
- embedded image OCR limits
- invalid PDF handling

## If You Want To Work On Structured Files

Open:

- `pd_scanner/extractors/csv_extractor.py`
- `pd_scanner/extractors/json_extractor.py`
- `pd_scanner/extractors/parquet_extractor.py`
- `pd_scanner/extractors/excel_extractor.py`
- `pd_scanner/workflows/structured_workflow.py`
- `pd_scanner/app/views/run_structured_scan.py`

Run preview mode from GUI:

- `Structured Files` page

Run CLI:

```bash
python -m pd_scanner.cli.main structured-scan --input "<path>" --output "<out>" --mode fast
```

Look at:

- `output/debug/structured_scan/structured_preview.json`

What to inspect:

- row limits
- sampled rows
- column names
- column hint metadata
- `.xls` vs `.xlsx` engine behavior

## If You Want To Work On OCR

Open:

- `pd_scanner/extractors/ocr_service.py`
- `pd_scanner/extractors/ocr_utils.py`
- `pd_scanner/extractors/resource_router.py`
- `pd_scanner/extractors/image_ocr_extractor.py`
- `pd_scanner/extractors/video_extractor.py`
- `pd_scanner/extractors/pdf_extractor.py`
- `pd_scanner/extractors/docx_extractor.py`
- `pd_scanner/extractors/html_extractor.py`

Check availability:

- GUI dashboard OCR status
- `ScanService.probe_ocr()`
- `get_ocr_status()`

Workflows using OCR:

- `image_scan`
- `video_scan`
- `pdf_scan` in deep mode
- embedded OCR inside DOCX/HTML/PDF

What to inspect:

- fast vs deep mode behavior
- warnings when OCR is unavailable
- limits such as max OCR calls

## If You Want To Work On GUI

Open:

- `pd_scanner/app/streamlit_app.py`
- `pd_scanner/app/state.py`
- `pd_scanner/app/ui_components.py`
- `pd_scanner/app/views/common.py`
- page file in `pd_scanner/app/views/`

Page files:

- `dashboard.py`
- `run_full_scan.py`
- `run_pdf_scan.py`
- `run_text_scan.py`
- `run_structured_scan.py`
- `run_image_ocr.py`
- `run_video_scan.py`
- `detector_lab.py`
- `reports.py`

Progress logic:

- `core/services.py` -> `ScanProgressTracker`
- `app/ui_components.py` -> `render_progress()`

State logic:

- `app/state.py` -> `BackgroundScanState`

Path-selection logic:

- `app/views/common.py`

## If You Want To Work On Detectors

Open:

- `pd_scanner/detectors/patterns.py`
- `pd_scanner/detectors/validators.py`
- `pd_scanner/detectors/maskers.py`
- `pd_scanner/detectors/context_rules.py`
- `pd_scanner/detectors/entity_detector.py`
- `pd_scanner/detectors/detection_pipeline.py`
- `pd_scanner/detectors/base.py`
- `pd_scanner/detectors/model_detector.py`

Run:

```bash
python -m pd_scanner.cli.main detector-lab --input "<workspace>" --output "<out>" --text "..."
```

Look at:

- `output/debug/detector_lab/detector_findings.json`

Add a new detector by:

1. inheriting from `BaseDetector`
2. returning `RawFinding`
3. wiring it into `DetectionPipeline`
4. optionally toggling via config

## If You Want To Add A New File Format

Recommended steps:

1. create a new extractor in `pd_scanner/extractors/`
2. return a proper `ExtractionResult`
3. emit meaningful `source_type` values
4. register the extractor in `scanner/file_dispatcher.py`
5. decide which workflows should include the suffix
6. update GUI inventory filters if needed
7. add tests
8. update developer docs

Questions to answer:

- is the file structured, text, OCR-heavy, or multimodal?
- should it participate in an existing workflow page or get a dedicated workflow?
- does it need embedded-resource routing?

## If You Want To Work On Reporting

Open:

- `pd_scanner/reporting/csv_report.py`
- `pd_scanner/reporting/json_report.py`
- `pd_scanner/reporting/markdown_report.py`
- `pd_scanner/workflows/reporting_workflow.py`
- `pd_scanner/app/views/reports.py`

Run:

```bash
python -m pd_scanner.cli.main build-report --input "<existing-output-dir>" --output "<existing-output-dir>"
```

Look at:

- `scan_report.csv`
- `scan_report.json`
- `scan_report.md`
- `summary.json`

## If You Want To Work On Lifecycle / Progress / Cancel

Open:

- `pd_scanner/core/lifecycle.py`
- `pd_scanner/core/services.py`
- `pd_scanner/app/state.py`
- `pd_scanner/app/ui_components.py`

Key things to understand:

- lifecycle manager enforces one active scan
- tracker persists `scan_state.json`
- GUI only requests cooperative stop
- workflows must periodically check `tracker.should_stop()`

## If You Want To Trace Data End-to-End

Start here:

1. `cli/main.py` or `app/streamlit_app.py`
2. workflow file
3. `workflows/single_file_workflow.py` or `core/pipeline.py`
4. `scanner/file_dispatcher.py`
5. extractor
6. `EntityDetector`
7. classifiers
8. reporting

This is the shortest path to understanding a runtime issue.

