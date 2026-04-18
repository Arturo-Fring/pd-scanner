"""Text-document workflow tests."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from pd_scanner.core.config import AppConfig
from pd_scanner.workflows.text_workflow import run_text_workflow


def test_text_workflow_docx(tmp_path: Path) -> None:
    docx_path = tmp_path / "note.docx"
    document = Document()
    document.add_paragraph("Email: ivan.petrov@mail.ru")
    document.save(docx_path)

    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_text_workflow(config, tmp_path)

    assert result.summary is not None
    assert result.summary.total_files == 1
    assert result.metadata["counts_by_type"]["docx"] == 1
    assert result.metadata["text_stats"][0]["chunk_count"] >= 1


def test_text_workflow_rtf(tmp_path: Path) -> None:
    rtf_path = tmp_path / "note.rtf"
    rtf_path.write_text(r"{\rtf1\ansi Email: ivan.petrov@mail.ru}", encoding="utf-8")

    config = AppConfig.build(input_path=tmp_path, output_path=tmp_path / "out", mode="fast", workers=1)
    result = run_text_workflow(config, tmp_path)

    assert result.summary is not None
    assert result.summary.total_files == 1
    assert result.metadata["counts_by_type"]["rtf"] == 1
    assert "sample_text" in result.metadata["text_stats"][0]
