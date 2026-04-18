# GUI

## Overview

The GUI is a thin Streamlit shell over the same backend workflows used by the CLI.

Main files:

- `pd_scanner/app/streamlit_app.py`
- `pd_scanner/app/state.py`
- `pd_scanner/app/ui_components.py`
- `pd_scanner/app/views/*.py`

The GUI should not contain business logic that diverges from CLI behavior.

## Core GUI Architecture

### `streamlit_app.py`

Responsibilities:

- bootstrap project root into `sys.path`
- create or reuse `BackgroundScanState`
- build default config
- expose sidebar navigation
- auto-refresh during active scans

### `state.py`

Responsibilities:

- own background thread state
- map workflow names to backend runners
- enforce one active background scan per session
- expose snapshots for rendering
- support cooperative stop requests

Main object:

- `BackgroundScanState`

### `ui_components.py`

Responsibilities:

- reusable progress rendering
- reusable summary cards
- workflow result rendering
- export/download blocks
- operator-friendly status presentation

### `views/*`

Responsibilities:

- page-specific controls
- path selection
- inventory preview
- workflow launch
- specialized result rendering

## Page Map

### Dashboard

File:

- `app/views/dashboard.py`

Shows:

- OCR status
- current active scan
- latest workflow result
- recent paths
- config preview

Uses state fields:

- `workflow_result`
- `recent_input_paths`
- `recent_output_paths`
- live snapshot via `state.snapshot()`

### Full Scan

File:

- `app/views/run_full_scan.py`

Launches:

- `full_scan`

Shows:

- path selectors
- runtime controls
- start/stop buttons
- live progress
- final workflow result

### PDF Scan

File:

- `app/views/run_pdf_scan.py`

Launches:

- `pdf_scan`

Shows:

- PDF inventory
- path/runtime controls
- live progress
- invalid PDF info
- extraction previews

### Text Documents

File:

- `app/views/run_text_scan.py`

Launches:

- `text_scan`

Shows:

- docx/rtf/txt inventory
- sample paths
- live progress
- preview chunks
- debug artifact path

### Structured Files

File:

- `app/views/run_structured_scan.py`

Launches:

- `structured_scan`

Shows:

- structured inventory
- preview/full toggle
- sample rows
- columns preview
- workflow result metadata
- debug artifact path

### Image OCR

File:

- `app/views/run_image_ocr.py`

Launches:

- `image_scan`

Shows:

- OCR availability
- image inventory
- live progress
- previews and skipped-file info

### Video Scan

File:

- `app/views/run_video_scan.py`

Launches:

- `video_scan`

Shows:

- MP4 inventory
- frame-step controls
- OCR availability
- workflow result previews

### Detector Lab

File:

- `app/views/detector_lab.py`

Launches:

- `detector_lab`

Shows:

- manual text input
- optional text-file path
- detector result preview
- debug artifact path

### Reports

File:

- `app/views/reports.py`

Launches:

- `report_build`

Shows:

- discovered report directories
- loaded report payload
- file results table
- artifact downloads

## Progress Model

The GUI does not inspect workflow internals directly. It renders a `ScanProgressSnapshot`.

Snapshot fields include:

- `is_running`
- `scan_id`
- `workflow_type`
- `status`
- `total_count`
- `processed_count`
- `warnings_count`
- `errors_count`
- `current_file`
- `current_file_type`
- `current_extractor_name`
- `current_stage`
- `recent_events`
- `queued_files`
- `recent_results`
- `live_previews`
- `artifacts`
- `processed_by_type`

These are rendered by `render_progress()`.

## Start / Stop / Cancel

Start behavior:

- page builds `AppConfig`
- page calls `state.start(...)`
- background thread begins workflow execution

Stop behavior:

- page calls `state.request_stop()`
- tracker sets `stop_requested = True`
- workflow loop checks `tracker.should_stop()`
- current file or current batch finishes
- workflow exits as `cancelled`

This is cooperative cancellation, not hard kill.

## Single-Active-Scan Policy

There are two enforcement layers:

### GUI layer

- Start buttons are disabled while a workflow is running
- only the active workflow gets an enabled Stop button

### Backend layer

- `ScanLifecycleManager` rejects a second active scan
- `BackgroundScanState.start()` also rejects concurrent thread start

This prevents accidental duplicate scans caused by Streamlit reruns.

## Path Selection

Implemented in:

- `app/views/common.py`

User inputs:

- root path
- optional subpath or file
- output directory

Additional helpers:

- dataset root preset
- project output preset
- latest input preset
- latest output preset
- recent path dropdowns

Resolved paths are always shown explicitly before launch.

## Artifacts Shown in GUI

The GUI can display:

- report artifacts
- debug artifact paths
- live extraction previews
- recent processed files
- aggregated warnings
- processed-by-type counters

The actual files are produced by workflows and the service layer. The GUI only renders them.

