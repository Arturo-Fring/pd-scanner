# pd_scanner

`pd_scanner` is a local engineering platform for personal-data discovery in mixed corporate file storages. The project is organized around reusable backend services and separate workflows so you can run, debug, and demonstrate:

- full recursive scan
- PDF workflow
- structured-data workflow
- image OCR workflow
- video workflow
- detector lab
- report viewing / report rebuild workflow

The current refactor pass focuses on structure, runtime stability, scan lifecycle control, log hygiene, and GUI ergonomics. It does not try to radically change the detection model.

## What Is Already Implemented

Reusable backend layers already existed and were preserved:

- extractors
- detector / validation logic
- UZ classification
- report writers
- CLI/Streamlit entrypoints

The engineering pass adds the missing coordination layer:

- explicit workflow layer
- shared lifecycle manager
- single-active-scan policy
- aggregated warning handling
- workflow-oriented CLI subcommands
- workflow-oriented Streamlit pages
- intermediate debug artifacts per workflow

## Multimodal Extraction Flow

Extraction is no longer limited to a single flat text payload per document. The backend now follows a compositional flow:

- document file
- structural parsing
- embedded resource discovery
- resource routing
- unified `ExtractedChunk` list

This keeps the external pipeline stable:

- file
- extractor
- chunks
- detector
- report

but makes each extractor smarter internally.

Embedded resources currently covered:

- PDF text layer as `pdf_text`
- embedded PDF images as `pdf_image_ocr`
- full-page PDF OCR fallback as `pdf_page_ocr`
- DOCX paragraphs as `docx_paragraph`
- DOCX table cells as `docx_table_cell`
- embedded DOCX images as `docx_image_ocr`
- HTML body text as `html_text`
- HTML image alt/title text as `html_alt_text`
- HTML links as `html_link`
- HTML meta tags as `html_metadata`
- local HTML images as `html_image_ocr`

OCR is centralized through a shared `OCRService`, so PDF, DOCX, HTML, image, and video workflows all use the same OCR availability and runtime policy.

Performance guards:

- `max_embedded_images_per_file`
- `max_ocr_calls_per_file`
- fast mode disables OCR-heavy embedded-resource processing

## Project Structure

```text
hack/
├── README.md
├── requirements.txt
├── pd_scanner/
│   ├── app/
│   │   ├── views/
│   │   ├── state.py
│   │   ├── streamlit_app.py
│   │   └── ui_components.py
│   ├── classifiers/
│   ├── cli/
│   │   ├── common.py
│   │   ├── detect_cli.py
│   │   ├── image_cli.py
│   │   ├── main.py
│   │   ├── pdf_cli.py
│   │   ├── report_cli.py
│   │   ├── structured_cli.py
│   │   └── video_cli.py
│   ├── core/
│   │   ├── config.py
│   │   ├── lifecycle.py
│   │   ├── logging_utils.py
│   │   ├── models.py
│   │   ├── pipeline.py
│   │   ├── services.py
│   │   ├── utils.py
│   │   └── workflow_models.py
│   ├── workflows/
│   │   ├── detector_workflow.py
│   │   ├── full_scan_workflow.py
│   │   ├── helpers.py
│   │   ├── image_workflow.py
│   │   ├── pdf_workflow.py
│   │   ├── reporting_workflow.py
│   │   ├── single_file_workflow.py
│   │   ├── structured_workflow.py
│   │   └── video_workflow.py
│   ├── scanner/
│   ├── extractors/
│   ├── detectors/
│   ├── reporting/
│   └── __init__.py
└── tests/
```

## Workflows

### Full Scan

Main recursive scan across all supported formats.

Uses:

- recursive walker
- extractor dispatch
- detector aggregation
- UZ classification
- CSV/JSON/Markdown reports

### PDF Workflow

Dedicated workflow for PDF debugging and operator review.

Shows:

