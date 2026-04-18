"""Shared helpers for Streamlit workflow views."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

import streamlit as st

from pd_scanner.app.ui_components import render_inventory_table, render_path_status
from pd_scanner.core.config import AppConfig
from pd_scanner.core.lifecycle import ScanAlreadyRunningError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = Path(r"C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset")
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "output"


def resolve_target_path(root_path: str, target_path: str) -> Path:
    """Resolve a root path plus optional relative/absolute target path."""
    root = Path(root_path).expanduser()
    if not target_path.strip():
        return root.resolve()
    target = Path(target_path).expanduser()
    if target.is_absolute():
        return target.resolve()
    return (root / target).resolve()


@st.cache_data(ttl=5, show_spinner=False)
def collect_file_inventory(path: Path, *, suffixes: tuple[str, ...] | None = None, sample_limit: int = 30) -> dict[str, object]:
    """Collect a compact recursive inventory for the selected target."""
    suffix_set = {item.lower() for item in suffixes} if suffixes is not None else None
    counts: Counter[str] = Counter()
    sample_rows: list[dict[str, str]] = []
    total = 0

    if not path.exists():
        return {"total": 0, "counts": {}, "rows": []}

    files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
    for file_path in files:
        suffix = file_path.suffix.lower() or "<no_ext>"
        if suffix_set is not None and suffix not in suffix_set:
            continue
        counts[suffix] += 1
        total += 1
        if len(sample_rows) < sample_limit:
            sample_rows.append({"path": str(file_path), "format": suffix})

    return {
        "total": total,
        "counts": dict(sorted(counts.items())),
        "rows": sample_rows,
    }


def build_runtime_config(
    *,
    input_path: Path,
    output_path: Path,
    mode: str,
    workers: int,
    log_level: str,
    ocr_lang: str,
    video_frame_step_sec: int,
    max_file_size_mb: int,
    tesseract_cmd: str,
) -> AppConfig:
    """Build app config from UI controls."""
    return AppConfig.build(
        input_path=input_path,
        output_path=output_path,
        mode=mode,
        workers=workers,
        log_level=log_level,
        ocr_lang=ocr_lang,
        video_frame_step_sec=video_frame_step_sec,
        max_file_size_mb=max_file_size_mb or None,
        tesseract_cmd=tesseract_cmd or None,
    )


def render_workflow_header(title: str, description: str) -> None:
    """Render standard workflow page heading."""
    st.title(title)
    st.caption(description)


def render_path_selector(state, default_config: AppConfig, *, key_prefix: str) -> tuple[Path, Path]:
    """Render root/target/output controls with presets and recent paths."""
    root_key = f"{key_prefix}_root_path"
    target_key = f"{key_prefix}_target_path"
    output_key = f"{key_prefix}_output_path"
    recent_input_key = f"{key_prefix}_recent_input"
    recent_output_key = f"{key_prefix}_recent_output"

    st.session_state.setdefault(root_key, str(default_config.input_path if default_config.input_path.exists() else DEFAULT_DATASET_ROOT))
    st.session_state.setdefault(target_key, "")
    st.session_state.setdefault(output_key, str(default_config.output_path if default_config.output_path else DEFAULT_OUTPUT_ROOT))
    st.session_state.setdefault(recent_input_key, "")
    st.session_state.setdefault(recent_output_key, "")

    preset_cols = st.columns(4)
    if preset_cols[0].button("Use dataset root", key=f"{key_prefix}_use_dataset"):
        st.session_state[root_key] = str(DEFAULT_DATASET_ROOT)
        st.session_state[target_key] = ""
    if preset_cols[1].button("Use project output", key=f"{key_prefix}_use_output"):
        st.session_state[output_key] = str(DEFAULT_OUTPUT_ROOT)
    if preset_cols[2].button("Use latest input", key=f"{key_prefix}_use_latest_input", disabled=not state.recent_input_paths):
        st.session_state[root_key] = state.recent_input_paths[0]
        st.session_state[target_key] = ""
    if preset_cols[3].button("Use latest output", key=f"{key_prefix}_use_latest_output", disabled=not state.recent_output_paths):
        st.session_state[output_key] = state.recent_output_paths[0]

    recent_cols = st.columns(2)
    recent_cols[0].selectbox(
        "Recent inputs",
        options=[""] + state.recent_input_paths,
        key=recent_input_key,
        help="Pick a recently used dataset root or file path.",
    )
    recent_cols[1].selectbox(
        "Recent outputs",
        options=[""] + state.recent_output_paths,
        key=recent_output_key,
        help="Pick a recently used output directory.",
    )

    apply_cols = st.columns(2)
    if apply_cols[0].button("Apply recent input", key=f"{key_prefix}_apply_recent_input", disabled=not st.session_state[recent_input_key]):
        st.session_state[root_key] = st.session_state[recent_input_key]
        st.session_state[target_key] = ""
    if apply_cols[1].button("Apply recent output", key=f"{key_prefix}_apply_recent_output", disabled=not st.session_state[recent_output_key]):
        st.session_state[output_key] = st.session_state[recent_output_key]

    st.text_input("Root path", key=root_key, help="Dataset root, working directory, or a direct file path.")
    st.text_input("Optional subpath or file", key=target_key, help="Relative to the root path unless absolute.")
    st.text_input("Output directory", key=output_key)

    resolved_input = resolve_target_path(st.session_state[root_key], st.session_state[target_key])
    resolved_output = Path(st.session_state[output_key]).expanduser().resolve()
    render_path_status(resolved_input, label="Resolved input")
    if resolved_output.exists():
        render_path_status(resolved_output, label="Resolved output")
    else:
        st.info(f"Resolved output: `{resolved_output}` (will be created if needed)")
    return resolved_input, resolved_output


def render_runtime_controls(default_config: AppConfig, *, key_prefix: str, allow_workers: bool = True) -> dict[str, object]:
    """Render shared runtime controls."""
    col1, col2, col3 = st.columns(3)
    mode = col1.selectbox(
        "Mode",
        options=["fast", "deep"],
        index=0 if default_config.runtime.mode == "fast" else 1,
        key=f"{key_prefix}_mode",
    )
    workers = col2.number_input(
        "Workers",
        min_value=1,
        max_value=32,
        value=default_config.runtime.workers,
        step=1,
        key=f"{key_prefix}_workers",
        disabled=not allow_workers,
        help="GUI runs are kept sequential for stable progress/cancel behavior.",
    )
    log_level = col3.selectbox(
        "Log level",
        options=["INFO", "WARNING", "ERROR"],
        index=0,
        key=f"{key_prefix}_log_level",
    )

    col4, col5, col6 = st.columns(3)
    ocr_lang = col4.text_input("OCR language", value=default_config.ocr.lang, key=f"{key_prefix}_ocr_lang")
    video_step = col5.number_input(
        "Video frame step (sec)",
        min_value=1,
        max_value=30,
        value=default_config.runtime.video_frame_step_sec,
        step=1,
        key=f"{key_prefix}_video_step",
    )
    max_file_size_mb = col6.number_input(
        "Max file size (MB)",
        min_value=0,
        value=default_config.runtime.max_file_size_mb or 0,
        step=10,
        key=f"{key_prefix}_max_file_size",
    )
    tesseract_cmd = st.text_input(
        "Optional Tesseract path",
        value=default_config.ocr.tesseract_cmd or "",
        key=f"{key_prefix}_tesseract_cmd",
    )
    return {
        "mode": mode,
        "workers": int(workers),
        "log_level": log_level,
        "ocr_lang": ocr_lang,
        "video_frame_step_sec": int(video_step),
        "max_file_size_mb": int(max_file_size_mb),
        "tesseract_cmd": tesseract_cmd,
    }


def render_ocr_runtime_summary(config: AppConfig, *, workflow_label: str) -> None:
    """Render compact OCR/deep-mode summary before workflow start."""
    st.subheader("Runtime Summary")
    cols = st.columns(4)
    cols[0].metric("Mode", config.runtime.mode)
    cols[1].metric("OCR enabled", "yes" if config.ocr.enabled else "no")
    cols[2].metric("OCR backend", config.ocr.backend)
    cols[3].metric("Offline-only OCR", "yes" if config.ocr.offline_only else "no")
    if config.runtime.mode == "deep":
        st.info(
            f"{workflow_label} in deep mode enables OCR-heavy processing. "
            "The app will initialize the OCR backend, check availability, then continue file-by-file."
        )
    else:
        st.info(
            f"{workflow_label} in fast mode skips OCR-heavy processing by design. "
            "Those skips are aggregated instead of flooding the live event feed."
        )
    st.caption(
        "Limits: "
        f"max OCR calls/file={config.runtime.max_ocr_calls_per_file}, "
        f"max embedded images/file={config.runtime.max_embedded_images_per_file}, "
        f"max PDF OCR pages={config.runtime.max_pdf_ocr_pages}, "
        f"max video frames={config.runtime.max_video_frames}."
    )


def render_start_stop_controls(
    state,
    *,
    workflow_type: str,
    config: AppConfig,
    start_label: str,
    start_kwargs: dict[str, object] | None = None,
) -> None:
    """Render standard Start/Stop controls with single-active-scan protection."""
    start_kwargs = start_kwargs or {}
    snapshot = state.snapshot()
    workflow_active = snapshot is not None and snapshot.is_running and snapshot.workflow_type == workflow_type
    cols = st.columns(2)
    if cols[0].button(start_label, type="primary", disabled=state.is_running(), key=f"{workflow_type}_start"):
        if not config.input_path.exists():
            st.error(f"Input path does not exist: {config.input_path}")
        else:
            try:
                state.start(workflow_type, config, **start_kwargs)
            except ScanAlreadyRunningError as exc:
                st.error(str(exc))
    if cols[1].button("Stop / Cancel", disabled=not workflow_active, key=f"{workflow_type}_stop"):
        if state.request_stop():
            st.warning("Stop requested. The workflow will stop after the current file or batch.")


def render_inventory_section(path: Path, *, suffixes: Iterable[str] | None, title: str) -> dict[str, object]:
    """Render inventory counts and sample rows for the selected target."""
    inventory = collect_file_inventory(path, suffixes=tuple(sorted(suffixes)) if suffixes is not None else None)
    count_cols = st.columns(2)
    count_cols[0].metric("Matching files", inventory["total"])
    count_cols[1].metric("Formats", len(inventory["counts"]))
    if inventory["counts"]:
        st.json({"counts_by_format": inventory["counts"]})
    render_inventory_table(inventory["rows"], title)
    return inventory


@st.cache_data(ttl=10, show_spinner=False)
def list_report_directories(output_root: Path, recent_output_paths: tuple[str, ...]) -> list[str]:
    """Return report directories that contain scan artifacts."""
    candidates: list[Path] = []
    if output_root.exists():
        candidates.append(output_root)
        candidates.extend(path for path in output_root.iterdir() if path.is_dir())
    for item in recent_output_paths:
        candidates.append(Path(item))

    seen: set[str] = set()
    resolved: list[str] = []
    for candidate in candidates:
        report_path = candidate / "scan_report.json"
        candidate_value = str(candidate.resolve())
        if report_path.exists() and candidate_value not in seen:
            seen.add(candidate_value)
            resolved.append(candidate_value)
    return resolved
