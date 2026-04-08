"""collapse_figure_spec ビルダー: ablation / falsification 一枚図の仕様を生成する。

設計書 §別紙 E §E5 に準拠。

x 軸順は E5.1 の定義に従う。current snapshot では Rule3 lanes は
trace-only invariance 条件のため skipped_conditions に記録される。
"""
from __future__ import annotations

from typing import Any, Mapping

from crisp.v3.report_guards import attach_guarded_exploratory_payload
from .contract import build_report_contract_fields

# 設計書 E5.1 の x 軸順（全 11 条件）
_FULL_CONDITION_ORDER: list[str] = [
    "native",
    "shuffle_axis",
    "shuffle_polar",
    "shuffle_joint",
    "rule1_sensor_drop",
    "rule1_threshold_off",
    "rule3_no_struct_conn",       # Phase-aware: current snapshot では invariance
    "rule3_random_order",          # 同上
    "rule3_no_near_band",          # 同上
    "layer1_off",
    "layer2_off",
]


def build_collapse_figure_spec(
    *,
    run_id: str,
    resource_profile: str,
    conditions: list[str],
    cap_metrics: dict[str, Any],
    comparison_type: str | None = None,
    comparison_type_source: str | None = None,
    skip_reason_codes: list[str] | None = None,
    inventory_json_errors: list[dict[str, Any]] | list[Any] | None = None,
    cap_truth_source_provenance: dict[str, Any] | None = None,
    pathyes_mode_requested: str | None = None,
    pathyes_mode_resolved: str | None = None,
    pathyes_state_source: str | None = None,
    pathyes_diagnostics_status: str | None = None,
    pathyes_diagnostics_error_code: str | None = None,
    pathyes_diagnostics_source: str | None = None,
    pathyes_goal_precheck_passed: bool | None = None,
    pathyes_rule1_applicability: str | None = None,
    pathyes_skip_code: str | None = None,
    rule3_phase_aware: bool = True,
    exploratory_metadata: Mapping[str, Any] | None = None,
    exploratory_sections: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """collapse_figure_spec.json のペイロードを生成する。

    x_axis_conditions は実際に実行された conditions を E5.1 の順序でソートして設定する。
    skipped_conditions はスキップされた条件をリストアップする。

    崩壊点（E5.3 注記に必須）:
      ci_crosses_zero, r_shuffle_joint_ci_upper_gt_0_5,
      stable_fraction_drop_ge_0_10, reason_code_flip, run_mode_complete_false
    """
    # E5.1 の順序に揃えた実行済み条件リスト
    ordered_conditions = [c for c in _FULL_CONDITION_ORDER if c in conditions]
    # 順序未定義の条件は末尾に追加（拡張への互換性）
    for c in conditions:
        if c not in ordered_conditions:
            ordered_conditions.append(c)

    skipped = [c for c in _FULL_CONDITION_ORDER if c not in conditions]

    payload = {
        "run_id": run_id,
        "resource_profile": resource_profile,
        "x_axis_conditions": ordered_conditions,
        "x_axis_full_spec": _FULL_CONDITION_ORDER,
        "skipped_conditions": skipped,
        "y_axes": {
            "upper": ["L0_gain_norm", "L1_gain_norm", "L2_gain_norm"],
            "lower": ["core_stable_fraction", "rule1_stable_fraction", "cap_batch_stability"],
        },
        "phase_aware_rule3": bool(rule3_phase_aware),
        # E4 崩壊点定義（E5.3 注記必須）
        "collapse_conditions": [
            "ci_crosses_zero",
            "r_shuffle_joint_ci_upper_gt_0_5",
            "stable_fraction_drop_ge_0_10",
            "reason_code_flip",
            "run_mode_complete_false",
        ],
        "cap_metrics": cap_metrics,
        # E4 注記: current snapshot の Rule3 lanes は baseline 一致を pass 条件とする
        "rule3_lane_note": (
            "current_snapshot_invariance_only"
            if rule3_phase_aware else "outcome_collapse_enabled"
        ),
    }
    payload.update(build_report_contract_fields(
        comparison_type=comparison_type,
        comparison_type_source=comparison_type_source,
        skip_reason_codes=skip_reason_codes,
        inventory_json_errors=inventory_json_errors,
        cap_truth_source_provenance=cap_truth_source_provenance,
        pathyes_mode_requested=pathyes_mode_requested,
        pathyes_mode_resolved=pathyes_mode_resolved,
        pathyes_state_source=pathyes_state_source,
        pathyes_diagnostics_status=pathyes_diagnostics_status,
        pathyes_diagnostics_error_code=pathyes_diagnostics_error_code,
        pathyes_diagnostics_source=pathyes_diagnostics_source,
        pathyes_goal_precheck_passed=pathyes_goal_precheck_passed,
        pathyes_rule1_applicability=pathyes_rule1_applicability,
        pathyes_skip_code=pathyes_skip_code,
    ))
    if exploratory_sections:
        if exploratory_metadata is None:
            raise ValueError("exploratory_metadata is required when exploratory_sections are provided")
        payload = attach_guarded_exploratory_payload(
            artifact_name="collapse_figure_spec.json",
            payload=payload,
            metadata=exploratory_metadata,
            sections=exploratory_sections,
        )
    return payload
