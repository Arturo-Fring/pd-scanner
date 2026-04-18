"""Dashboard view."""

from __future__ import annotations

from pd_scanner.app.ui_components import render_dashboard
from pd_scanner.core.config import AppConfig
from pd_scanner.core.services import ScanService


def render_dashboard_page(state, default_config: AppConfig) -> None:
    """Render dashboard."""
    result = state.workflow_result
    ocr_available, ocr_message = ScanService.probe_ocr(default_config)
    render_dashboard(
        ocr_available=ocr_available,
        ocr_message=ocr_message,
        config_preview=default_config.to_dict(),
        latest_result=result,
        active_snapshot=state.snapshot(),
        recent_inputs=state.recent_input_paths,
        recent_outputs=state.recent_output_paths,
    )

