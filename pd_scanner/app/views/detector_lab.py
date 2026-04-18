"""Detector lab view."""

from __future__ import annotations

import streamlit as st

from pd_scanner.app.ui_components import render_workflow_result
from pd_scanner.app.views.common import render_path_selector, render_workflow_header
from pd_scanner.core.config import AppConfig


def render_detector_lab_page(state, default_config) -> None:
    """Render detector lab page."""
    render_workflow_header(
        "Detector Lab",
        "Run detectors on manual text or a text file without launching a full scan workflow.",
    )
    _, resolved_output = render_path_selector(state, default_config, key_prefix="detector_lab")
    text = st.text_area("Input text", height=220)
    text_file = st.text_input("Optional text file path", value="")
    if st.button("Run Detector Lab", type="primary", key="detector_lab_start"):
        config = AppConfig.build(
            input_path=default_config.input_path,
            output_path=resolved_output,
            mode=default_config.runtime.mode,
            workers=1,
            ocr_lang=default_config.ocr.lang,
            video_frame_step_sec=default_config.runtime.video_frame_step_sec,
            max_file_size_mb=default_config.runtime.max_file_size_mb,
            log_level=default_config.runtime.log_level,
            tesseract_cmd=default_config.ocr.tesseract_cmd,
        )
        result = state.run_sync(
            "detector_lab",
            config,
            text=text or None,
            text_file=text_file or None,
        )
        render_workflow_result(result)
    elif state.workflow_result is not None and state.workflow_result.workflow_type == "detector_lab":
        render_workflow_result(state.workflow_result)
