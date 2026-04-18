"""Structured workflow view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pd_scanner.app.ui_components import render_progress, render_workflow_result
from pd_scanner.app.views.common import (
    build_runtime_config,
    render_inventory_section,
    render_path_selector,
    render_runtime_controls,
    render_start_stop_controls,
    render_workflow_header,
)

STRUCTURED_SUFFIXES = {".csv", ".json", ".jsonl", ".parquet", ".xls", ".xlsx"}


def render_structured_scan_page(state, default_config) -> None:
    """Render structured-data workflow page."""
    render_workflow_header(
        "Structured Files",
        "Inspect CSV, JSON, JSONL, Parquet, XLS, and XLSX traversal with previews, row counts, columns, and hints.",
    )
    resolved_input, resolved_output = render_path_selector(state, default_config, key_prefix="structured_scan")
    runtime = render_runtime_controls(default_config, key_prefix="structured_scan_runtime", allow_workers=False)
    config = build_runtime_config(input_path=resolved_input, output_path=resolved_output, **runtime)
    options_cols = st.columns(2)
    preview_only = options_cols[0].toggle(
        "Preview only",
        value=True,
        help="Limit processing to the first few structured files for fast engineering checks.",
    )
    preview_limit = options_cols[1].number_input(
        "Preview file limit",
        min_value=1,
        max_value=50,
        value=5,
        step=1,
        disabled=not preview_only,
    )
    inventory = render_inventory_section(resolved_input, suffixes=STRUCTURED_SUFFIXES, title="Structured files in scope")
    render_start_stop_controls(
        state,
        workflow_type="structured_scan",
        config=config,
        start_label="Start Structured Workflow",
        start_kwargs={
            "input_path": resolved_input,
            "preview_only": bool(preview_only),
            "preview_limit": int(preview_limit),
        },
    )

    snapshot = state.snapshot()
    if snapshot is not None and snapshot.workflow_type == "structured_scan":
        render_progress(snapshot)

    st.subheader("Structured traversal notes")
    st.write(
        "Use preview mode to inspect how column-aware extraction behaves before running the full structured-file sweep."
    )
    if inventory["counts"]:
        format_rows = [{"format": key, "count": value} for key, value in inventory["counts"].items()]
        st.dataframe(pd.DataFrame(format_rows), use_container_width=True, hide_index=True)

    result = state.workflow_result
    if result is not None and result.workflow_type == "structured_scan":
        stats = result.metadata.get("structured_stats", [])
        cols = st.columns(4)
        cols[0].metric("Files scanned", result.metadata.get("files_scanned", len(result.results)))
        cols[1].metric("Preview mode", "On" if result.metadata.get("preview_only") else "Off")
        cols[2].metric("Preview rows", len(stats))
        cols[3].metric("Debug artifact", "Ready" if result.metadata.get("debug_artifact") else "Missing")
        if stats:
            st.subheader("Extraction metadata")
            st.dataframe(pd.DataFrame(stats), use_container_width=True, hide_index=True)
        render_workflow_result(result)

