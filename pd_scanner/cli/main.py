"""Command-line interface for pd_scanner workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pd_scanner.cli.common import add_runtime_arguments, build_config_from_args
from pd_scanner.cli.detect_cli import run_detector_cli
from pd_scanner.cli.image_cli import run_image_cli
from pd_scanner.cli.pdf_cli import run_pdf_cli
from pd_scanner.cli.report_cli import run_report_cli
from pd_scanner.cli.structured_cli import run_structured_cli
from pd_scanner.cli.text_cli import run_text_cli
from pd_scanner.cli.video_cli import run_video_cli
from pd_scanner.core.lifecycle import ScanAlreadyRunningError
from pd_scanner.workflows.full_scan_workflow import run_full_scan_workflow


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser with workflow subcommands."""
    parser = argparse.ArgumentParser(description="pd_scanner workflow CLI")
    subparsers = parser.add_subparsers(dest="command")

    full_scan = subparsers.add_parser("full-scan", help="Run full recursive scan")
    add_runtime_arguments(full_scan)

    pdf_scan = subparsers.add_parser("pdf-scan", help="Run PDF-only workflow")
    add_runtime_arguments(pdf_scan)

    structured_scan = subparsers.add_parser("structured-scan", help="Run structured-data workflow")
    add_runtime_arguments(structured_scan)

    text_scan = subparsers.add_parser("text-scan", help="Run text-document workflow")
    add_runtime_arguments(text_scan)

    image_scan = subparsers.add_parser("image-scan", help="Run image OCR workflow")
    add_runtime_arguments(image_scan)

    video_scan = subparsers.add_parser("video-scan", help="Run video workflow")
    add_runtime_arguments(video_scan)

    detector_lab = subparsers.add_parser("detector-lab", help="Run detectors on manual text or a text file")
    detector_lab.add_argument("--input", required=True, help="Output directory for artifacts")
    detector_lab.add_argument("--output", required=True, help="Output directory for artifacts")
    detector_lab.add_argument("--text", default=None, help="Inline text for detector lab")
    detector_lab.add_argument("--text-file", default=None, help="Path to a text file")
    detector_lab.add_argument("--log-level", default="INFO", help="Logging level")

    report_build = subparsers.add_parser("build-report", help="Load existing reports and artifacts")
    report_build.add_argument("--input", required=True, help="Existing output directory with reports")
    report_build.add_argument("--output", required=True, help="Output directory")
    report_build.add_argument("--log-level", default="INFO", help="Logging level")

    return parser


def _print_workflow_result(result) -> None:
    print(f"Workflow: {result.workflow_type}")
    if result.summary is not None:
        print(
            f"Processed: {result.summary.processed_files}/{result.summary.total_files} | "
            f"with_pd={result.summary.files_with_pd} | errors={result.summary.errors_count} | "
            f"warnings={result.summary.warnings_count}"
        )
    if result.metadata:
        print(json.dumps(result.metadata, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    argv = list(sys.argv[1:] if argv is None else argv)
    # Backward compatibility: legacy call without subcommand behaves as full-scan.
    if argv and argv[0].startswith("--") and argv[0] not in {"-h", "--help"}:
        argv = ["full-scan", *argv]

    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "full-scan"

    try:
        if command == "full-scan":
            config = build_config_from_args(args)
            result = run_full_scan_workflow(config)
        elif command == "pdf-scan":
            config = build_config_from_args(args)
            result = run_pdf_cli(config, args.input)
        elif command == "structured-scan":
            config = build_config_from_args(args)
            result = run_structured_cli(config, args.input)
        elif command == "text-scan":
            config = build_config_from_args(args)
            result = run_text_cli(config, args.input)
        elif command == "image-scan":
            config = build_config_from_args(args)
            result = run_image_cli(config, args.input)
        elif command == "video-scan":
            config = build_config_from_args(args)
            result = run_video_cli(config, args.input)
        elif command == "detector-lab":
            from pd_scanner.core.config import AppConfig

            config = AppConfig.build(input_path=args.input, output_path=args.output, log_level=args.log_level)
            result = run_detector_cli(config, text=args.text, text_file=args.text_file)
        elif command == "build-report":
            from pd_scanner.core.config import AppConfig

            config = AppConfig.build(input_path=args.input, output_path=args.output, log_level=args.log_level)
            result = run_report_cli(config, args.input)
        else:
            parser.error(f"Unsupported command: {command}")
            return 2
    except ScanAlreadyRunningError as exc:
        print(f"Scan in progress: {exc}")
        return 2

    _print_workflow_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