- page count
- OCR fallback usage
- invalid PDF handling
- sample extracted text chunks
- preview artifacts under `output/debug/pdf_scan`

### Structured Data Workflow

Dedicated workflow for:

- CSV
- JSON
- JSONL
- Parquet
- XLS
- XLSX

Shows:

- sample rows
- columns
- structured row counts
- extraction metadata
- preview artifacts under `output/debug/structured_scan`

### Text Documents Workflow

Dedicated workflow for:

- DOCX
- RTF
- TXT

Unlike `PDF Workflow`, this path is for formats that already expose readable text through existing extractors. Unlike `Structured Data Workflow`, it focuses on paragraph/body chunks rather than table-oriented previews.

Shows:

- docx/rtf/txt counts
- sample extracted text chunks
- chunk counts and extractor names
- preview artifacts under `output/debug/text_scan`

### Image OCR Workflow

Dedicated workflow for:

- JPG
- JPEG
- PNG
- GIF
- TIF
- TIFF

Shows:

- OCR availability
- OCR runtime summary before start
- OCR mode behavior
- extracted sample chunks
- debug artifacts under `output/debug/image_scan`

### Video Workflow

Dedicated workflow for MP4 processing.

Shows:

- frame step config
- sampled-frame metadata
- OCR availability
- OCR warning summaries instead of raw frame-level spam
- debug artifacts under `output/debug/video_scan`

### Detector Lab

Detector-only workflow for manual text or a plain-text file.

Useful for:

- validating patterns and validators
- explaining confidence / masking
- iterating on detector behavior without full scan

Writes debug findings into `output/debug/detector_lab`.

### Reporting Workflow

Loads and views existing `scan_report.json` artifacts without rerunning extraction.

Useful for:

- reviewing old runs
- re-opening results in GUI
- separating scan runtime from report analysis

## Scan Lifecycle Policy

The project now follows a strict single-active-scan policy.

- only one active scan workflow can run at a time
- the lifecycle manager blocks accidental concurrent background scans
- Streamlit disables start buttons during an active scan
- Streamlit exposes a dedicated `Stop / Cancel` control for long-running workflows
- cancellation is cooperative: the current file/batch finishes, then the workflow moves to `cancelled`
- `scan_state.json` reflects workflow type, scan id, timestamps, counters, and final status
- failed runs move to `failed`, not a stuck `running`

This policy applies to:

- full scan
- pdf scan
- text scan
- structured scan
- image scan
- video scan

## Logging Hygiene

There are now two levels of runtime visibility:

### Operator-facing progress

Used in Streamlit and `scan_state.json`.

Shows:

- workflow started
- files discovered
- OCR backend initialization and availability checks for OCR-heavy workflows
- processed counter
- current file
- current file type and extractor name
- current stage
- processed-by-type counters
- queue preview and recent processed files
- live preview snippets and artifact paths when the workflow publishes them
- compact recent events
- aggregated warning counters, including OCR runtime summaries
- workflow finished / failed

### Technical log

Stored in `scan.log`.

Can contain detailed parser/runtime information and tracebacks.

Repeated expected warnings are aggregated instead of flooding the operator feed. For example:

- `Image OCR skipped in fast mode`
- `DOC support is best-effort binary text extraction`
- `PaddleOCR inference runtime failed; OCR disabled for the remaining items.`

These are counted and summarized instead of being surfaced as hundreds of live warnings.

## Fast vs Deep Mode

`fast` mode:

- prioritizes speed
- disables OCR-heavy steps by design
- avoids operator log spam for expected OCR skips

`deep` mode:

- enables OCR where supported
- uses OCR for scanned PDFs, images, and video frames when available
- shows OCR runtime summary in the GUI before start, including offline-only behavior and OCR limits

## Extractor Stabilization Notes

### PDF

- controlled invalid PDF handling
- no post-close access to PyMuPDF document internals
- OCR fallback only when appropriate
- embedded images can now produce `pdf_image_ocr` chunks

### Excel

