"""Cap Batch SCV: FAIL-3 修正（reason_code 体系）の確認。"""
from __future__ import annotations

from crisp.v29.cap.scv import run_cap_batch_scv
from crisp.v29.contracts import CapBatchEval, Layer2Result


def _native(i: int) -> dict:
    return {"pairing_role": "native", "comb": 0.6, "PAS": 0.5, "P_hit": 0.4, "dist": 0.3, "idx": i}


def _fals(i: int) -> dict:
    return {"pairing_role": "matched_falsification", "comb": 0.3, "PAS": 0.2, "P_hit": 0.2, "dist": 0.4, "idx": i}


def _layer2(delta_m2: float | None, r_shuffle: float | None) -> Layer2Result:
    return Layer2Result(
        status="OK",
        n_rows_mapping=10, n_rows_falsification=5,
        cv_r2_m1_base=0.1, cv_r2_m1_full=0.15,
        cv_r2_m2_base=0.2, cv_r2_m2_full=0.3,
        delta_cv_r2_m1=0.05, delta_cv_r2_m2=delta_m2,
        bootstrap_ci_m1=None, bootstrap_ci_m2=None,
        r_shuffle_joint=r_shuffle,
        diagnostics_json={},
    )


def test_batch_scv_truth_source_and_final_verdict() -> None:
    rows = [_native(i) for i in range(5)] + [_fals(i) for i in range(3)]
    result = run_cap_batch_scv(run_id="run_x", pair_features_rows=rows, layer2_result=None)
    assert isinstance(result, CapBatchEval)
    assert result.source_of_truth is True
    assert result.cap_batch_verdict in {"PASS", "FAIL", "UNCLEAR"}


def test_l2_shuffle_joint_uses_l2_reason_code() -> None:
    """FAIL-3 修正確認: r_shuffle_joint > 0.5 は FAIL_L2_SHUFFLE_JOINT_RESISTANT を使う。"""
    rows = [_native(i) for i in range(5)] + [_fals(i) for i in range(3)]
    # delta_m2 > 0 だが r_shuffle_joint > 0.5 → FAIL_L2_SHUFFLE_JOINT_RESISTANT
    l2 = _layer2(delta_m2=0.1, r_shuffle=0.7)
    result = run_cap_batch_scv(run_id="run_x", pair_features_rows=rows, layer2_result=l2)
    assert "FAIL_L2_SHUFFLE_JOINT_RESISTANT" in result.reason_codes, (
        f"Expected FAIL_L2_SHUFFLE_JOINT_RESISTANT, got {result.reason_codes}"
    )
    # 旧コードの誤り: FAIL_L1_SHUFFLE_RESISTANT は Layer1 判定にのみ使う
    # r_shuffle_joint の判定では使わない
    assert result.reason_codes.count("FAIL_L1_SHUFFLE_RESISTANT") <= 1, (
        "FAIL_L1_SHUFFLE_RESISTANT should only appear if Layer1 also fails"
    )


def test_l1_shuffle_uses_l1_reason_code() -> None:
    """Layer1 FAIL は FAIL_L1_SHUFFLE_RESISTANT を使う（変更なし）。"""
    # native_pas < fals_pas になるよう設定
    native_rows = [{"pairing_role": "native", "comb": 0.6, "PAS": 0.1, "P_hit": 0.4, "dist": 0.3}
                   for _ in range(5)]
    fals_rows = [{"pairing_role": "matched_falsification", "comb": 0.3, "PAS": 0.8, "P_hit": 0.2, "dist": 0.4}
                 for _ in range(3)]
    rows = native_rows + fals_rows
    result = run_cap_batch_scv(run_id="run_y", pair_features_rows=rows, layer2_result=None)
    assert "FAIL_L1_SHUFFLE_RESISTANT" in result.reason_codes


def test_l2_no_kinetic_mapping_reason_code() -> None:
    """delta_cv_r2_m2 <= 0 は FAIL_L2_NO_KINETIC_MAPPING を使う。"""
    rows = [_native(i) for i in range(5)] + [_fals(i) for i in range(3)]
    l2 = _layer2(delta_m2=-0.05, r_shuffle=None)
    result = run_cap_batch_scv(run_id="run_z", pair_features_rows=rows, layer2_result=l2)
    assert "FAIL_L2_NO_KINETIC_MAPPING" in result.reason_codes


def test_unclear_when_empty_rows() -> None:
    result = run_cap_batch_scv(run_id="run_e", pair_features_rows=[], layer2_result=None)
    assert result.cap_batch_verdict == "UNCLEAR"
    assert result.cap_batch_reason_code == "UNCLEAR_SAMPLE_SIZE"
