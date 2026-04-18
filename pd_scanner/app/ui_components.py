"""Reusable Streamlit UI components."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from pd_scanner.core.services import ScanProgressSnapshot
from pd_scanner.core.workflow_models import WorkflowResult


STAGE_LABELS = {
    "initializing": "initializing",
    "discovering files": "discovering files",
    "initializing OCR backend": "initializing OCR backend",
    "checking OCR availability": "checking OCR availability",
    "processing files": "processing files",
    "processing file": "processing file",
    "running OCR": "running OCR",
    "continuing with warning": "continuing with warning",
    "finished": "finished",
}


def render_summary_cards(summary) -> None:
    """Render top-level KPI cards."""
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Files", summary.total_files)
    col2.metric("Processed", summary.processed_files)
    col3.metric("Files With PD", summary.files_with_pd)
    col4.metric("Errors", summary.errors_count)
    col5.metric("Warnings", summary.warnings_count)
    uz_cols = st.columns(max(1, len(summary.files_by_uz)))
    for index, (uz_level, count) in enumerate(sorted(summary.files_by_uz.items())):
        uz_cols[index].metric(uz_level, count)


def render_progress(snapshot: ScanProgressSnapshot) -> None:
    """Render compact operator-facing progress."""
    total = snapshot.total_count or 1
    progress = min(snapshot.processed_count / total, 1.0)
    stage_label = STAGE_LABELS.get(snapshot.current_stage or "", snapshot.current_stage or "n/a")
    st.progress(progress, text=f"{snapshot.processed_count}/{snapshot.total_count} processed • {stage_label}")
    st.caption(
        f"Workflow: {snapshot.workflow_type or 'n/a'} | scan_id: {snapshot.scan_id or 'n/a'} | status: {snapshot.status}"
    )
    info_cols = st.columns(6)
    info_cols[0].metric("Processed", snapshot.processed_count)
    info_cols[1].metric("With PD", snapshot.files_with_pd)
    info_cols[2].metric("Warnings", snapshot.warnings_count)
    info_cols[3].metric("Errors", snapshot.errors_count)
    info_cols[4].metric("Unsupported", snapshot.unsupported_count)
    info_cols[5].metric("Stage", stage_label)
    if snapshot.current_file:
        st.info(f"Current file: `{snapshot.current_file}`")
        handler_parts = []
        if snapshot.current_file_type:
            handler_parts.append(f"type: `{snapshot.current_file_type}`")
        if snapshot.current_extractor_name:
            handler_parts.append(f"extractor: `{snapshot.current_extractor_name}`")
        if handler_parts:
            st.caption(" | ".join(handler_parts))
    elif snapshot.last_result_path:
        st.caption(f"Last completed file: `{snapshot.last_result_path}`")
    if snapshot.stop_requested and snapshot.is_running:
        st.warning("Stop requested. The workflow is finishing the current step before shutting down.")
    ocr_warnings = [
        {"warning": key, "count": value}
        for key, value in snapshot.aggregated_warnings.items()
        if "ocr" in key.lower() or "paddle" in key.lower() or "tesseract" in key.lower()
    ]
    if ocr_warnings:
        st.warning(
            "OCR warnings are aggregated here so the live feed stays readable. "
            "Full backend details remain in scan.log."
        )
        st.dataframe(pd.DataFrame(ocr_warnings[:5]), use_container_width=True, hide_index=True, height=180)
    if snapshot.artifacts:
        with st.expander("Artifact paths", expanded=True):
            for item in snapshot.artifacts:
                st.code(f"{item['label']}: {item['path']}", language="text")
    queue_col, recent_col = st.columns(2)
    if snapshot.queued_files:
        queue_col.subheader("Queue preview")
        queue_col.dataframe(
            pd.DataFrame({"path": snapshot.queued_files}),
            use_container_width=True,
            hide_index=True,
            height=220,
        )
    if snapshot.recent_results:
        recent_col.subheader("Recent results")
        recent_col.dataframe(pd.DataFrame(snapshot.recent_results), use_container_width=True, hide_index=True, height=220)
    if snapshot.recent_events:
        log_text = "\n".join(
            f"[{event.timestamp}] {event.level}: {event.message}"
            for event in list(reversed(snapshot.recent_events[:12]))
        )
        st.text_area("Operator events", value=log_text, height=180)
    if snapshot.live_previews:
        st.subheader("Live previews")
        for preview in snapshot.live_previews[:3]:
            with st.expander(preview["title"], expanded=False):
                st.json(preview["items"])
    if snapshot.aggregated_warnings:
        with st.expander("Aggregated warnings", expanded=False):
            warning_rows = [{"warning": key, "count": value} for key, value in snapshot.aggregated_warnings.items()]
            st.dataframe(pd.DataFrame(warning_rows), use_container_width=True, hide_index=True)
    if snapshot.processed_by_type:
        with st.expander("Processed by type", expanded=False):
            type_rows = [{"file_type": key, "count": value} for key, value in snapshot.processed_by_type.items()]
            st.dataframe(pd.DataFrame(type_rows), use_container_width=True, hide_index=True)


def render_dashboard(
    *,
    ocr_available: bool,
    ocr_message: str,
    config_preview: dict[str, Any],
    latest_result: WorkflowResult | None,
    active_snapshot: ScanProgressSnapshot | None,
    recent_inputs: list[str],
    recent_outputs: list[str],
) -> None:
    """Render dashboard page."""
    st.title("pd_scanner")
    st.write("Local engineering platform for PII discovery workflows and report analysis.")
    if ocr_available:
        st.success(f"OCR available: {ocr_message}")
    else:
        st.warning(f"OCR unavailable: {ocr_message}")
    if active_snapshot is not None and active_snapshot.is_running:
        st.subheader("Active scan")
        render_progress(active_snapshot)
    elif latest_result is not None:
        status = latest_result.status
        severity = st.warning if status == "cancelled" else st.success
        severity(f"Latest workflow: {latest_result.workflow_type} ({status})")
    st.subheader("Recent paths")
    recent_cols = st.columns(2)
    recent_cols[0].write("Recent inputs")
    recent_cols[0].code("\n".join(recent_inputs[:6]) or "No recent inputs yet.", language="text")
    recent_cols[1].write("Recent outputs")
    recent_cols[1].code("\n".join(recent_outputs[:6]) or "No recent outputs yet.", language="text")
    st.subheader("Config Preview")
    st.json(config_preview)
    if latest_result is not None:
        st.subheader("Latest Workflow Result")
        st.write(f"Workflow: `{latest_result.workflow_type}` | Status: `{latest_result.status}`")
        if latest_result.summary is not None:
            render_summary_cards(latest_result.summary)


def render_workflow_result(result: WorkflowResult) -> None:
    """Render generic workflow result UI."""
    st.subheader(f"Workflow Result: {result.workflow_type}")
    status_message = f"Status: {result.status}"
    if result.status == "cancelled":
        st.warning(status_message)
    elif result.status == "failed":
        st.error(status_message)
    else:
        st.success(status_message)
    if result.summary is not None:
        render_summary_cards(result.summary)
    if result.metadata:
        with st.expander("Workflow metadata", expanded=False):
            st.json(result.metadata)
    if result.previews:
        st.subheader("Intermediate previews")
        for preview in result.previews:
            with st.expander(preview.title, expanded=False):
                st.json(preview.to_dict())
    if result.results:
        rows = []
        for item in result.results:
            rows.append(
                {
                    "path": item.path,
                    "file_type": item.file_type,
                    "status": item.status,
                    "uz_level": item.uz_level,
                    "categories": ", ".join(item.category_counts.keys()),
                    "warnings": len(item.warnings),
                    "error": item.error_message or "",
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if result.errors:
        st.subheader("Errors")
        st.dataframe(pd.DataFrame(result.errors), use_container_width=True, hide_index=True)
    if result.artifacts is not None:
        render_export_section(result.artifacts)


def render_path_status(path: Path, *, label: str = "Resolved target") -> None:
    """Render a small status block for a path."""
    if path.exists():
        kind = "file" if path.is_file() else "directory"
        st.success(f"{label}: `{path}` ({kind})")
    else:
        st.error(f"{label}: `{path}` (missing)")


def render_inventory_table(rows: list[dict[str, Any]], title: str) -> None:
    """Render a compact inventory table."""
    if not rows:
        st.info("No matching files found for this selection yet.")
        return
    st.subheader(title)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_export_section(artifacts) -> None:
    """Render export/download buttons for generated reports."""
    st.subheader("Export")
    files = {
        "CSV report": artifacts.csv_report,
        "JSON report": artifacts.json_report,
        "Markdown report": artifacts.markdown_report,
    }
    columns = st.columns(len(files))
    for index, (label, file_path) in enumerate(files.items()):
        path = Path(file_path)
        if path.exists():
            columns[index].download_button(label=label, data=path.read_bytes(), file_name=path.name, mime="application/octet-stream")
        else:
            columns[index].button(label, disabled=True)

    if st.button("Open output folder"):
        output_dir = artifacts.output_dir
        if hasattr(os, "startfile"):
            os.startfile(output_dir)  # type: ignore[attr-defined]
        else:
            st.info(f"Output directory: {output_dir}")
