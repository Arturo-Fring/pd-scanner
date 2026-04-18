# CLI

## Entry Point

Main entrypoint:

```bash
python -m pd_scanner.cli.main
```

File:

- `pd_scanner/cli/main.py`

## Supported Subcommands

- `full-scan`
- `pdf-scan`
- `structured-scan`
- `text-scan`
- `image-scan`
- `video-scan`
- `detector-lab`
- `build-report`

## Backward Compatibility

If the CLI is called without a subcommand and starts directly with flags, it is interpreted as:

- `full-scan`

## Command Routing

Routing logic:

- parser chooses command
- config built from args
- command mapped to backend workflow or CLI helper

Examples:

- `pdf-scan -> run_pdf_cli()`
- `structured-scan -> run_structured_cli()`
- `text-scan -> run_text_cli()`
- `full-scan -> run_full_scan_workflow()`

## Common Runtime Arguments

Most workflow commands use shared runtime arguments defined in:

- `pd_scanner/cli/common.py`

Typical arguments:

- `--input`
- `--output`
- `--mode`
- `--workers`
- `--ocr-lang`
- `--video-frame-step-sec`
- `--max-file-size-mb`
- `--log-level`
- optional `--tesseract-cmd`

## Error Handling

Concurrent scan rejection:

- surfaced as `ScanAlreadyRunningError`
- CLI exits with non-zero code

Workflow summary printing:

- compact workflow name
- processed counts
- metadata JSON when available

