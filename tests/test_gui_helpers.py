"""GUI helper tests."""

from __future__ import annotations

from pathlib import Path

from pd_scanner.app.views.common import collect_file_inventory, list_report_directories, resolve_target_path


def test_resolve_target_path_supports_relative_targets(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    nested = root / "pdfs"
    nested.mkdir(parents=True)
    resolved = resolve_target_path(str(root), "pdfs")
    assert resolved == nested.resolve()


def test_collect_file_inventory_filters_suffixes(tmp_path: Path) -> None:
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.csv").write_text("x", encoding="utf-8")
    inventory = collect_file_inventory(tmp_path, suffixes=(".pdf",))
    assert inventory["total"] == 1
    assert inventory["counts"] == {".pdf": 1}


def test_list_report_directories_finds_existing_reports(tmp_path: Path) -> None:
    output_dir = tmp_path / "output_a"
    output_dir.mkdir()
    (output_dir / "scan_report.json").write_text("{}", encoding="utf-8")
    found = list_report_directories(tmp_path, (str(output_dir),))
    assert str(output_dir.resolve()) in found
