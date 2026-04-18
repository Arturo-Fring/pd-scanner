"""Lightweight GUI helper coverage for text workflow."""

from __future__ import annotations

from pd_scanner.app.views.common import collect_file_inventory


def test_gui_helpers_text_scan_inventory(tmp_path) -> None:
    (tmp_path / "a.docx").write_text("placeholder", encoding="utf-8")
    (tmp_path / "b.rtf").write_text(r"{\rtf1 sample}", encoding="utf-8")
    (tmp_path / "c.txt").write_text("sample", encoding="utf-8")

    inventory = collect_file_inventory(tmp_path, suffixes=(".docx", ".rtf", ".txt"))

    assert inventory["total"] == 3
    assert inventory["counts"][".docx"] == 1
    assert inventory["counts"][".rtf"] == 1
    assert inventory["counts"][".txt"] == 1
