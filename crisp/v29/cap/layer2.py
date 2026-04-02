"""Cap Layer2: 幾何量→機能スコア の canonical-link 単位 CV モデル。

設計書 §Cap-Layer2, 別紙 E §E4 に準拠。

責務:
  - mapping_table (native-only) と falsification_table (matched_falsification-only) を受け取る
  - 交差検証 R² (M1: geometry-only, M2: geometry+kinetics-proxy) を計算する
  - per-fold delta を bootstrap resample して 95% CI を返す
  - cap shuffle falsification との比較 (r_shuffle_joint) を記録する

禁止:
  - PASS / FAIL / UNCLEAR の判定（→ cap/scv.py が行う）
  - mapping / falsification の fold 割り当てを異なる seed で行う（V29-I09）

FAIL-2 修正:
  bootstrap CI は per-fold delta のリストを resample する。
  スカラーを定数ベクトルに複製した疑似 bootstrap は禁止（E4 崩壊点検出が不能になる）。
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import numpy as np

from crisp.v29.contracts import Layer2Result

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fold 割り当て (V29-I09)
# ---------------------------------------------------------------------------

def _assign_folds(canonical_link_ids: list[str], n_splits: int, cv_seed: int) -> list[int]:
    """canonical_link_id × cv_seed の SHA256 で fold を決定論的に割り当てる。

    V29-I09: mapping_table と falsification_table で同じ cv_seed を使うことで
    canonical_link_id が共通の行に対して fold map の一致を保証する。
    """
    return [
        int(hashlib.sha256(f"{cv_seed}::{link_id}".encode("utf-8")).hexdigest()[:8], 16) % n_splits
        for link_id in canonical_link_ids
    ]


# ---------------------------------------------------------------------------
# 前処理
# ---------------------------------------------------------------------------

def _condition_zscore(rows: list[dict[str, Any]]) -> np.ndarray:
    """condition_hash ごとに functional_score を z-score 正規化する。"""
    values = np.asarray([float(r["functional_score"]) for r in rows], dtype=float)
    conditions = [str(r.get("condition_hash", "default")) for r in rows]
    normalized = np.zeros_like(values)
    for cond in sorted(set(conditions)):
        idx = np.asarray([i for i, c in enumerate(conditions) if c == cond], dtype=int)
        subset = values[idx]
        mu = float(np.mean(subset))
        sd = float(np.std(subset))
        normalized[idx] = (subset - mu) / sd if sd > 1e-12 else subset - mu
    return normalized


def _build_design_matrix(rows: list[dict[str, Any]], feature_names: list[str]) -> np.ndarray:
    """intercept + condition dummies + features の計画行列を構築する。"""
    conditions = [str(r.get("condition_hash", "default")) for r in rows]
    condition_levels = sorted(set(conditions))
    condition_index = {c: i for i, c in enumerate(condition_levels)}
    n_dummies = max(0, len(condition_levels) - 1)

    matrix_rows: list[list[float]] = []
    for row, cond in zip(rows, conditions):
        dummy_vec = [0.0] * n_dummies
        cond_idx = condition_index[cond]
        if cond_idx > 0:
            dummy_vec[cond_idx - 1] = 1.0
        feature_vec = [float(row[name]) for name in feature_names]
        matrix_rows.append([1.0] + dummy_vec + feature_vec)
    return np.asarray(matrix_rows, dtype=float)


def _fit_and_predict(
    x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray
) -> np.ndarray:
    """最小二乗でフィットし test 点を予測する。"""
    coef, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)
    return x_test @ coef


def _r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """決定係数 R²。ss_tot ≒ 0 の場合は 0.0 を返す。"""
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return 0.0 if ss_tot <= 1e-12 else 1.0 - ss_res / ss_tot


# ---------------------------------------------------------------------------
# CV: per-fold R² の計算 (FAIL-2 修正の基盤)
# ---------------------------------------------------------------------------

def _cv_r2_fold_scores(
    rows: list[dict[str, Any]],
    feature_names: list[str],
    cv_seed: int,
    n_splits: int = 3,
) -> list[float] | None:
    """k-fold CV を実施し、fold ごとの R² スコアリストを返す。

    FAIL-2 修正:
    旧実装は全 fold 平均のスカラーを返していた。bootstrap CI の計算には
    fold ごとの値が必要なため list[float] を返すよう変更した。
    全体 R² が必要な場合は np.mean() でまとめる。
    """
    if len(rows) < max(3, n_splits):
        return None

    canonical_link_ids = [str(r["canonical_link_id"]) for r in rows]
    fold_assignments = _assign_folds(canonical_link_ids, n_splits, cv_seed)
    y_all = _condition_zscore(rows)
    x_all = _build_design_matrix(rows, feature_names)

    fold_scores: list[float] = []
    for fold_idx in range(n_splits):
        test_mask = [i for i, f in enumerate(fold_assignments) if f == fold_idx]
        train_mask = [i for i, f in enumerate(fold_assignments) if f != fold_idx]
        if not test_mask or len(train_mask) < 2:
            _log.debug(
                "_cv_r2_fold_scores: fold %d skipped (test=%d, train=%d)",
                fold_idx, len(test_mask), len(train_mask),
            )
            continue
        test_idx = np.asarray(test_mask, dtype=int)
        train_idx = np.asarray(train_mask, dtype=int)
        y_pred = _fit_and_predict(x_all[train_idx], y_all[train_idx], x_all[test_idx])
        fold_scores.append(_r2_score(y_all[test_idx], y_pred))

    return fold_scores if fold_scores else None


def _mean_cv_r2(fold_scores: list[float] | None) -> float | None:
    """fold スコアリストの平均を返す。None 入力は None を返す。"""
    if not fold_scores:
        return None
    return float(np.mean(fold_scores))


def _per_fold_delta(
    base_folds: list[float] | None,
    full_folds: list[float] | None,
) -> list[float] | None:
    """fold ごとの改善量 (full - base) を計算する。

    FAIL-2 修正の核心。fold 数が一致しない場合は zip で短い方に揃える。
    """
    if not base_folds or not full_folds:
        return None
    return [full - base for base, full in zip(base_folds, full_folds)]


# ---------------------------------------------------------------------------
# Bootstrap CI (FAIL-2 修正: per-fold delta を resample)
# ---------------------------------------------------------------------------

def _bootstrap_ci_from_fold_deltas(
    fold_deltas: list[float],
    seed: int,
    n_boot: int = 50,
) -> tuple[float, float] | None:
    """per-fold delta (full - base) のリストを bootstrap resample して 95% CI を返す。

    FAIL-2 修正:
    旧実装は [delta_scalar] * N という定数ベクトルを使っていたため
    CI = (delta, delta) になり E4 崩壊点検出が不能だった。
    正しくは fold ごとの delta をリサンプルして fold 間ばらつきを反映する。
    """
    if len(fold_deltas) < 2:
        _log.debug("bootstrap_ci skipped: fewer than 2 fold deltas (%d)", len(fold_deltas))
        return None
    rng = np.random.default_rng(seed)
    arr = np.asarray(fold_deltas, dtype=float)
    boot_means = [
        float(np.mean(rng.choice(arr, size=len(arr), replace=True)))
        for _ in range(n_boot)
    ]
    lo, hi = np.quantile(np.asarray(boot_means, dtype=float), [0.025, 0.975])
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Layer2 メイン
# ---------------------------------------------------------------------------

def run_layer2(
    mapping_rows: list[dict[str, Any]],
    falsification_rows: list[dict[str, Any]],
    cv_seed: int,
    bootstrap_seed: int,
    n_splits: int = 3,
    n_boot: int = 50,
) -> Layer2Result:
    """canonical-link 単位の CV モデルを実行し Layer2Result を返す。

    モデル定義:
      M1 base: [comb] → functional_score
      M1 full: [comb, PAS] → functional_score
      M2 base: [comb, P_hit] → functional_score
      M2 full: [comb, P_hit, PAS, dist] → functional_score

    V29-I09: mapping / falsification は同一 cv_seed で fold を割り当てる。
    FAIL-2:  bootstrap CI は per-fold delta を resample（定数ベクトル禁止）。
    """
    _log.debug(
        "run_layer2: mapping=%d, falsification=%d, cv_seed=%d, n_splits=%d, n_boot=%d",
        len(mapping_rows), len(falsification_rows), cv_seed, n_splits, n_boot,
    )

    if len(mapping_rows) < max(3, n_splits):
        _log.warning(
            "Layer2 UNCLEAR_SAMPLE_SIZE: mapping rows %d < min %d",
            len(mapping_rows), max(3, n_splits),
        )
        return Layer2Result(
            status="UNCLEAR_SAMPLE_SIZE",
            n_rows_mapping=len(mapping_rows),
            n_rows_falsification=len(falsification_rows),
            cv_r2_m1_base=None,
            cv_r2_m1_full=None,
            cv_r2_m2_base=None,
            cv_r2_m2_full=None,
            delta_cv_r2_m1=None,
            delta_cv_r2_m2=None,
            bootstrap_ci_m1=None,
            bootstrap_ci_m2=None,
            r_shuffle_joint=None,
            diagnostics_json={
                "reason": "too_few_mapping_rows",
                "n_rows_mapping": len(mapping_rows),
                "n_splits": n_splits,
            },
        )

    # V29-I09: fold map 一致検証 ------------------------------------------------
    mapping_ids = {str(r["canonical_link_id"]) for r in mapping_rows}
    fals_ids = {str(r["canonical_link_id"]) for r in falsification_rows}
    id_overlap_count = len(mapping_ids & fals_ids)
    if falsification_rows and id_overlap_count == 0:
        _log.warning(
            "V29-I09 WARNING: mapping and falsification share no canonical_link_ids; "
            "fold assignments will diverge. mapping=%d, falsification=%d",
            len(mapping_ids), len(fals_ids),
        )

    # per-fold R² スコア -------------------------------------------------------
    folds_m1_base = _cv_r2_fold_scores(mapping_rows, ["comb"], cv_seed, n_splits)
    folds_m1_full = _cv_r2_fold_scores(mapping_rows, ["comb", "PAS"], cv_seed, n_splits)
    folds_m2_base = _cv_r2_fold_scores(mapping_rows, ["comb", "P_hit"], cv_seed, n_splits)
    folds_m2_full = _cv_r2_fold_scores(
        mapping_rows, ["comb", "P_hit", "PAS", "dist"], cv_seed, n_splits
    )

    cv_r2_m1_base = _mean_cv_r2(folds_m1_base)
    cv_r2_m1_full = _mean_cv_r2(folds_m1_full)
    cv_r2_m2_base = _mean_cv_r2(folds_m2_base)
    cv_r2_m2_full = _mean_cv_r2(folds_m2_full)

    # per-fold delta -----------------------------------------------------------
    fold_deltas_m1 = _per_fold_delta(folds_m1_base, folds_m1_full)
    fold_deltas_m2 = _per_fold_delta(folds_m2_base, folds_m2_full)

    delta_cv_r2_m1 = _mean_cv_r2(fold_deltas_m1)
    delta_cv_r2_m2 = _mean_cv_r2(fold_deltas_m2)

    # bootstrap CI from per-fold delta (FAIL-2 修正) ---------------------------
    ci_m1 = (
        _bootstrap_ci_from_fold_deltas(fold_deltas_m1, seed=bootstrap_seed, n_boot=n_boot)
        if fold_deltas_m1 else None
    )
    ci_m2 = (
        _bootstrap_ci_from_fold_deltas(fold_deltas_m2, seed=bootstrap_seed + 1, n_boot=n_boot)
        if fold_deltas_m2 else None
    )

    # cap shuffle falsification との比較 ---------------------------------------
    fals_m2_full: float | None = None
    r_shuffle_joint: float | None = None
    if falsification_rows:
        fals_folds = _cv_r2_fold_scores(
            falsification_rows,
            ["comb", "P_hit", "PAS", "dist"],
            cv_seed=cv_seed,
            n_splits=min(n_splits, len(falsification_rows)),
        )
        fals_m2_full = _mean_cv_r2(fals_folds)
        if fals_m2_full is not None and cv_r2_m2_full not in (None, 0.0):
            denom = max(abs(float(cv_r2_m2_full)), 1e-8)
            r_shuffle_joint = float(max(0.0, min(1.0, abs(fals_m2_full) / denom)))

    _log.info(
        "Layer2 OK: delta_m1=%.4f, delta_m2=%.4f, ci_m1=%s, ci_m2=%s, r_shuffle=%.3f",
        delta_cv_r2_m1 or 0.0,
        delta_cv_r2_m2 or 0.0,
        ci_m1,
        ci_m2,
        r_shuffle_joint or 0.0,
    )

    return Layer2Result(
        status="OK",
        n_rows_mapping=len(mapping_rows),
        n_rows_falsification=len(falsification_rows),
        cv_r2_m1_base=cv_r2_m1_base,
        cv_r2_m1_full=cv_r2_m1_full,
        cv_r2_m2_base=cv_r2_m2_base,
        cv_r2_m2_full=cv_r2_m2_full,
        delta_cv_r2_m1=delta_cv_r2_m1,
        delta_cv_r2_m2=delta_cv_r2_m2,
        bootstrap_ci_m1=ci_m1,
        bootstrap_ci_m2=ci_m2,
        r_shuffle_joint=r_shuffle_joint,
        diagnostics_json={
            "falsification_cv_r2_m2_full": fals_m2_full,
            "n_splits": n_splits,
            "n_boot": n_boot,
            "model_family": "fixed_effects_only",
            "fold_map_overlap_count": id_overlap_count,
            "bootstrap_ci_source": "per_fold_delta",  # FAIL-2 修正のマーカー
        },
    )
