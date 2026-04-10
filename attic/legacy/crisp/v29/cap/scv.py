"""Cap Batch SCV: run-level Cap verdict の唯一の truth source。

設計書 §4A-3, V29-I02, V29-I06, 別紙 D §D2.2 に準拠。

責務:
  - pair_features_rows (Layer0/1 観測量) と Layer2Result を受け取る
  - run-level の Cap batch verdict を決定する（PASS / FAIL / UNCLEAR）
  - cap_batch_eval.json の truth source として source_of_truth=True で出力する

禁止:
  - eval_report.json に verdict キーを持たせる（→ writers.py の guard が防ぐ）
  - Core branch の compound-target verdict と混合する

reason_code 体系（FAIL-3 修正）:
  Layer0 判定: FAIL_L0_SHUFFLE_INSENSITIVE
  Layer1 判定: FAIL_L1_SHUFFLE_RESISTANT
  Layer2 判定:
    FAIL_L2_NO_KINETIC_MAPPING   ... delta_cv_r2_m2 <= 0
    FAIL_L2_SHUFFLE_JOINT_RESISTANT ... r_shuffle_joint > 0.5  ← FAIL-3 修正
  Sample size: UNCLEAR_SAMPLE_SIZE
"""
from __future__ import annotations

import logging
from typing import Any

from crisp.v29.contracts import CapBatchEval, Layer2Result

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------

def _row_mean(rows: list[dict[str, Any]], key: str) -> float | None:
    """rows が空の場合は None を返す。"""
    if not rows:
        return None
    return sum(float(r[key]) for r in rows) / len(rows)