- `.xls` uses `xlrd`
- `.xlsx` uses `openpyxl`
- if the required engine is missing, the workflow returns a controlled runtime error

### OCR

- centralized OCR availability checks
- GUI shows OCR status clearly
- fast mode skips OCR-heavy steps by design
- PaddleOCR runtime failures are normalized and aggregated in the GUI while full details stay in `scan.log`
- offline runtime is preserved by requiring local OCR assets instead of downloading them during scans

### Detector Pipeline

Detection is prepared for hybrid rule-based + model-based operation:

- `RuleBasedDetector` preserves the current explainable regex/context logic
- `ModelDetector` is added as a stub extension point for future ML integrations such as Presidio or GLiNER
- `DetectionPipeline` runs detectors and merges duplicate hits by entity type and span

This means future ML detectors can be added without replacing the current rule-based layer.

## Intermediate Artifacts

Workflow-specific debug artifacts are written under:

```text
output/debug/
```

Examples:

- `output/debug/pdf_scan`
- `output/debug/structured_scan`
- `output/debug/image_scan`
- `output/debug/video_scan`
- `output/debug/detector_lab`

These artifacts are intentionally compact and preview-oriented.

## Installation

```powershell
conda activate torchlab311
cd C:\Coding\pytorchlabs\hack
python -m pip install -r requirements.txt
```

## OCR / Tesseract

Primary OCR backend is EasyOCR. PaddleOCR and Tesseract remain optional fallbacks when available.

Runtime behavior is intentionally offline-safe:

- EasyOCR is initialized lazily and reused through the shared `OCRService`
- no extractor talks to EasyOCR directly
- OCR-heavy workflows expose backend/device status in GUI progress
- if the selected backend is unavailable or fails at runtime, extraction continues with controlled warnings instead of aborting the whole scan
- PaddleOCR is only used as an optional fallback path and stays behind the same `OCRService` contract
- Tesseract is optional and can still be configured through `tesseract.exe` in `PATH` or an explicit CLI/config path

RTF/TXT/HTML text loading now uses best-effort local encoding selection with mojibake detection, and `.rtf` files that actually contain HTML/error-page content are surfaced with explicit fallback warnings instead of being silently treated as healthy RTF.

PDF extraction now prefers the native text layer, uses embedded-image OCR before page OCR, and keeps more honest metadata such as:

- `dense_text_pages`
- `sparse_text_pages`
- `embedded_image_ocr_attempts`
- `page_ocr_attempts`
- `page_ocr_successes`
- `page_debug`

## CLI Usage

Main CLI now uses workflow subcommands.

### Full Scan

```powershell
python -m pd_scanner.cli.main full-scan `
  --input "C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset" `
  --output "C:\Coding\pytorchlabs\hack\output" `
  --mode fast `
  --workers 1 `
  --log-level INFO
```

Legacy backward-compatible form still works and maps to `full-scan`:

```powershell
python -m pd_scanner.cli.main `
  --input "C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset" `
  --output "C:\Coding\pytorchlabs\hack\output" `
  --mode fast `
  --workers 1 `
  --log-level INFO
```

### PDF Scan

```powershell
python -m pd_scanner.cli.main pdf-scan `
  --input "C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset" `
  --output "C:\Coding\pytorchlabs\hack\output_pdf" `
  --mode deep `
  --workers 1
```

### Structured Scan

```powershell
python -m pd_scanner.cli.main structured-scan `
  --input "C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset" `
  --output "C:\Coding\pytorchlabs\hack\output_structured" `
  --mode fast `
  --workers 1
```

### Text Scan

```powershell
python -m pd_scanner.cli.main text-scan `
  --input "C:\Coding\pytorchlabs\РџР”РЅDataset\РџР”РЅDataset" `
  --output "C:\Coding\pytorchlabs\hack\output_text" `
  --mode fast `
  --workers 1
```

### Image Scan

