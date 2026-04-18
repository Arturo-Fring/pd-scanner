"""Text-document workflow view."""

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

TEXT_SUFFIXES = {".docx", ".rtf", ".txt"}


def render_text_scan_page(state, default_config) -> None:
    """Render text-document workflow page."""
    render_workflow_header(
        "Text Documents",
        "Inspect DOCX, RTF, and TXT extraction as a dedicated workflow with previews, chunk counts, and debug artifacts.",
    )
    resolved_input, resolved_output = render_path_selector(state, default_config, key_prefix="text_scan")
    runtime = render_runtime_controls(default_config, key_prefix="text_scan_runtime", allow_workers=False)
    config = build_runtime_config(input_path=resolved_input, output_path=resolved_output, **runtime)
    inventory = render_inventory_section(resolved_input, suffixes=TEXT_SUFFIXES, title="Text documents in scope")
    if inventory["counts"]:
        count_cols = st.columns(3)
        count_cols[0].metric("DOCX", inventory["counts"].get(".docx", 0))
        count_cols[1].metric("RTF", inventory["counts"].get(".rtf", 0))
        count_cols[2].metric("TXT", inventory["counts"].get(".txt", 0))
    render_start_stop_controls(
        state,
        workflow_type="text_scan",
        config=config,
        start_label="Start Text Workflow",
        start_kwargs={"input_path": resolved_input},
    )

    snapshot = state.snapshot()
    if snapshot is not None and snapshot.workflow_type == "text_scan":
        render_progress(snapshot)

    result = state.workflow_result
    if result is not None and result.workflow_type == "text_scan":
        stats = result.metadata.get("text_stats", [])
        summary_cols = st.columns(4)
        summary_cols[0].metric("Files scanned", result.metadata.get("files_scanned", len(result.results)))
        summary_cols[1].metric("Chunk rows", sum(int(item.get("chunk_count", 0)) for item in stats))
        summary_cols[2].metric("DOCX", result.metadata.get("counts_by_type", {}).get("docx", 0))
        summary_cols[3].metric("RTF/TXT", result.metadata.get("counts_by_type", {}).get("rtf", 0) + result.metadata.get("counts_by_type", {}).get("txt", 0))
        if stats:
            st.subheader("Extraction metadata")
            st.dataframe(pd.DataFrame(stats), use_container_width=True, hide_index=True)
        render_workflow_result(result)
