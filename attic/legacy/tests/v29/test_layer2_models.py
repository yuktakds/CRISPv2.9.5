"""Layer2: bootstrap CI が意味のある区間を返すことを検証する (FAIL-2 修正確認)。"""
from __future__ import annotations

from crisp.v29.cap.layer2 import (
    _bootstrap_ci_from_fold_deltas,
    _cv_r2_fold_scores,
    _per_fold_delta,
    run_layer2,
)


def _make_rows(n: int, comb_base: float = 0.5, pas_boost: float = 0.2) -> list[dict]:
    """テスト用 mapping_rows を生成する。"""
    import math
    rows = []
    for i in range(n):
        comb = comb_base + 0.05 * math.sin(i)
        pas = comb + pas_boost + 0.03 * math.cos(i)
        rows.append({
            "canonical_link_id": f"link_{i:03d}",
            "molecule_id": f"mol_{i:03d}",
            "target_id": "target_a",
            "condition_hash": "cond_0",
            "functional_score": float(i % 5) - 2.0,
            "comb": comb,
            "P_hit": comb * 0.9,
            "PAS": pas,
            "dist": 0.3 + 0.01 * i,
        })
    return rows


def test_layer2_runs_and_returns_metrics() -> None:
    mapping = _make_rows(12)
    result = run_layer2(mapping, [], cv_seed=42, bootstrap_seed=7, n_splits=3, n_boot=20)
    assert result.status == "OK"
    assert result.n_rows_mapping == 12
    assert result.delta_cv_r2_m2 is not None
    # bootstrap_ci_source マーカーの確認（FAIL-2 修正）
    assert result.diagnostics_json.get("bootstrap_ci_source") == "per_fold_delta"


def test_bootstrap_ci_is_not_degenerate_point_estimate() -> None:
    """FAIL-2 修正確認: per-fold delta bootstrap は点推定と異なる CI を返す。

    旧実装: [delta] * N → resample → mean は常に delta → CI = (delta, delta)
    新実装: fold ごとの delta リスト → resample → 区間が広がる
    """
    # fold deltas にばらつきを持たせる
    fold_deltas = [0.10, 0.25, 0.05, 0.18, 0.12]
    ci = _bootstrap_ci_from_fold_deltas(fold_deltas, seed=0, n_boot=200)
    assert ci is not None, "CI should not be None"
    lo, hi = ci
    # CI は点推定（mean=0.14）と異なる区間になるはず
    mean_delta = sum(fold_deltas) / len(fold_deltas)
    assert lo <= mean_delta <= hi, "mean should be within CI"
    # CI の幅が 0 でないこと（旧実装のダミー bootstrap では lo==hi==mean）
    assert hi - lo > 1e-6, f"CI should have non-zero width, got [{lo:.6f}, {hi:.6f}]"


def test_per_fold_delta_pairs_folds_correctly() -> None:
    """_per_fold_delta が fold ごとに正しく差分を取ることを確認する。"""
    base_folds = [0.1, 0.2, 0.3]
    full_folds = [0.15, 0.28, 0.35]
    deltas = _per_fold_delta(base_folds, full_folds)
    assert deltas is not None
    assert len(deltas) == 3
    assert abs(deltas[0] - 0.05) < 1e-9
    assert abs(deltas[1] - 0.08) < 1e-9
    assert abs(deltas[2] - 0.05) < 1e-9


def test_layer2_unclear_when_too_few_rows() -> None:
    mapping = _make_rows(2)
    result = run_layer2(mapping, [], cv_seed=42, bootstrap_seed=7, n_splits=3)
    assert result.status == "UNCLEAR_SAMPLE_SIZE"
    assert result.delta_cv_r2_m2 is None
    assert result.bootstrap_ci_m2 is None


def test_layer2_v29i09_fold_map_overlap_logged() -> None:
    """V29-I09: 重複ゼロの場合も UNCLEAR にはならず diagnostics に記録される。"""
    mapping = _make_rows(9)
    fals = _make_rows(9)
    # canonical_link_id を別にする → 重複ゼロ
    for i, r in enumerate(fals):
        r["canonical_link_id"] = f"fals_{i:03d}"
    result = run_layer2(mapping, fals, cv_seed=42, bootstrap_seed=7, n_splits=3, n_boot=10)
    assert result.diagnostics_json.get("fold_map_overlap_count") == 0
