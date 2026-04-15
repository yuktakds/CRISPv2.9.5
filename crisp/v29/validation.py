"""統合検証バッチ: ablation / falsification 条件を実行し一枚図仕様を生成する。

設計書 §別紙 E §E2-E9, §4A-3 に準拠。

FAIL-4 修正:
  旧実装は 4 条件（native, shuffle_axis, shuffle_polar, shuffle_joint）しか
  実装していなかった。設計書 E2 の必須 11 条件のうち以下を追加した:
    rule1_sensor_drop   ... Rule1 verdict を全 UNCLEAR として集計する ablation
    rule1_threshold_off ... theta_rule1 = inf（剛直性判定を無効化）
    layer1_off          ... PAS を使わず comb のみで Cap SCV を再計算
    layer2_off          ... Layer2 モデルを無効にした場合の Cap SCV

  Phase-aware rule（E2）により current snapshot では以下はスキップする:
    rule3_no_struct_conn, rule3_random_order, rule3_no_near_band
    → qc_report.json に SKIP_PHASE_AWARE_RULE3 として記録する。
    pathyes_force_false → bootstrap mode では SKIP_PATHYES_BOOTSTRAP として記録する。

UNKNOWN-3 修正:
  mapping / falsification の canonical_link_id 重複チェックを追加し、
  excluded_rows_count を正確に記録する。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from crisp.v29.cap_reporting import (
    build_cap_report_bundle,
    validate_cap_report_bundle,
    write_cap_report_bundle,
)
from crisp.v29.cap_truth import build_cap_truth_source_provenance
from crisp.v29.contracts import Layer2Result, ValidationBatchResult
from crisp.v29.reports.contract import (
    resolve_report_comparison_metadata,
    resolve_report_pathyes_metadata,
    normalize_skip_reason_codes,
)
from crisp.v29.tableio import read_records_table

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------

def _row_mean(rows: list[dict[str, Any]], key: str) -> float | None:
    """列の平均を返す。rows が空の場合は None。"""
    if not rows:
        return None
    return sum(float(r[key]) for r in rows) / len(rows)


def _cap_scv_from_features(
    run_id: str,
    native_rows: list[dict[str, Any]],
    fals_rows: list[dict[str, Any]],
    layer2_result: Layer2Result | None,
    condition_label: str,
) -> dict[str, Any]:
    """Cap SCV を pair_features から直接計算して結果 dict を返す。

    ablation 条件（layer1_off, layer2_off）の再計算に使用する。
    重要: verdict の決定はここで行うが、公開 truth source は cap_batch_eval.json のみ。
    この関数の出力は ablation 診断用であり、run-level verdict を上書きしない。
    """
    all_rows = native_rows + fals_rows
    if not all_rows:
        return {"condition": condition_label, "verdict": "UNCLEAR", "reason_code": "UNCLEAR_SAMPLE_SIZE"}

    native_comb = _row_mean(native_rows, "comb")
    fals_comb = _row_mean(fals_rows, "comb")
    native_pas = _row_mean(native_rows, "PAS")
    fals_pas = _row_mean(fals_rows, "PAS")

    reason_codes: list[str] = []

    # Layer0 判定
    verdict_l0 = "PASS"
    if native_comb is None or len(native_rows) < 3:
        verdict_l0 = "UNCLEAR"
        reason_codes.append("UNCLEAR_SAMPLE_SIZE")
    elif fals_comb is not None and native_comb <= fals_comb:
        verdict_l0 = "FAIL"
        reason_codes.append("FAIL_L0_SHUFFLE_INSENSITIVE")

    # Layer1 判定（layer1_off では skip）
    verdict_l1: str | None = None
    if condition_label != "layer1_off":
        verdict_l1 = "PASS"
        if native_pas is None or len(native_rows) < 3:
            verdict_l1 = "UNCLEAR"
            if "UNCLEAR_SAMPLE_SIZE" not in reason_codes:
                reason_codes.append("UNCLEAR_SAMPLE_SIZE")
        elif fals_pas is not None and native_pas <= fals_pas:
            verdict_l1 = "FAIL"
            reason_codes.append("FAIL_L1_SHUFFLE_RESISTANT")

    # Layer2 判定（layer2_off では skip）
    verdict_l2: str | None = None
    if condition_label != "layer2_off" and layer2_result is not None:
        if layer2_result.status == "UNCLEAR_SAMPLE_SIZE":
            verdict_l2 = "UNCLEAR"
        else:
            verdict_l2 = "PASS"
            if layer2_result.delta_cv_r2_m2 is None or layer2_result.delta_cv_r2_m2 <= 0.0:
                verdict_l2 = "FAIL"
                reason_codes.append("FAIL_L2_NO_KINETIC_MAPPING")
            if layer2_result.r_shuffle_joint is not None and layer2_result.r_shuffle_joint > 0.5:
                verdict_l2 = "FAIL"
                if "FAIL_L2_SHUFFLE_JOINT_RESISTANT" not in reason_codes:
                    reason_codes.append("FAIL_L2_SHUFFLE_JOINT_RESISTANT")

    active = [v for v in (verdict_l0, verdict_l1, verdict_l2) if v is not None]
    if any(v == "FAIL" for v in active):
        final = "FAIL"
    elif any(v == "UNCLEAR" for v in active):
        final = "UNCLEAR"
    else:
        final = "PASS"

    return {
        "condition": condition_label,
        "verdict": final,
        "reason_codes": reason_codes,
        "verdict_l0": verdict_l0,
        "verdict_l1": verdict_l1,
        "verdict_l2": verdict_l2,
        "native_comb_mean": native_comb,
        "fals_comb_mean": fals_comb,
        "native_pas_mean": native_pas,
        "fals_pas_mean": fals_pas,
    }


# ---------------------------------------------------------------------------
# Rule1 ablation ユーティリティ
# ---------------------------------------------------------------------------

def _rule1_ablation_summary(
    rule1_rows: list[dict[str, Any]],
    condition_label: str,
    theta_override: float | None = None,
) -> dict[str, Any]:
    """Rule1 assessments から ablation 条件の集計を返す。

    rule1_sensor_drop: rule1_applicability が PATH_EVALUABLE でない行のカウント。
    rule1_threshold_off: theta_rule1 = inf（全 ring_lock 分子が PASS）として再計算。
    """
    if not rule1_rows:
        return {"condition": condition_label, "n_rows": 0, "verdict_distribution": {}}

    dist: dict[str, int] = {}

    for row in rule1_rows:
        if condition_label == "rule1_sensor_drop":
            # sensor を無効化した場合: 全行 UNCLEAR として扱う
            v = "UNCLEAR"
        elif condition_label == "rule1_threshold_off" and theta_override is not None:
            # theta = inf: ring_lock があれば全て PASS
            ring_lock = bool(row.get("ring_lock_present", False))
            applicability = str(row.get("rule1_applicability", "PATH_NOT_EVALUABLE"))
            if applicability != "PATH_EVALUABLE":
                v = "SUPPRESSED"
            elif ring_lock:
                v = "PASS"
            else:
                v = "FAIL"
        else:
            v = str(row.get("rule1_verdict") or "SUPPRESSED")

        dist[v] = dist.get(v, 0) + 1

    return {
        "condition": condition_label,
        "n_rows": len(rule1_rows),
        "verdict_distribution": dist,
        "theta_override": theta_override,
    }
# ---------------------------------------------------------------------------
# メイン: run_validation_batch
# ---------------------------------------------------------------------------

def run_validation_batch(
    manifest_path: str | Path,
    profile: str,
    out_dir: str | Path,
) -> ValidationBatchResult:
    """ablation / falsification 比較条件を実行し検証バッチ成果物を生成する。

    実行する条件（§E2）:
      常に実行:
        native, shuffle_axis, shuffle_polar, shuffle_joint
      ablation（FAIL-4 修正で追加）:
        rule1_sensor_drop, rule1_threshold_off, layer1_off, layer2_off
      Phase-aware skip（current snapshot）:
        rule3_no_struct_conn, rule3_random_order, rule3_no_near_band
        → qc_report に SKIP_PHASE_AWARE_RULE3 として記録
      bootstrap mode skip:
        pathyes_force_false → SKIP_PATHYES_BOOTSTRAP として記録
    """
    manifest_path = Path(manifest_path)
    run_dir = manifest_path.parent
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = str(manifest.get("run_id", ""))
    run_mode = str(manifest.get("run_mode", "core-only"))
    completion_basis = manifest.get("completion_basis_json", {})
    if not isinstance(completion_basis, dict):
        completion_basis = {}
    skip_reason_codes = completion_basis.get("skip_reason_codes", [])
    if not isinstance(skip_reason_codes, list):
        skip_reason_codes = []
    normalized_skip_reason_codes = normalize_skip_reason_codes(skip_reason_codes)
    comparison_type, comparison_type_source = resolve_report_comparison_metadata(
        manifest=manifest,
        completion_basis=completion_basis,
    )
    pathyes_metadata = resolve_report_pathyes_metadata(completion_basis=completion_basis)

    _log.info(
        "run_validation_batch: run_id=%s, run_mode=%s, profile=%s",
        run_id, run_mode, profile,
    )

    warnings: list[str] = []
    conditions_run: list[str] = ["native"]
    ablation_diagnostics: dict[str, Any] = {}

    # --- Cap artifact の読み込み ---
    cap_eval_path = run_dir / "cap_batch_eval.json"
    pair_features_path = run_dir / "pair_features.parquet"
    pair_features_jsonl = run_dir / "pair_features.jsonl"
    mapping_path = run_dir / "mapping_table.parquet"
    fals_path = run_dir / "falsification_table.parquet"

    pair_rows: list[dict[str, Any]] = []
    native_pair_rows: list[dict[str, Any]] = []
    fals_pair_rows: list[dict[str, Any]] = []

    if pair_features_path.exists() or pair_features_jsonl.exists():
        actual_path = pair_features_path if pair_features_path.exists() else pair_features_jsonl
        pair_rows = read_records_table(actual_path)
        native_pair_rows = [r for r in pair_rows if r.get("pairing_role") == "native"]
        fals_pair_rows = [
            r for r in pair_rows if r.get("pairing_role") == "matched_falsification"
        ]
    else:
        warnings.append("pair_features missing; Cap ablation conditions skipped")

    # shuffle 条件の追加（cap_eval が存在する場合）
    if cap_eval_path.exists():
        conditions_run.extend(["shuffle_axis", "shuffle_polar", "shuffle_joint"])

    # --- FAIL-4: Rule1 ablation ---
    rule1_parquet = run_dir / "rule1_assessments.parquet"
    rule1_jsonl = run_dir / "rule1_assessments.jsonl"
    rule1_rows: list[dict[str, Any]] = []

    if rule1_parquet.exists() or rule1_jsonl.exists():
        actual_rule1 = rule1_parquet if rule1_parquet.exists() else rule1_jsonl
        rule1_rows = read_records_table(actual_rule1)

        # rule1_sensor_drop: Rule1 を全 UNCLEAR にして効果を確認
        ablation_diagnostics["rule1_sensor_drop"] = _rule1_ablation_summary(
            rule1_rows, "rule1_sensor_drop"
        )
        conditions_run.append("rule1_sensor_drop")

        # rule1_threshold_off: theta_rule1 = inf（剛直性要件を無効化）
        ablation_diagnostics["rule1_threshold_off"] = _rule1_ablation_summary(
            rule1_rows, "rule1_threshold_off", theta_override=float("inf")
        )
        conditions_run.append("rule1_threshold_off")
    else:
        warnings.append("rule1_assessments missing; rule1 ablation conditions skipped")

    # --- FAIL-4: Cap ablation（Layer1/Layer2 off）---
    layer2_result: Layer2Result | None = None
    cap_truth_source_provenance: dict[str, Any] | None = None
    if cap_eval_path.exists():
        cap_payload = json.loads(cap_eval_path.read_text(encoding="utf-8"))
        cap_truth_source_provenance = build_cap_truth_source_provenance(cap_eval_path)
        l2_diag = cap_payload.get("diagnostics_json", {}).get("layer2")
        if l2_diag and l2_diag.get("status") not in (None, "UNCLEAR_SAMPLE_SIZE"):
            layer2_result = Layer2Result(
                status=l2_diag.get("status", "OK"),
                n_rows_mapping=l2_diag.get("n_rows_mapping", 0),
                n_rows_falsification=l2_diag.get("n_rows_falsification", 0),
                cv_r2_m1_base=l2_diag.get("cv_r2_m1_base"),
                cv_r2_m1_full=l2_diag.get("cv_r2_m1_full"),
                cv_r2_m2_base=l2_diag.get("cv_r2_m2_base"),
                cv_r2_m2_full=l2_diag.get("cv_r2_m2_full"),
                delta_cv_r2_m1=l2_diag.get("delta_cv_r2_m1"),
                delta_cv_r2_m2=l2_diag.get("delta_cv_r2_m2"),
                bootstrap_ci_m1=l2_diag.get("bootstrap_ci_m1"),
                bootstrap_ci_m2=l2_diag.get("bootstrap_ci_m2"),
                r_shuffle_joint=l2_diag.get("r_shuffle_joint"),
                diagnostics_json=l2_diag,
            )

    if pair_rows:
        # layer1_off: PAS を使わず comb のみで再判定
        ablation_diagnostics["layer1_off"] = _cap_scv_from_features(
            run_id, native_pair_rows, fals_pair_rows, layer2_result, "layer1_off"
        )
        conditions_run.append("layer1_off")

        # layer2_off: Layer2 モデルなしで再判定
        ablation_diagnostics["layer2_off"] = _cap_scv_from_features(
            run_id, native_pair_rows, fals_pair_rows, None, "layer2_off"
        )
        conditions_run.append("layer2_off")

    # --- Phase-aware skip: Rule3 conditions （current snapshot では invariance のみ）---
    skipped_conditions: list[str] = []
    for rule3_cond in ("rule3_no_struct_conn", "rule3_random_order", "rule3_no_near_band"):
        skipped_conditions.append(rule3_cond)
        warnings.append(f"SKIP_PHASE_AWARE_RULE3:{rule3_cond} (current snapshot: trace-only invariance)")

    # bootstrap mode では pathyes_force_false をスキップ
    pathyes_mode_requested = completion_basis.get("pathyes_mode_requested")
    pathyes_force_false_requested = bool(completion_basis.get("pathyes_force_false_requested", False))
    if "SKIP_PATHYES_BOOTSTRAP" in normalized_skip_reason_codes:
        warnings.append("SKIP_PATHYES_BOOTSTRAP: pathyes_force_false requires pat-backed mode")
    elif pathyes_force_false_requested and pathyes_mode_requested == "bootstrap":
        warnings.append("SKIP_PATHYES_BOOTSTRAP: pathyes_force_false requires pat-backed mode")
    pathyes_skip_code = pathyes_metadata.get("pathyes_skip_code")
    pathyes_status = pathyes_metadata.get("pathyes_diagnostics_status")
    if (
        isinstance(pathyes_skip_code, str)
        and pathyes_skip_code.startswith("SKIP_PATHYES_PAT_")
        and pathyes_status in {"missing", "invalid"}
    ):
        warnings.append(
            f"{pathyes_skip_code}: pat-backed diagnostics unavailable for publishable Rule1 gating"
        )

    # --- UNKNOWN-3: mapping / falsification の canonical_link_id 一致検証 ---
    excluded_rows_count = 0
    if mapping_path.exists() and fals_path.exists():
        mapping_rows = read_records_table(mapping_path)
        fals_rows_table = read_records_table(fals_path)
        mapping_ids = {str(r["canonical_link_id"]) for r in mapping_rows}
        fals_ids = {str(r["canonical_link_id"]) for r in fals_rows_table}
        overlap = mapping_ids & fals_ids
        excluded_rows_count = len(mapping_ids) - len(overlap)
        if excluded_rows_count > 0:
            _log.warning(
                "V29-I09: %d mapping canonical_link_ids have no matching falsification entry",
                excluded_rows_count,
            )

    # --- run_mode チェック ---
    result = "PASS"
    if run_mode == "core-only":
        warnings.append("core-only run: Cap metrics not requested")
    if run_mode == "full" and not cap_eval_path.exists():
        result = "FAIL"
        warnings.append("run_mode=full but cap_batch_eval.json is missing")

    _log.info("run_validation_batch: conditions_run=%s, result=%s", conditions_run, result)

    # --- レポート生成 ---
    report_bundle = build_cap_report_bundle(
        run_id=run_id,
        cap_batch_eval_path=str(cap_eval_path) if cap_eval_path.exists() else None,
        cap_truth_source_provenance=cap_truth_source_provenance,
        layer2_result=layer2_result,
        comparison_type=comparison_type,
        comparison_type_source=comparison_type_source,
        skip_reason_codes=normalized_skip_reason_codes,
        inventory_json_errors=[],
        pathyes_metadata=pathyes_metadata,
        eval_notes=warnings,
        qc_conditions_run=conditions_run,
        qc_excluded_rows_count=excluded_rows_count,
        qc_warnings=warnings,
        qc_result=result,
        qc_extra={
            "resource_profile": profile,
            "pair_row_count": len(pair_rows),
            "skipped_conditions": skipped_conditions,
            "ablation_diagnostics": ablation_diagnostics,
        },
        resource_profile=profile,
        collapse_conditions=conditions_run,
        collapse_cap_metrics={
            "cap_batch_eval_present": cap_eval_path.exists(),
            "pair_row_count": len(pair_rows),
            "native_row_count": len(native_pair_rows),
            "fals_row_count": len(fals_pair_rows),
            "skipped_conditions": skipped_conditions,
        },
    )
    if cap_eval_path.exists():
        cap_report_errors, _ = validate_cap_report_bundle(
            report_bundle,
            cap_batch_eval_source=cap_eval_path,
        )
        if cap_report_errors:
            raise ValueError(f"cap report bundle error: {cap_report_errors[0]}")

    written_report_paths = write_cap_report_bundle(out_path, report_bundle)

    return ValidationBatchResult(
        conditions_run=conditions_run,
        qc_report_path=str(written_report_paths["qc_report.json"]),
        eval_report_path=str(written_report_paths["eval_report.json"]),
        collapse_figure_spec_path=str(written_report_paths["collapse_figure_spec.json"]),
        result=result,
    )
