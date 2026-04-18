"""Reports view."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from pd_scanner.app.ui_components import render_workflow_result
from pd_scanner.app.views.common import DEFAULT_OUTPUT_ROOT, list_report_directories, render_workflow_header


def render_reports_page(state, default_config) -> None:
    """Render reports page."""
    render_workflow_header(
        "Reports",
        "Load existing JSON/CSV/Markdown outputs without re-running extraction, and inspect previously generated summaries.",
    )
    known_outputs = list_report_directories(DEFAULT_OUTPUT_ROOT, tuple(state.recent_output_paths))
    selected_output = st.selectbox("Known report directories", options=[""] + known_outputs, index=0)
    manual_output = st.text_input("Existing output directory", value=selected_output or str(default_config.output_path))
    if st.button("Load Reports", type="primary", key="reports_load"):
        state.load_existing_results(manual_output)
    if state.workflow_result is not None and state.workflow_result.workflow_type == "report_build":
        render_workflow_result(state.workflow_result)
        report_dir = Path(manual_output).expanduser().resolve()
        if report_dir.exists():
            st.caption(f"Loaded reports from `{report_dir}`")
