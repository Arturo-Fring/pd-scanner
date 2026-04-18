"""Full scan view."""

from __future__ import annotations

import streamlit as st

from pd_scanner.app.ui_components import render_progress, render_workflow_result
from pd_scanner.app.views.common import (
    build_runtime_config,
    render_path_selector,
    render_ocr_runtime_summary,
    render_runtime_controls,
    render_start_stop_controls,
    render_workflow_header,
)
from pd_scanner.core.services import ScanService


def render_full_scan_page(state, default_config) -> None:
    """Render full scan page."""
    render_workflow_header(
        "Full Scan",
        "Recursive end-to-end scan with live progress, warning aggregation, and report generation.",
    )
    resolved_input, resolved_output = render_path_selector(state, default_config, key_prefix="full_scan")
    runtime = render_runtime_controls(default_config, key_prefix="full_scan_runtime")
    config = build_runtime_config(input_path=resolved_input, output_path=resolved_output, **runtime)
    st.info(config.mode_description())
    render_ocr_runtime_summary(config, workflow_label="Full Scan")
    available, message = ScanService.probe_ocr(config)
    if available:
        st.success(f"OCR available: {message}")
    else:
        st.warning(f"OCR unavailable: {message}")
    render_start_stop_controls(
        state,
        workflow_type="full_scan",
        config=config,
        start_label="Start Full Scan",
    )
    snapshot = state.snapshot()
    if snapshot is not None and snapshot.workflow_type == "full_scan":
        render_progress(snapshot)
    if state.workflow_result is not None and state.workflow_result.workflow_type == "full_scan":
        render_workflow_result(state.workflow_result)
