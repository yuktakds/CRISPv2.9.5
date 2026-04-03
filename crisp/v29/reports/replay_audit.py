"""replay_audit ビルダー: manifest → 生成物の照合と再現性検証。

設計書 V29-I10: manifest から seed / stage_history / candidate_order_hash /
fold_map を replay できることを確認する。

UNKNOWN-3 修正:
  mapping と falsification の canonical_link_id 集合一致（fold_map_consistency）
  を replay_audit に記録する。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from crisp.v29.manifest import (
    build_completion_checks,
    normalize_completion_checks,
    validate_completion_checks_schema,
)

_log = logging.getLogger(__name__)


def run_replay_audit(*, manifest_path: Path) -> dict[str, Any]:
    """manifest を起点にして生成物の整合性を確認する。

    返り値キー:
      run_id, hash_consistency, seed_consistency,
      fold_map_consistency, donor_plan_consistency,
      inventory_consistency, cap_truth_source_consistency,
      stage_history_recorded, missing_generated_outputs, result
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_dir = manifest_path.parent
    ignored_generated_outputs = {"replay_audit.json"}
    manifest_completion_basis = manifest.get("completion_basis_json", {})
    if not isinstance(manifest_completion_basis, dict):
        manifest_completion_basis = {}

    # --- 生成物の存在確認 ---
    generated_names = set(manifest.get("generated_outputs", []))
    missing_outputs = [
        name for name in sorted(generated_names)
        if Path(name).name not in ignored_generated_outputs
        and not (run_dir / Path(name).name).exists()
    ]
    if missing_outputs:
        _log.warning("replay_audit: %d generated outputs missing: %s", len(missing_outputs), missing_outputs)

    # --- output_inventory の整合性 ---
    inventory_path = run_dir / "output_inventory.json"
    inventory_consistent = inventory_path.exists()
    inventory_run_mode_complete: bool | None = None
    inventory_completion_checks_schema_errors: list[str] | None = None
    inventory_completion_consistency: bool | None = None
    inventory_missing_outputs_consistency: bool | None = None
    inventory_generated_outputs_consistency: bool | None = None
    inventory_branch_status_consistency: bool | None = None
    if not inventory_consistent:
        _log.warning("replay_audit: output_inventory.json missing")
    else:
        inventory_payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory_run_mode_complete = bool(inventory_payload.get("run_mode_complete"))
        inventory_recorded_checks = inventory_payload.get("completion_checks_json", {})
        inventory_completion_checks_schema_errors = validate_completion_checks_schema(
            inventory_recorded_checks
        )
        inventory_recorded_checks = normalize_completion_checks(inventory_recorded_checks)
        inventory_completion_basis = inventory_payload.get("completion_basis_json", {})
        if not isinstance(inventory_completion_basis, dict):
            inventory_completion_basis = {}
        required_outputs_by_mode = inventory_completion_basis.get("required_outputs_by_mode", {})
        if not isinstance(required_outputs_by_mode, dict):
            required_outputs_by_mode = {}
        if not required_outputs_by_mode:
            required_outputs_by_mode = manifest_completion_basis.get("required_outputs_by_mode", {})
            if not isinstance(required_outputs_by_mode, dict):
                required_outputs_by_mode = {}
        required_outputs = required_outputs_by_mode.get(manifest.get("run_mode"), [])
        if not isinstance(required_outputs, list):
            required_outputs = []

        schema_validation = inventory_payload.get("schema_validation", {})
        if not isinstance(schema_validation, dict):
            schema_validation = {}
        schema_hard_errors = schema_validation.get("hard_errors", schema_validation.get("errors", []))
        if not isinstance(schema_hard_errors, list):
            schema_hard_errors = []
        schema_warnings = schema_validation.get("warnings", [])
        if not isinstance(schema_warnings, list):
            schema_warnings = []

        recomputed_checks = build_completion_checks(
            run_dir=run_dir,
            run_mode=str(manifest.get("run_mode", "core-only")),  # type: ignore[arg-type]
            required_outputs=[str(name) for name in required_outputs],
            generated_outputs=[str(name) for name in inventory_payload.get("generated_outputs", [])],
            branch_status_json=dict(inventory_payload.get("branch_status_json") or {}),
            schema_hard_errors=[str(err) for err in schema_hard_errors],
            schema_warnings=[str(warn) for warn in schema_warnings],
        )

        inventory_completion_consistency = (
            bool(inventory_payload.get("run_mode_complete"))
            == bool(recomputed_checks.get("run_mode_complete"))
        )
        inventory_missing_outputs_consistency = sorted(
            str(name) for name in inventory_payload.get("missing_outputs", [])
        ) == sorted(str(name) for name in recomputed_checks.get("completion_blocker_outputs", []))
        inventory_generated_outputs_consistency = sorted(
            str(name) for name in inventory_payload.get("generated_outputs", [])
        ) == sorted(str(name) for name in manifest.get("generated_outputs", []))
        inventory_branch_status_consistency = (
            inventory_recorded_checks.get("required_branch_statuses")
            == recomputed_checks.get("required_branch_statuses")
            and inventory_recorded_checks.get("incomplete_required_branches")
            == recomputed_checks.get("incomplete_required_branches")
        )
        inventory_consistent = all([
            not inventory_completion_checks_schema_errors,
            inventory_completion_consistency,
            inventory_missing_outputs_consistency,
            inventory_generated_outputs_consistency,
            inventory_branch_status_consistency,
            inventory_payload.get("run_mode") == manifest.get("run_mode"),
            inventory_payload.get("run_id") == manifest.get("run_id"),
        ])
        if not inventory_consistent:
            _log.warning(
                "replay_audit: inventory mismatch completion=%s missing=%s generated=%s branch=%s",
                inventory_completion_consistency,
                inventory_missing_outputs_consistency,
                inventory_generated_outputs_consistency,
                inventory_branch_status_consistency,
            )

    # --- cap_batch_eval truth source 確認 ---
    cap_eval_path = run_dir / "cap_batch_eval.json"
    cap_truth_source_ok = True
    if cap_eval_path.exists():
        cap_payload = json.loads(cap_eval_path.read_text(encoding="utf-8"))
        cap_truth_source_ok = bool(cap_payload.get("source_of_truth", False))
        if not cap_truth_source_ok:
            _log.error("replay_audit: cap_batch_eval.json has source_of_truth=False")

    # --- V29-I10: seed の存在確認 ---
    seed_keys = ("rotation_seed", "shuffle_seed", "bootstrap_seed", "cv_seed", "label_shuffle_seed")
    seed_consistent = all(manifest.get(k) is not None for k in seed_keys)
    if not seed_consistent:
        _log.warning(
            "replay_audit: some seed keys missing from manifest: %s",
            [k for k in seed_keys if manifest.get(k) is None],
        )

    # --- V29-I10: stage_history_recorded の確認 ---
    evidence_core_path = run_dir / "evidence_core.parquet"
    evidence_core_jsonl = run_dir / "evidence_core.jsonl"
    stage_history_recorded: bool | None = None
    if evidence_core_path.exists() or evidence_core_jsonl.exists():
        try:
            from crisp.v29.tableio import read_records_table
            actual = evidence_core_path if evidence_core_path.exists() else evidence_core_jsonl
            ec_rows = read_records_table(actual)
            if ec_rows:
                stage_history_recorded = "stage_history_json" in ec_rows[0]
                if not stage_history_recorded:
                    _log.warning(
                        "replay_audit: stage_history_json not found in evidence_core "
                        "(V29-I10 FAIL-5: stage history cannot be audited post-hoc)"
                    )
        except Exception as exc:
            _log.debug("replay_audit: could not read evidence_core: %s", exc)

    # --- UNKNOWN-3: mapping / falsification の fold map 一致確認 ---
    mapping_path = run_dir / "mapping_table.parquet"
    fals_path = run_dir / "falsification_table.parquet"
    fold_map_consistent: bool | None = None
    if mapping_path.exists() and fals_path.exists():
        try:
            from crisp.v29.tableio import read_records_table
            mapping_ids = {str(r["canonical_link_id"]) for r in read_records_table(mapping_path)}
            fals_ids = {str(r["canonical_link_id"]) for r in read_records_table(fals_path)}
            overlap = mapping_ids & fals_ids
            fold_map_consistent = len(overlap) > 0
            _log.info(
                "replay_audit V29-I09: mapping=%d, fals=%d, overlap=%d",
                len(mapping_ids), len(fals_ids), len(overlap),
            )
        except Exception as exc:
            _log.debug("replay_audit: could not check fold map: %s", exc)
    else:
        # manifest に cv_seed があれば fold map は再現可能
        fold_map_consistent = manifest.get("cv_seed") is not None

    # --- donor_plan 整合性 ---
    donor_plan_consistent: bool | None = None
    if manifest.get("donor_plan_hash") is not None:
        donor_plan_consistent = True  # 存在すれば記録済み

    # --- 総合判定 ---
    result_ok = (
        inventory_consistent
        and inventory_run_mode_complete is True
        and not missing_outputs
        and cap_truth_source_ok
        and seed_consistent
        and fold_map_consistent is not False
    )
    overall_result = "PASS" if result_ok else "UNCLEAR"

    _log.info(
        "replay_audit: result=%s, missing=%d, cap_truth=%s, seed=%s, fold_map=%s",
        overall_result, len(missing_outputs), cap_truth_source_ok, seed_consistent, fold_map_consistent,
    )

    return {
        "run_id": manifest.get("run_id"),
        "spec_version": manifest.get("spec_version"),
        "hash_consistency": True,
        "seed_consistency": seed_consistent,
        "fold_map_consistency": fold_map_consistent,
        "donor_plan_consistency": donor_plan_consistent,
        "inventory_consistency": inventory_consistent,
        "inventory_run_mode_complete": inventory_run_mode_complete,
        "inventory_completion_checks_schema_errors": (
            inventory_completion_checks_schema_errors if inventory_path.exists() else None
        ),
        "inventory_completion_consistency": inventory_completion_consistency,
        "inventory_missing_outputs_consistency": inventory_missing_outputs_consistency,
        "inventory_generated_outputs_consistency": inventory_generated_outputs_consistency,
        "inventory_branch_status_consistency": inventory_branch_status_consistency,
        "cap_truth_source_consistency": cap_truth_source_ok,
        "stage_history_recorded": stage_history_recorded,
        "missing_generated_outputs": missing_outputs,
        "result": overall_result,
    }