def _split_by_role(
    pair_features_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """native と matched_falsification を分離する（V29-I06, V29-I08）。"""
    native = [r for r in pair_features_rows if r.get("pairing_role") == "native"]
    falsification = [
        r for r in pair_features_rows if r.get("pairing_role") == "matched_falsification"
    ]
    return native, falsification


# ---------------------------------------------------------------------------
# SCV 本体
# ---------------------------------------------------------------------------

def run_cap_batch_scv(
    *,
    run_id: str,
    pair_features_rows: list[dict[str, Any]],
    layer2_result: Layer2Result | None,
) -> CapBatchEval:
    """run-level Cap batch verdict を計算して返す。

    §4A-3: cap_batch_eval.json が唯一の truth source であることを
    source_of_truth=True フラグで明示する。

    FAIL-3 修正:
    Layer2 の r_shuffle_joint 判定に誤って FAIL_L1_SHUFFLE_RESISTANT を
    付与していた箇所を FAIL_L2_SHUFFLE_JOINT_RESISTANT に修正した。
    """
    _log.debug(
        "run_cap_batch_scv: run_id=%s, pair_features=%d, layer2=%s",
        run_id, len(pair_features_rows),
        layer2_result.status if layer2_result else "None",
    )

    if not pair_features_rows:
        _log.warning("run_cap_batch_scv: no pair_features_rows → UNCLEAR_SAMPLE_SIZE")
        return CapBatchEval(
            run_id=run_id,
            status="UNCLEAR",
            cap_batch_verdict="UNCLEAR",
            cap_batch_reason_code="UNCLEAR_SAMPLE_SIZE",
            verdict_layer0="UNCLEAR",
            verdict_layer1="UNCLEAR",
            verdict_layer2="UNCLEAR",
            verdict_final="UNCLEAR",
            reason_codes=["UNCLEAR_SAMPLE_SIZE"],
            diagnostics_json={"reason": "no_pair_features"},
        )

    native_rows, fals_rows = _split_by_role(pair_features_rows)

    native_comb = _row_mean(native_rows, "comb")
    fals_comb = _row_mean(fals_rows, "comb")
    native_pas = _row_mean(native_rows, "PAS")
    fals_pas = _row_mean(fals_rows, "PAS")

    reason_codes: list[str] = []

    # --- Layer0 判定 (comb: native > falsification) ---
    verdict_l0 = "PASS"
    if native_comb is None or len(native_rows) < 3:
        verdict_l0 = "UNCLEAR"
        reason_codes.append("UNCLEAR_SAMPLE_SIZE")
    elif fals_comb is not None and native_comb <= fals_comb:
        verdict_l0 = "FAIL"
        reason_codes.append("FAIL_L0_SHUFFLE_INSENSITIVE")

    # --- Layer1 判定 (PAS: native > falsification) ---
    verdict_l1 = "PASS"
    if native_pas is None or len(native_rows) < 3:
        verdict_l1 = "UNCLEAR"
        if "UNCLEAR_SAMPLE_SIZE" not in reason_codes:
            reason_codes.append("UNCLEAR_SAMPLE_SIZE")
    elif fals_pas is not None and native_pas <= fals_pas:
        verdict_l1 = "FAIL"
        reason_codes.append("FAIL_L1_SHUFFLE_RESISTANT")

    # --- Layer2 判定 ---
    verdict_l2: str | None = None
    if layer2_result is None:
        verdict_l2 = None
    elif layer2_result.status == "UNCLEAR_SAMPLE_SIZE":
        verdict_l2 = "UNCLEAR"
        if "UNCLEAR_SAMPLE_SIZE" not in reason_codes:
            reason_codes.append("UNCLEAR_SAMPLE_SIZE")
    else:
        verdict_l2 = "PASS"

        # delta_cv_r2_m2 <= 0 → kinetics-proxy が幾何量に追加説明力を持たない
        if layer2_result.delta_cv_r2_m2 is None or layer2_result.delta_cv_r2_m2 <= 0.0:
            verdict_l2 = "FAIL"
            reason_codes.append("FAIL_L2_NO_KINETIC_MAPPING")

        # r_shuffle_joint > 0.5 → falsification が native と区別できない
        # FAIL-3 修正: Layer2 指標には Layer2 の reason_code を使う
        if (
            layer2_result.r_shuffle_joint is not None
            and layer2_result.r_shuffle_joint > 0.5
        ):
            verdict_l2 = "FAIL"
            # 旧コードは FAIL_L1_SHUFFLE_RESISTANT を誤使用していた（FAIL-3 修正）
            if "FAIL_L2_SHUFFLE_JOINT_RESISTANT" not in reason_codes:
                reason_codes.append("FAIL_L2_SHUFFLE_JOINT_RESISTANT")

    # --- 最終判定 ---
    active_verdicts = [v for v in (verdict_l0, verdict_l1, verdict_l2) if v is not None]
    if any(v == "FAIL" for v in active_verdicts):
        final_verdict = "FAIL"
    elif any(v == "UNCLEAR" for v in active_verdicts):
        final_verdict = "UNCLEAR"
    else:
        final_verdict = "PASS"

    primary_reason = reason_codes[0] if reason_codes else None

    _log.info(
        "run_cap_batch_scv: verdict=%s, reason=%s, l0=%s, l1=%s, l2=%s",
        final_verdict, primary_reason, verdict_l0, verdict_l1, verdict_l2,
    )

    return CapBatchEval(
        run_id=run_id,
        status="OK",
        cap_batch_verdict=final_verdict,
        cap_batch_reason_code=primary_reason,
        verdict_layer0=verdict_l0,
        verdict_layer1=verdict_l1,
        verdict_layer2=verdict_l2,
        verdict_final=final_verdict,
        reason_codes=reason_codes,
        diagnostics_json={
            "native_comb_mean": native_comb,
            "fals_comb_mean": fals_comb,
            "native_pas_mean": native_pas,
            "fals_pas_mean": fals_pas,
            "native_row_count": len(native_rows),
            "fals_row_count": len(fals_rows),
            "layer2": None if layer2_result is None else layer2_result.to_dict(),
        },
    )
