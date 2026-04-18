# Workflows

## Overview

The project is organized around explicit workflow entrypoints instead of one monolithic scan path.

Implemented workflows:

- `full-scan`
- `pdf-scan`
- `text-scan`
- `structured-scan`
- `image-scan`
- `video-scan`
- `detector-lab`
- `build-report`

Each workflow is exposed through:

- CLI subcommand
- backend workflow function
- optional GUI page
- optional debug artifact directory

---

## Full Scan

### CLI

```bash
python -m pd_scanner.cli.main full-scan ...
```

Legacy mode without subcommand is still mapped to `full-scan`.

### Backend file

- `pd_scanner/workflows/full_scan_workflow.py`

### Uses

- `ScanService.run_scan()`
- `ScanPipeline`
- `walker.iter_files()`
- `file_dispatcher.get_extractor()`
- all supported extractors
- detector pipeline through `EntityDetector`
- classifiers
- report writers

### Debug artifacts

Generated in output root:

- `scan.log`
- `scan_state.json`
- `scan_report.csv`
- `scan_report.json`
- `scan_report.md`
- `summary.json`

### GUI page

- `Full Scan`

### Output

- full reporting set
- final file-level results
- progress state with `processed_by_type`

### Progress visibility

- `scan_state.json`
- Streamlit progress view
- `ScanProgressTracker`

### Route map

`CLI/GUI -> ScanService.run_scan -> ScanPipeline -> walker -> dispatcher -> extractor -> detector pipeline -> classifiers -> report writers`

---

## PDF Scan

### CLI

```bash
python -m pd_scanner.cli.main pdf-scan ...
```

### Backend file

- `pd_scanner/workflows/pdf_workflow.py`

### Extractors used

- `PDFExtractor`

### Debug artifacts

- `output/debug/pdf_scan/pdf_workflow_preview.json`

### GUI page

- `PDF Scan`

### Output

- `WorkflowResult` with PDF-only results
- extraction previews
- invalid PDF list in workflow metadata

### Progress visibility

- current file
- extractor name
- live preview payloads
- queue preview
- operator events

### Route map

`CLI/GUI -> run_pdf_workflow -> scan_single_path -> PDFExtractor -> ExtractionResult -> EntityDetector -> classifiers -> WorkflowResult`

---

## Text Scan

### CLI

```bash
python -m pd_scanner.cli.main text-scan ...
```

### Backend file

- `pd_scanner/workflows/text_workflow.py`

### Extractors used

- `DOCXExtractor`
- `RTFExtractor`
- `TXTExtractor`

### Debug artifacts

- `output/debug/text_scan/preview.json`

### GUI page

- `Text Documents`

### Output

- counts by type
- chunk counts
- extractor names
- sample chunk previews

### Progress visibility

- current file
- current extractor
- recent processed files
- live previews

### Route map

`CLI/GUI -> run_text_workflow -> scan_single_path -> DOCX/RTF/TXT extractor -> EntityDetector -> classifiers -> WorkflowResult`

---

## Structured Scan

### CLI

```bash
python -m pd_scanner.cli.main structured-scan ...
```

### Backend file

- `pd_scanner/workflows/structured_workflow.py`

### Extractors used

- `CSVExtractor`
- `JSONExtractor`
- `ParquetExtractor`
- `ExcelExtractor`

### Debug artifacts

- `output/debug/structured_scan/structured_preview.json`

### GUI page

- `Structured Files`

### Output

- structured file statistics
- row counts
- columns preview
- detected column hints
- chunk previews

### Progress visibility

- preview/full mode
- queue preview
- current structured file
- live extraction previews

### Route map

`CLI/GUI -> run_structured_workflow -> scan_single_path -> structured extractor -> EntityDetector -> classifiers -> WorkflowResult`

---

## Image Scan

### CLI

```bash
python -m pd_scanner.cli.main image-scan ...
```

### Backend file

- `pd_scanner/workflows/image_workflow.py`

### Extractors used

- `ImageOCRExtractor`

### Debug artifacts

- `output/debug/image_scan/image_preview.json`

### GUI page

- `Image OCR`

### Output

- OCR availability
- skipped count
- sample OCR previews

### Progress visibility

- current image
- OCR availability
- recent results

### Route map

`CLI/GUI -> run_image_workflow -> scan_single_path -> ImageOCRExtractor -> EntityDetector -> classifiers -> WorkflowResult`

---

## Video Scan

### CLI

```bash
python -m pd_scanner.cli.main video-scan ...
```

### Backend file

- `pd_scanner/workflows/video_workflow.py`

### Extractors used

- `VideoExtractor`

### Debug artifacts

- `output/debug/video_scan/video_preview.json`

### GUI page

- `Video Scan`

### Output

- OCR availability
- frame-step metadata
- sample previews

### Progress visibility

- current video
- sampled extraction previews

### Route map

`CLI/GUI -> run_video_workflow -> scan_single_path -> VideoExtractor -> EntityDetector -> classifiers -> WorkflowResult`

---

## Detector Lab

### CLI

```bash
python -m pd_scanner.cli.main detector-lab --text ...
python -m pd_scanner.cli.main detector-lab --text-file ...
```

### Backend file

- `pd_scanner/workflows/detector_workflow.py`

### Extractors used

- no file extractor required
- manual `ExtractionResult` is built from input text

### Debug artifacts

- `output/debug/detector_lab/detector_findings.json`

### GUI page

- `Detector Lab`

### Output

- findings count
- masked findings preview
- UZ result for synthetic detector-only file

### Progress visibility

- synchronous in GUI
- no long-running background scan required

### Route map

`CLI/GUI -> run_detector_workflow -> synthetic ExtractionResult -> EntityDetector -> classifiers -> WorkflowResult`

---

## Build Report

### CLI

```bash
python -m pd_scanner.cli.main build-report --input <existing-output-dir> ...
```

### Backend file

- `pd_scanner/workflows/reporting_workflow.py`

### Extractors used

- none

### Debug artifacts

- none generated by default
- reads existing `scan_report.json`

### GUI page

- `Reports`

### Output

- deserialized report summary
- file results table
- download buttons if report artifacts exist

### Progress visibility

- synchronous reload

### Route map

`CLI/GUI -> run_reporting_workflow -> ScanService.load_scan_results -> deserialize summary/results -> WorkflowResult`

---

## Workflow Selection Map

| Workflow | CLI subcommand | Backend file | GUI page |
|---|---|---|---|
| Full Scan | `full-scan` | `workflows/full_scan_workflow.py` | `Full Scan` |
| PDF Scan | `pdf-scan` | `workflows/pdf_workflow.py` | `PDF Scan` |
| Text Scan | `text-scan` | `workflows/text_workflow.py` | `Text Documents` |
| Structured Scan | `structured-scan` | `workflows/structured_workflow.py` | `Structured Files` |
| Image Scan | `image-scan` | `workflows/image_workflow.py` | `Image OCR` |
| Video Scan | `video-scan` | `workflows/video_workflow.py` | `Video Scan` |
| Detector Lab | `detector-lab` | `workflows/detector_workflow.py` | `Detector Lab` |
| Build Report | `build-report` | `workflows/reporting_workflow.py` | `Reports` |

