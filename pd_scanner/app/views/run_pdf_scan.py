"""PDF workflow view."""

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


def render_pdf_scan_page(state, default_config) -> None:
    """Render PDF workflow page."""
    render_workflow_header(
        "PDF Scan",
        "Inspect PDF traversal, invalid-file handling, OCR fallback usage, and extraction previews.",
    )
    resolved_input, resolved_output = render_path_selector(state, default_config, key_prefix="pdf_scan")
    runtime = render_runtime_controls(default_config, key_prefix="pdf_scan_runtime", allow_workers=False)
    config = build_runtime_config(input_path=resolved_input, output_path=resolved_output, **runtime)
    render_ocr_runtime_summary(config, workflow_label="PDF Scan")
    available, message = ScanService.probe_ocr(config)
    if available:
        st.success(f"OCR available: {message}")
    else:
        st.warning(f"OCR unavailable: {message}")
    render_inventory_section(resolved_input, suffixes={".pdf"}, title="PDF files in scope")
    render_start_stop_controls(
        state,
        workflow_type="pdf_scan",
        config=config,
        start_label="Start PDF Workflow",
        start_kwargs={"input_path": resolved_input},
    )

    snapshot = state.snapshot()
    if snapshot is not None and snapshot.workflow_type == "pdf_scan":
        render_progress(snapshot)

    result = state.workflow_result
    if result is not None and result.workflow_type == "pdf_scan":
        metadata = result.metadata
        total_pages = sum(int(item.metadata.get("page_count", 0)) for item in result.results)
        cols = st.columns(3)
        cols[0].metric("Files scanned", metadata.get("files_scanned", 0))
        cols[1].metric("Invalid PDFs", len(metadata.get("invalid_pdfs", [])))
        cols[2].metric("Page count (sum)", total_pages)
        extra_cols = st.columns(2)
        ocr_used = sum(1 for item in result.results if item.metadata.get("ocr_used"))
        extra_cols[0].metric("OCR fallback used", ocr_used)
        extra_cols[1].metric("Preview chunks", len(result.previews))
        if metadata.get("invalid_pdfs"):
            st.warning("Invalid PDFs detected")
            st.dataframe(
                [{"file": name} for name in metadata["invalid_pdfs"][:50]],
                use_container_width=True,
                hide_index=True,
            )
        render_workflow_result(result)
