"""Video scan view."""

from __future__ import annotations

import streamlit as st

from pd_scanner.app.ui_components import render_progress, render_workflow_result
from pd_scanner.app.views.common import (
    build_runtime_config,
    render_inventory_section,
    render_ocr_runtime_summary,
    render_path_selector,
    render_runtime_controls,
    render_start_stop_controls,
    render_workflow_header,
)
from pd_scanner.core.services import ScanService


def render_video_scan_page(state, default_config) -> None:
    """Render video workflow page."""
    render_workflow_header(
        "Video Scan",
        "Inspect MP4 traversal, frame sampling, OCR availability, and live workflow progress.",
    )
    resolved_input, resolved_output = render_path_selector(state, default_config, key_prefix="video_scan")
    runtime = render_runtime_controls(default_config, key_prefix="video_scan_runtime", allow_workers=False)
    config = build_runtime_config(input_path=resolved_input, output_path=resolved_output, **runtime)
    render_ocr_runtime_summary(config, workflow_label="Video Scan")
    available, message = ScanService.probe_ocr(config)
    if available:
        st.success(f"OCR available: {message}")
    else:
        st.warning(f"OCR unavailable: {message}")
    render_inventory_section(resolved_input, suffixes={".mp4"}, title="Video files in scope")
    render_start_stop_controls(
        state,
        workflow_type="video_scan",
        config=config,
        start_label="Start Video Workflow",
        start_kwargs={"input_path": resolved_input},
    )
    snapshot = state.snapshot()
    if snapshot is not None and snapshot.workflow_type == "video_scan":
        render_progress(snapshot)
    if state.workflow_result is not None and state.workflow_result.workflow_type == "video_scan":
        render_workflow_result(state.workflow_result)
