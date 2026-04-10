"""inputs.py のテスト: 形式サポート + Bug1/Bug2/Bug3 修正確認。"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from crisp.v29.inputs import (
    _parse_smi_file,
    _strip_rdkit_extension,
    load_molecule_rows,
    normalize_run_mode,
    to_core_library_text,
)


# ---------------------------------------------------------------------------
# normalize_run_mode
# ---------------------------------------------------------------------------

def test_normalize_run_mode_accepts_aliases() -> None:
    assert normalize_run_mode("core-only") == "core-only"
    assert normalize_run_mode("rule1-bootstrap") == "core+rule1"


def test_normalize_run_mode_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported run mode"):
        normalize_run_mode("unknown-mode")


# ---------------------------------------------------------------------------
# _strip_rdkit_extension (Bug1 修正のコアロジック)
# ---------------------------------------------------------------------------

class TestStripRdkitExtension:
    def test_strips_pipe_notation(self) -> None:
        raw = "C=CC(=O)N[C@H]1CO |&1:5,r|"
        assert _strip_rdkit_extension(raw) == "C=CC(=O)N[C@H]1CO"

    def test_strips_complex_pipe_notation(self) -> None:
        raw = "C=CC(=O)N1C[C@@H](C(=O)OC)[C@H](C1)C=2C=CC=CC2 |&1:6,11,r|"
        assert _strip_rdkit_extension(raw) == "C=CC(=O)N1C[C@@H](C(=O)OC)[C@H](C1)C=2C=CC=CC2"

    def test_noop_when_no_pipe(self) -> None:
        raw = "C=CC(=O)NCC1CC1"
        assert _strip_rdkit_extension(raw) == "C=CC(=O)NCC1CC1"

    def test_strips_trailing_whitespace(self) -> None:
        assert _strip_rdkit_extension("  C=CC  ") == "C=CC"

    def test_empty_string(self) -> None:
        assert _strip_rdkit_extension("") == ""


# ---------------------------------------------------------------------------
# _parse_smi_file / load_molecule_rows (.smi / .smiles)
# ---------------------------------------------------------------------------

class TestParseSmiFile:
    def _write(self, tmp_path: Path, content: str, suffix: str = ".smi") -> Path:
        p = tmp_path / f"lib{suffix}"
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p

    # --- 基本動作 ---

    def test_simple_space_separated(self, tmp_path: Path) -> None:
        p = self._write(tmp_path, """\
            C=CC(=O)NCC1CC1 mol_001
            C=CC(=O)NC1CC1  mol_002
        """)
        rows = load_molecule_rows(p)
        assert len(rows) == 2
        assert rows[0]["molecule_id"] == "mol_001"
        assert rows[0]["smiles"] == "C=CC(=O)NCC1CC1"
        assert rows[1]["molecule_id"] == "mol_002"

    def test_tab_separated(self, tmp_path: Path) -> None:
        p = self._write(tmp_path, "C=CC(=O)NCC1CC1\tmol_001\t276.0\n")
        rows = load_molecule_rows(p)
        assert len(rows) == 1
        assert rows[0]["molecule_id"] == "mol_001"
        assert rows[0]["smiles"] == "C=CC(=O)NCC1CC1"

    def test_smiles_extension_recognized(self, tmp_path: Path) -> None:
        """Bug1 修正確認: .smiles 拡張子が正しく認識される。"""
        p = self._write(tmp_path, "C=CC(=O)NCC1CC1\tmol_001\n", suffix=".smiles")
        rows = load_molecule_rows(p)
        assert len(rows) == 1
        assert rows[0]["molecule_id"] == "mol_001"

    # --- Bug1: |...| 拡張表記 ---

    def test_pipe_notation_tab_separated(self, tmp_path: Path) -> None:
        """Bug1 修正確認: タブ区切り + |...| 行で molecule_id が正しく取得される。"""
        content = "C=CC(=O)N[C@H]1CO |&1:5,r|\tmol_001\t100.0\n"
        p = self._write(tmp_path, content)
        rows = load_molecule_rows(p)
        assert len(rows) == 1
        assert rows[0]["molecule_id"] == "mol_001", (
            f"Expected mol_001 but got {rows[0]['molecule_id']!r} — Bug1 not fixed"
        )
        assert "|" not in rows[0]["smiles"], "SMILES should not contain |...| notation"
        assert rows[0]["smiles"] == "C=CC(=O)N[C@H]1CO"

    def test_pipe_notation_does_not_cause_duplicate_id(self, tmp_path: Path) -> None:
        """Bug1 修正確認: 複数の |...| 行が重複 ID エラーを起こさない。"""
        content = (
            "C=CC(=O)N[C@H]1CO |&1:5,r|\tmol_001\n"
            "C=CC(=O)N[C@@H]1CO |&1:5,r|\tmol_002\n"
        )
        p = self._write(tmp_path, content)
        rows = load_molecule_rows(p)
        assert len(rows) == 2
        ids = [r["molecule_id"] for r in rows]
        assert "mol_001" in ids and "mol_002" in ids

    def test_multiple_pipe_formats(self, tmp_path: Path) -> None:
        """様々な |...| 表記パターンをすべて正しく処理する。"""
        content = (
            "C=CC(=O)N1C[C@@H](CC1) |&1:6,11,r|\tmol_a\n"
            "C=CC(=O)NC[C@H]1C=C[C@@H]2C[C@H]1CO2 |&1:6,9,11,r|\tmol_b\n"
            "C=CC(=O)NCC1CC1\tmol_c\n"  # |...|なし
        )
        p = self._write(tmp_path, content)
        rows = load_molecule_rows(p)
        assert len(rows) == 3
        ids = {r["molecule_id"] for r in rows}
        assert ids == {"mol_a", "mol_b", "mol_c"}
        for r in rows:
            assert "|" not in r["smiles"]

    # --- 入力正規化 ---

    def test_comment_lines_skipped(self, tmp_path: Path) -> None:
        content = "# header\nC=CC(=O)NCC1CC1 mol_001\n# another comment\nC=CC NC mol_002\n"
        p = self._write(tmp_path, content)
        rows = load_molecule_rows(p)
        assert len(rows) == 2

    def test_empty_lines_skipped(self, tmp_path: Path) -> None:
        content = "\nC=CC(=O)NCC1CC1 mol_001\n\n\nC=CC NC mol_002\n\n"
        p = self._write(tmp_path, content)
        rows = load_molecule_rows(p)
        assert len(rows) == 2

    def test_auto_molecule_id_when_omitted(self, tmp_path: Path) -> None:
        content = "C=CC(=O)NCC1CC1\n"
        p = self._write(tmp_path, content)
        rows = load_molecule_rows(p)
        assert len(rows) == 1
        assert rows[0]["molecule_id"].startswith("compound_")

    def test_duplicate_id_raises(self, tmp_path: Path) -> None:
        # SMI フォーマット: "SMILES ID" → スペースなし SMILES で同一 ID を 2 行
        content = "C=CC(=O)NCC1CC1\tmol_001\nC=CC(=O)NC1CC1\tmol_001\n"
        p = self._write(tmp_path, content)
        with pytest.raises(ValueError, match="INPUT_DUPLICATE_ID"):
            load_molecule_rows(p)

    def test_input_order_is_sequential(self, tmp_path: Path) -> None:
        content = "C=CC NC mol_a\nC=CC NO mol_b\nC=CC NF mol_c\n"
        p = self._write(tmp_path, content)
        rows = load_molecule_rows(p)
        orders = [r["input_order"] for r in rows]
        assert orders == [0, 1, 2]

    def test_library_id_from_filename(self, tmp_path: Path) -> None:
        p = self._write(tmp_path, "C=CC(=O)NCC1CC1 mol_001\n", suffix=".smi")
        rows = load_molecule_rows(p)
        assert rows[0]["library_id"] == p.stem

    # --- parquet 経由 ---

    def test_load_molecule_rows_from_parquet(self, tmp_path: Path) -> None:
        import pandas as pd
        data = [
            {"molecule_id": "mol_a", "smiles": "C=CC NC", "library_id": "lib", "input_order": 0},
            {"molecule_id": "mol_b", "smiles": "C=CC NF", "library_id": "lib", "input_order": 1},
        ]
        p = tmp_path / "lib.parquet"
        pd.DataFrame(data).to_parquet(p)
        rows = load_molecule_rows(p)
        assert len(rows) == 2
        assert rows[0]["molecule_id"] == "mol_a"


# ---------------------------------------------------------------------------
# to_core_library_text
# ---------------------------------------------------------------------------

def test_to_core_library_text_format() -> None:
    rows = [
        {"smiles": "C=CC(=O)NCC1CC1", "molecule_id": "mol_001"},
        {"smiles": "C=CC NC", "molecule_id": "mol_002"},
    ]
    text = to_core_library_text(rows)
    lines = text.strip().splitlines()
    assert len(lines) == 2
    assert lines[0] == "C=CC(=O)NCC1CC1 mol_001"
    assert lines[1] == "C=CC NC mol_002"
