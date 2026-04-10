"""mapping_table / falsification_table のテスト (Bug2 修正含む)。"""
from __future__ import annotations

import pytest

from crisp.v29.cap.mapping import _column_mean, build_mapping_table, functional_score_from_raw
from crisp.v29.cap.falsification import build_falsification_table


# ---------------------------------------------------------------------------
# functional_score_from_raw
# ---------------------------------------------------------------------------

class TestFunctionalScoreFromRaw:
    def test_ic50_negative(self) -> None:
        assert functional_score_from_raw(10.0, "ic50", "") == -10.0

    def test_direction_inhibitory(self) -> None:
        assert functional_score_from_raw(5.0, "", "inhibitory") == -5.0

    def test_direction_activating(self) -> None:
        assert functional_score_from_raw(3.0, "", "activating") == 3.0

    def test_non_numeric_returns_none(self) -> None:
        assert functional_score_from_raw("n/a", "ic50", "") is None

    def test_unknown_type_and_direction_returns_none(self) -> None:
        assert functional_score_from_raw(1.0, "unknown", "unknown") is None


# ---------------------------------------------------------------------------
# _column_mean (Bug2 修正確認)
# ---------------------------------------------------------------------------

class TestColumnMean:
    def test_empty_list_returns_zero(self) -> None:
        """Bug2 修正確認: 空リストで ZeroDivisionError が発生しない。"""
        result = _column_mean([], "comb")
        assert result == 0.0, f"Expected 0.0, got {result!r} — Bug2 not fixed"

    def test_single_row(self) -> None:
        rows = [{"comb": 0.75}]
        assert _column_mean(rows, "comb") == pytest.approx(0.75)

    def test_multiple_rows(self) -> None:
        rows = [{"comb": 0.2}, {"comb": 0.4}, {"comb": 0.6}]
        assert _column_mean(rows, "comb") == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# build_mapping_table (native-only)
# ---------------------------------------------------------------------------

def _make_pair_row(role: str, link_id: str = "link_1", **extra) -> dict:
    base = {
        "pairing_role": role,
        "canonical_link_id": link_id,
        "molecule_id": "mol_1",
        "target_id": "tgt",
        "comb": 0.8, "P_hit": 0.7, "PAS": 0.3,
        "dist": 0.2, "LPCS": 0.6, "PCF": 0.5,
    }
    base.update(extra)
    return base


def _make_assay(link_id: str = "link_1") -> dict:
    return {
        "canonical_link_id": link_id,
        "condition_hash": "cond_0",
        "functional_score_raw": 5.0,
        "assay_type": "ic50",
        "direction": "",
        "unit": "nM",
    }


def test_mapping_table_contains_native_only() -> None:
    """V29-I08: mapping_table は native のみ。"""
    rows = [_make_pair_row("native"), _make_pair_row("matched_falsification")]
    assays = [_make_assay()]
    result = build_mapping_table(rows, assays)
    assert len(result) == 1
    assert result[0]["pairing_role"] == "native"


def test_mapping_table_empty_when_no_assay_match() -> None:
    rows = [_make_pair_row("native")]
    result = build_mapping_table(rows, [])
    assert result == []


def test_mapping_table_functional_score_computed() -> None:
    rows = [_make_pair_row("native")]
    assays = [_make_assay()]
    result = build_mapping_table(rows, assays)
    assert result[0]["functional_score"] == pytest.approx(-5.0)  # ic50 → 負符号


def test_mapping_table_averages_multiple_pairs_per_link() -> None:
    rows = [
        _make_pair_row("native", comb=0.6),
        _make_pair_row("native", comb=0.8),
    ]
    assays = [_make_assay()]
    result = build_mapping_table(rows, assays)
    assert len(result) == 1
    assert result[0]["comb"] == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# build_falsification_table (matched_falsification-only)
# ---------------------------------------------------------------------------

def test_falsification_table_contains_matched_only() -> None:
    """V29-I08: falsification_table は matched_falsification のみ。"""
    rows = [_make_pair_row("native"), _make_pair_row("matched_falsification")]
    assays = [_make_assay()]
    result = build_falsification_table(rows, assays, donor_plan=None)
    assert len(result) == 1
    assert result[0]["pairing_role"] == "matched_falsification"


def test_falsification_table_records_donor_plan_hashes() -> None:
    rows = [_make_pair_row("matched_falsification")]
    assays = [_make_assay()]
    donor_plan = {"shuffle_donor_pool_hash": "sha256:abc", "donor_plan_hash": "sha256:def"}
    result = build_falsification_table(rows, assays, donor_plan)
    assert result[0]["shuffle_donor_pool_hash"] == "sha256:abc"
    assert result[0]["donor_plan_hash"] == "sha256:def"


def test_falsification_table_empty_when_no_assay_match() -> None:
    rows = [_make_pair_row("matched_falsification")]
    result = build_falsification_table(rows, [], donor_plan=None)
    assert result == []
