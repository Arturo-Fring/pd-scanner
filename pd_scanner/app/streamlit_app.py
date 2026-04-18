"""Streamlit GUI for pd_scanner workflows."""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from pd_scanner.app.state import BackgroundScanState
from pd_scanner.app.views.dashboard import render_dashboard_page
from pd_scanner.app.views.detector_lab import render_detector_lab_page
from pd_scanner.app.views.reports import render_reports_page
from pd_scanner.app.views.run_full_scan import render_full_scan_page
from pd_scanner.app.views.run_image_ocr import render_image_ocr_page
from pd_scanner.app.views.run_pdf_scan import render_pdf_scan_page
from pd_scanner.app.views.run_structured_scan import render_structured_scan_page
from pd_scanner.app.views.run_text_scan import render_text_scan_page
from pd_scanner.app.views.run_video_scan import render_video_scan_page
from pd_scanner.core.config import AppConfig


def get_state() -> BackgroundScanState:
    """Return or initialize the app state."""
    if "scan_state" not in st.session_state:
        st.session_state["scan_state"] = BackgroundScanState()
    return st.session_state["scan_state"]


def build_default_config() -> AppConfig:
    """Return default config shown in the UI."""
    dataset_root = Path(r"C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset")
    if not dataset_root.exists():
        dataset_root = PROJECT_ROOT
    return AppConfig.build(
        input_path=dataset_root,
        output_path=PROJECT_ROOT / "output",
        mode="fast",
        workers=1,
    )


def main() -> None:
    """Render the Streamlit application."""
    st.set_page_config(page_title="pd_scanner", page_icon="🔎", layout="wide")
    state = get_state()
    default_config = build_default_config()

    st.sidebar.title("Workflows")
    page = st.sidebar.radio(
        "Page",
        (
            "Dashboard",
            "Full Scan",
            "PDF Scan",
            "Text Documents",
            "Structured Files",
            "Image OCR",
            "Video Scan",
            "Detector Lab",
            "Reports",
        ),
    )
    if state.is_running():
        st.sidebar.warning("Scan in progress")
    if page == "Dashboard":
        render_dashboard_page(state, default_config)
    elif page == "Full Scan":
        render_full_scan_page(state, default_config)
    elif page == "PDF Scan":
        render_pdf_scan_page(state, default_config)
    elif page == "Text Documents":
        render_text_scan_page(state, default_config)
    elif page == "Structured Files":
        render_structured_scan_page(state, default_config)
    elif page == "Image OCR":
        render_image_ocr_page(state, default_config)
    elif page == "Video Scan":
        render_video_scan_page(state, default_config)
    elif page == "Detector Lab":
        render_detector_lab_page(state, default_config)
    else:
        render_reports_page(state, default_config)
    if state.exception_message:
        st.sidebar.error(state.exception_message)
    if state.is_running():
        st.sidebar.caption("Auto-refreshing every second while the workflow is active.")
        time.sleep(1.0)
        st.rerun()


if __name__ == "__main__":
    main()