```powershell
python -m pd_scanner.cli.main image-scan `
  --input "C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset" `
  --output "C:\Coding\pytorchlabs\hack\output_image" `
  --mode deep `
  --workers 1
```

### Video Scan

```powershell
python -m pd_scanner.cli.main video-scan `
  --input "C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset" `
  --output "C:\Coding\pytorchlabs\hack\output_video" `
  --mode deep `
  --video-frame-step-sec 3 `
  --workers 1
```

### Detector Lab

```powershell
python -m pd_scanner.cli.main detector-lab `
  --input "C:\Coding\pytorchlabs\hack" `
  --output "C:\Coding\pytorchlabs\hack\output_detector" `
  --text "Email: ivan.petrov@mail.ru; phone: +7 999 123-45-67"
```

### Report Build / Report View

```powershell
python -m pd_scanner.cli.main build-report `
  --input "C:\Coding\pytorchlabs\hack\output" `
  --output "C:\Coding\pytorchlabs\hack\output"
```

## Streamlit GUI

Run from the project root:

```powershell
conda activate torchlab311
cd C:\Coding\pytorchlabs\hack
streamlit run pd_scanner/app/streamlit_app.py
```

The Streamlit entrypoint bootstraps the project root into `sys.path`, so no manual `PYTHONPATH` setup is required.

GUI pages:

- Dashboard
- Full Scan
- PDF Scan
- Text Documents
- Structured Files
- Image OCR
- Video Scan
- Detector Lab
- Reports

The GUI no longer exposes empty internal pages such as `common` or helper modules. Internal page renderers now live under `pd_scanner/app/views`, while Streamlit shows only the single curated navigation inside `streamlit_app.py`.

Workflow UX notes:

- `Dashboard` shows OCR status, active scan state, latest workflow result, and recent input/output paths
- `Full Scan` shows live progress, current file, extractor/type details, processed-by-type counters, recent processed files, recent events, and report artifact paths
- `PDF Scan` shows PDF inventory, invalid PDF list, OCR fallback count, page-count summary, and extraction previews
- `Text Documents` shows DOCX/RTF/TXT inventory, sample paths, live extractor info, chunk previews, and debug artifacts
- `Structured Files` is preview-oriented and shows counts by format, sample files, preview/full toggle, row/column metadata, and structured debug artifacts
- `Image OCR` shows OCR availability, image inventory, skipped-file behavior, and OCR previews
- `Video Scan` shows MP4 inventory, frame-step settings, OCR status, and workflow progress
- `Detector Lab` runs detector-only analysis against manual text or a text file and writes a dedicated debug artifact
- `Reports` reloads existing `scan_report.json` outputs without re-running extraction

Path selection in GUI:

- every workflow page has a `Root path` plus optional `subpath or file`
- quick buttons let you jump to the dataset root, latest input, and latest output
- recent path history is remembered per session
- the resolved input/output paths are shown explicitly before launch

Text-document debug artifacts:

- `output/debug/text_scan/preview.json` contains counts by type, sample chunks, and extraction metadata
- the same backend workflow is used by CLI, GUI, and full-scan observability

## Tests

Run:

```powershell
python -m pytest -q
```

Coverage now includes:

- validators and maskers
- UZ classification
- PDF regression and invalid PDF handling
- multimodal extraction for PDF/DOCX/HTML embedded resources
- detector pipeline duplicate merging
- structured workflow
- text workflow
- image workflow
- video workflow
- detector workflow
- reporting workflow
- single-active-scan policy
- state reset, cancel behavior, and warning aggregation
- GUI helper utilities for path resolution and report discovery
- CLI wiring for `text-scan`

## Limitations

- `DOC` remains best-effort
- OCR quality depends on local Tesseract and source quality
- specialized workflows currently prioritize stability and inspectability over maximum throughput
- operator-facing progress for specialized workflows is intentionally compact and less noisy than `scan.log`
- cancellation is cooperative, so a very slow single-file extractor can only stop after the current file step yields control
