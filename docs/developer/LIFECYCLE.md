# Lifecycle

## Purpose

This document explains how scan lifecycle is managed across CLI, GUI, background execution, and state persistence.

## Core Components

Main files:

- `pd_scanner/core/lifecycle.py`
- `pd_scanner/core/services.py`
- `pd_scanner/app/state.py`

## Single-Active-Scan Policy

The system enforces one active long-running scan at a time.

Why:

- prevent duplicate background scans
- avoid conflicting writes to the same output/state files
- keep GUI progress coherent
- keep cancellation semantics predictable

Enforcement points:

- `ScanLifecycleManager.start()`
- `BackgroundScanState.start()`

If a scan is already active:

- CLI receives `ScanAlreadyRunningError`
- GUI shows a controlled error and keeps Start disabled

## Lifecycle States

Operational states visible through `ScanProgressSnapshot.status`:

- `idle`
- `running`
- `stopping`
- `cancelled`
- `completed`
- `failed`

The documentation shorthand may call `completed` a finished state.

## Lifecycle Flow

1. workflow wants to start
2. lifecycle manager allocates `scan_id`
3. tracker enters `running`
4. tracker writes initial `scan_state.json`
5. workflow updates counters/events during execution
6. stop may be requested cooperatively
7. workflow completes, cancels, or fails
8. tracker writes final state
9. lifecycle manager clears active scan

## `ScanLifecycleManager`

File:

- `core/lifecycle.py`

Responsibilities:

- hold one active scan record in-process
- issue a unique `scan_id`
- reject concurrent starts
- clear active record on finish

Important limitation:

- this is process-local, not cross-process locking

That is enough for the current CLI/Streamlit runtime model.

## `ScanProgressTracker`

File:

- `core/services.py`

Responsibilities:

- keep progress counters
- track current file
- publish recent events
- publish queue preview
- aggregate warnings
- expose artifact paths
- persist `scan_state.json`

## `scan_state.json`

Produced by:

- `ScanProgressTracker._persist_locked()`

Contains:

- workflow identity
- status
- counters
- current file
- recent events
- aggregated warnings
- artifact list
- live previews
- processed-by-type counters

The file is written incrementally and is suitable for polling.

## Cooperative Cancellation

Stop/cancel is implemented as a flag, not as thread termination.

Mechanism:

1. UI or caller invokes `request_stop()`
2. tracker sets `stop_requested = True`
3. workflow loops call `tracker.should_stop()`
4. current file or current batch finishes
5. workflow exits cleanly
6. tracker finalizes state as `cancelled`

This keeps extractor/report state consistent and avoids half-written artifacts.

## What Happens on Stop

### Full scan

- main scan loop checks `tracker.should_stop()` before processing the next file

### Specialized workflows

- file iteration loops in workflow modules check the same flag
- once observed, they break after the current iteration boundary

### GUI view

- shows “Stop requested”
- keeps auto-refresh enabled
- once background thread exits, page transitions back to completed/cancelled rendering

## What Happens on Failure

### Single file failure

- current file gets `status = error`
- scan continues

### Workflow-level fatal failure

- `ScanService.run_scan()` or `run_managed_workflow()` catches exception
- tracker records operator-visible fatal message
- tracker finishes with `failed`
- lifecycle manager clears the active scan

This avoids a stuck `running` state.

## GUI Synchronization

The GUI syncs through:

- `BackgroundScanState.thread`
- `BackgroundScanState.tracker`
- `BackgroundScanState.snapshot()`

The Streamlit app:

- reruns once per second while a scan is active
- renders the latest snapshot
- disables Start while `is_running() == True`

## Finished-State Semantics

States considered terminal:

- `completed`
- `cancelled`
- `failed`

Once terminal:

- lifecycle manager is cleared
- GUI can start another workflow
- latest `WorkflowResult` remains available for review

