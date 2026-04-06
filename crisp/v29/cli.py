"""統合 CLI: v2.9.5 multi-branch tuple 出力の実行エントリーポイント。

設計書 §4A, §5.2, §8 に準拠。

修正点:
  - locals().get('donor_plan') → 明示的なスコープ変数で管理
  - object.__setattr__(frozen_dataclass, ...) → manifest 引数で正直に渡す
  - print → logging
  - branch_status / completion_basis を関数に分離
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from crisp.config.loader import load_target_config
from crisp.v29.cap import (
    build_falsification_table,
    build_mapping_table,
    run_cap_batch_scv,
    run_layer0,
    run_layer1,
    run_layer2,
)
from crisp.v29.core_bridge import run_core_bridge
from crisp.v29.contracts import RunMode
from crisp.v29.inputs import load_molecule_rows, normalize_run_mode
from crisp.v29.manifest import (
    build_completion_checks,
    build_integrated_manifest,
    build_output_inventory,
    required_branches_for_mode,
)
from crisp.v29.planning import build_donor_plan, build_pair_plan
from crisp.v29.repo import resolve_repo_root
from crisp.v29.reports import (
    build_collapse_figure_spec,
    build_eval_report,
    build_qc_report,
    run_replay_audit,
)
from crisp.v29.rule1 import run_rule1_assessments
from crisp.v29.rule1_theta import (
    ThetaRule1RuntimeError,
    load_theta_rule1_runtime_table,
    trace_theta_rule1_resolution,
)
from crisp.v29.tableio import read_records_table, write_records_table
from crisp.v29.validators import (
    validate_cap_artifact_invariants,
    validate_molecules_input,
    validate_pair_evidence_no_verdict,
    validate_theta_rule1_runtime_table,
)
from crisp.v29.writers import (
    write_cap_batch_eval,
    write_collapse_figure_spec,
    write_eval_report,
    write_integrated_manifest,
    write_legacy_phase1_evidence_alias,
    write_output_inventory,
    write_qc_report,
    write_replay_audit,
    write_theta_rule1_resolution,
)

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _load_integrated_config(path: Path | None) -> dict[str, Any]:
    """統合 config YAML を読み込む。path が None の場合は空 dict を返す。"""
    if path is None:
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise TypeError(f"integrated config must be a mapping, got {type(payload).__name__}")
    return payload


def _resource_profile_params(profile: str) -> tuple[int, int, int]:
    """profile 名から (n_rotations, n_splits, n_boot) を返す（別紙 E §E6）。"""
    if profile == "release":
        return 1024, 5, 1000
    if profile == "pilot":
        return 256, 5, 200
    # smoke またはその他
    return 64, 3, 50


def _branch_status(status: str, **extra: Any) -> dict[str, Any]:
    """branch_status_json の 1 エントリを生成する。"""
    return {
        "requested": True,
        "implemented": True,
        "executable": True,
        "executed": status == "COMPLETE",
        "status": status,
        **extra,
    }


def _required_outputs_for_mode(run_mode: str) -> list[str]:
    """run_mode ごとの必須出力ファイル名リストを返す。"""
    required = ["core_compounds.parquet", "evidence_core.parquet",
                "run_manifest.json", "output_inventory.json"]
    if run_mode in {"core+rule1", "core+rule1+cap", "full"}:
        required.append("rule1_assessments.parquet")
    if run_mode in {"core+rule1+cap", "full"}:
        required.extend([
            "pair_features.parquet",
            "evidence_pairs.parquet",
            "cap_batch_eval.json",
            "qc_report.json",
            "eval_report.json",
            "collapse_figure_spec.json",
        ])
    if run_mode == "full":
        required.extend([
            "mapping_table.parquet", "falsification_table.parquet",
        ])
    return required


def _record_materialization_event(
    events: list[dict[str, Any]],
    fallback_reason_codes: list[str],
    *,
    logical_output: str,
    table_result: Any,
) -> None:
    event = table_result.to_materialization_event(logical_output=logical_output)
    events.append(event)
    if event.get("fallback_used") and event.get("fallback_reason_code"):
        fallback_reason_codes.append(str(event["fallback_reason_code"]))


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def run_integrated_v29(
    *,
    repo_root: str | Path | None,
    config_path: Path,
    library_path: Path,
    stageplan_path: Path,
    out_dir: Path,
    integrated_config_path: Path | None = None,
    run_mode: str = "core-only",
    caps_path: Path | None = None,
    assays_path: Path | None = None,
) -> dict[str, Any]:
    """v2.9.5 統合実行エントリーポイント。

    返り値:
        run_id, run_mode, generated_outputs, missing_outputs, run_mode_complete
        を含む dict（単一 global verdict は返さない: V29-I12）。
    """
    run_mode = normalize_run_mode(run_mode)
    resolution = resolve_repo_root(explicit_repo_root=repo_root, start=out_dir.parent)
    resolved_repo_root = resolution.repo_root
    integrated = _load_integrated_config(integrated_config_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = out_dir.name
    resource_profile = str(integrated.get("resource_profile", "smoke"))

    _log.info(
        "run_integrated_v29: run_id=%s, mode=%s, profile=%s, repo_root_source=%s",
        run_id, run_mode, resource_profile, resolution.source,
    )

    requested_branches: list[str] = ["core"]
    implemented_branches: list[str] = ["core"]
    generated_outputs: list[str] = []
    warnings: list[str] = []
    skip_reason_codes: list[str] = []
    output_materialization_events: list[dict[str, Any]] = []
    output_fallback_reason_codes: list[str] = []
    pathyes_mode_requested: str | None = None
    pathyes_force_false_requested = False
    pathyes_mode_resolved: str | None = None
    pathyes_state_source: str | None = None
    pathyes_diagnostics_status: str | None = None
    pathyes_diagnostics_error_code: str | None = None
    pathyes_diagnostics_source: str | None = None
    pathyes_goal_precheck_passed: bool | None = None
    pathyes_rule1_applicability: str | None = None
    pathyes_skip_code: str | None = None
    comparison_type = None
    comparison_type_source = None

    # --- 入力検証 ---
    schema_hard_errors, schema_warnings = validate_molecules_input(library_path)
    warnings.extend(schema_warnings)

    # --- Core branch ---
    core_result = run_core_bridge(
        repo_root=resolved_repo_root,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        out_dir=out_dir,
        proposal_mode=str(integrated.get("proposal_mode", "legacy_passthrough")),
    )
    generated_outputs.extend([
        Path(core_result.core_rows_path).name,
        Path(core_result.evidence_core_path).name,
        Path(core_result.diagnostics_path).name,
    ])
    output_materialization_events.extend(core_result.materialization_events)
    for event in core_result.materialization_events:
        if event.get("fallback_used") and event.get("fallback_reason_code"):
            output_fallback_reason_codes.append(str(event["fallback_reason_code"]))

    alias_payload = {
        "run_id": run_id,
        "alias_type": "legacy_phase1_evidence_alias",
        "source_core_rows_path": core_result.core_rows_path,
        "source_evidence_core_path": core_result.evidence_core_path,
        "legacy_core_final_verdict_field": "legacy_core_final_verdict",
    }
    write_legacy_phase1_evidence_alias(out_dir / "legacy_phase1_evidence_alias.json", alias_payload)
    generated_outputs.append("legacy_phase1_evidence_alias.json")

    branch_status_json: dict[str, Any] = {
        "core": _branch_status("COMPLETE", mode="frozen-service"),
    }

    config = load_target_config(config_path)
    requested_pathyes_mode = (
        str(integrated.get("pathyes_mode", "bootstrap"))
        if run_mode in {"core+rule1", "core+rule1+cap", "full"}
        else "bootstrap"
    )
    require_managed_theta_table = run_mode in {"core+rule1", "core+rule1+cap", "full"} and (
        requested_pathyes_mode != "bootstrap"
    )
    theta_runtime_table = load_theta_rule1_runtime_table(
        integrated.get("theta_rule1_table"),
        require_managed=require_managed_theta_table,
    )
    theta_resolution_trace = trace_theta_rule1_resolution(theta_runtime_table, config=config)
    theta_errors, theta_warnings, theta_diagnostics = validate_theta_rule1_runtime_table(
        theta_runtime_table,
        config=config,
        config_path=config_path,
        resolution_trace=theta_resolution_trace,
    )
    warnings.extend(theta_warnings)
    if theta_errors:
        first_error = str(theta_errors[0])
        raise ThetaRule1RuntimeError(
            code=first_error.split(":", 1)[0],
            message=first_error,
        )
    if run_mode in {"core+rule1", "core+rule1+cap", "full"} or integrated.get("theta_rule1_table") is not None:
        write_theta_rule1_resolution(
            out_dir / "theta_rule1_resolution.json",
            {
                "run_id": run_id,
                **theta_diagnostics,
            },
        )
        generated_outputs.append("theta_rule1_resolution.json")
    requested_comparison_type = integrated.get("comparison_type")
    if requested_comparison_type is not None:
        comparison_type = config.assert_allows_comparison(
            requested_comparison_type,
            context="run-integrated-v29 comparison_type override",
            config_path=config_path,
        ).value
        comparison_type_source = "explicit_override"
    else:
        comparison_type = config.default_comparison_type().value
        comparison_type_source = "config_role_default"
    molecule_rows = load_molecule_rows(library_path)
    entries: list[tuple[str, str]] = [
        (str(r["smiles"]), str(r["molecule_id"])) for r in molecule_rows
    ]

    # --- Rule1 branch ---
    if run_mode in {"core+rule1", "core+rule1+cap", "full"}:
        requested_branches.append("rule1")
        implemented_branches.append("rule1")

        pathyes_mode = str(integrated.get("pathyes_mode", "bootstrap"))
        pat_diag_path = integrated.get("pat_diagnostics_path")
        force_pathyes_false = bool(integrated.get("pathyes_force_false", False))
        pathyes_mode_requested = pathyes_mode
        pathyes_force_false_requested = force_pathyes_false
        theta_rule1 = float(theta_resolution_trace["theta_rule1"])

        rule1_table, rule1_diag = run_rule1_assessments(
            entries=entries,
            config=config,
            out_path=out_dir / "rule1_assessments.parquet",
            theta_rule1=theta_rule1,
            pathyes_mode=pathyes_mode,
            pat_diagnostics_path=pat_diag_path,
            pathyes_force_false=force_pathyes_false,
            run_id=run_id,
        )
        rule1_diag["theta_rule1_resolution"] = {
            "resolved_lookup_key": theta_resolution_trace.get("resolved_lookup_key"),
            "resolution_status": theta_resolution_trace.get("resolution_status"),
            "theta_rule1": theta_rule1,
            "validator_errors": theta_diagnostics.get("validator_errors", []),
            "validator_warnings": theta_diagnostics.get("validator_warnings", []),
        }
        (out_dir / "rule1_branch_diagnostics.json").write_text(
            json.dumps(rule1_diag, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        generated_outputs.extend([Path(rule1_table.path).name, "rule1_branch_diagnostics.json"])
        _record_materialization_event(
            output_materialization_events,
            output_fallback_reason_codes,
            logical_output="rule1_assessments.parquet",
            table_result=rule1_table,
        )
        branch_status_json["rule1"] = _branch_status(
            "COMPLETE",
            mode=rule1_diag.get("pathyes_mode_resolved", pathyes_mode),
            rule1_applicability=rule1_diag["rule1_applicability"],
            goal_precheck_passed=rule1_diag.get("goal_precheck_passed"),
            pathyes_diagnostics_status=rule1_diag.get("pathyes_diagnostics_status"),
            pathyes_diagnostics_error_code=rule1_diag.get("pathyes_diagnostics_error_code"),
            pathyes_skip_code=rule1_diag.get("pathyes_skip_code"),
        )
        pathyes_mode_resolved = (
            None if rule1_diag.get("pathyes_mode_resolved") is None
            else str(rule1_diag.get("pathyes_mode_resolved"))
        )
        pathyes_state_source = (
            None if rule1_diag.get("pathyes_state_source") is None
            else str(rule1_diag.get("pathyes_state_source"))
        )
        pathyes_diagnostics_status = (
            None if rule1_diag.get("pathyes_diagnostics_status") is None
            else str(rule1_diag.get("pathyes_diagnostics_status"))
        )
        pathyes_diagnostics_error_code = (
            None if rule1_diag.get("pathyes_diagnostics_error_code") is None
            else str(rule1_diag.get("pathyes_diagnostics_error_code"))
        )
        pathyes_diagnostics_source = (
            None if rule1_diag.get("pathyes_diagnostics_source") is None
            else str(rule1_diag.get("pathyes_diagnostics_source"))
        )
        goal_precheck_value = rule1_diag.get("pathyes_goal_precheck_passed")
        pathyes_goal_precheck_passed = (
            goal_precheck_value if isinstance(goal_precheck_value, bool) else None
        )
        pathyes_rule1_applicability = str(rule1_diag["rule1_applicability"])
        pathyes_skip_code = (
            None if rule1_diag.get("pathyes_skip_code") is None
            else str(rule1_diag.get("pathyes_skip_code"))
        )
        if rule1_diag.get("skip_code"):
            skip_code = str(rule1_diag["skip_code"])
            warnings.append(skip_code)
            skip_reason_codes.append(skip_code)

    # --- Cap branch ---
    # donor_plan を明示的なスコープ変数として管理（旧実装の locals().get() バグを修正）
    donor_plan: dict[str, Any] | None = None
    layer2_result = None
    mapping_validation_source: str | Path | list[dict[str, Any]] | None = None
    falsification_validation_source: str | Path | list[dict[str, Any]] | None = None

    if run_mode in {"core+rule1+cap", "full"}:
        requested_branches.append("cap")
        implemented_branches.append("cap")

        if caps_path is None:
            raise ValueError("caps_path is required when Cap branch is requested")

        caps_rows = read_records_table(caps_path)
        n_rotations, n_splits, n_boot = _resource_profile_params(resource_profile)
        shuffle_seed = int(integrated.get("seeds", {}).get("shuffle_seed", config.random_seed))

        pair_plan_rows = build_pair_plan(
            entries=entries,
            target_id=config.target_name,
            caps_rows=caps_rows,
            shuffle_seed=shuffle_seed,
        )
        donor_plan = build_donor_plan(
            pair_plan_rows,
            str(integrated.get("shuffle_universe_scope", "target_family_motion_class")),
            shuffle_seed,
        )
        pair_plan_tbl = write_records_table(out_dir / "pair_plan.parquet", pair_plan_rows)
        generated_outputs.append(Path(pair_plan_tbl.path).name)
        _record_materialization_event(
            output_materialization_events,
            output_fallback_reason_codes,
            logical_output="pair_plan.parquet",
            table_result=pair_plan_tbl,
        )

        layer0_rows = run_layer0(pair_plan_rows, caps_rows, n_rotations=n_rotations)
        pair_features_rows = run_layer1(layer0_rows)

        # pair_features.parquet: Layer0/1 の全特徴量（ablation に使用）
        pair_features_tbl = write_records_table(
            out_dir / "pair_features.parquet",
            [{**r, "run_id": run_id} for r in pair_features_rows],
        )

        # evidence_pairs.parquet: pair-level provenance（verdict 禁止, D4 準拠）
        evidence_pair_columns = {
            "run_id", "pair_id", "molecule_id", "target_id", "cap_id", "native_cap_id",
            "pairing_role", "shuffle_id", "rotation_seed", "shuffle_seed",
            "rotation_index_count", "config_hash",
        }
        evidence_pairs_rows = [
            {"run_id": run_id, **{k: v for k, v in row.items() if k in evidence_pair_columns}}
            for row in pair_features_rows
        ]
        evidence_pairs_tbl = write_records_table(
            out_dir / "evidence_pairs.parquet", evidence_pairs_rows
        )
        ev_errors, _ = validate_pair_evidence_no_verdict(evidence_pairs_tbl.path)
        schema_hard_errors.extend(ev_errors)

        generated_outputs.extend([
            Path(pair_features_tbl.path).name,
            Path(evidence_pairs_tbl.path).name,
        ])
        _record_materialization_event(
            output_materialization_events,
            output_fallback_reason_codes,
            logical_output="pair_features.parquet",
            table_result=pair_features_tbl,
        )
        _record_materialization_event(
            output_materialization_events,
            output_fallback_reason_codes,
            logical_output="evidence_pairs.parquet",
            table_result=evidence_pairs_tbl,
        )
        branch_status_json["cap"] = _branch_status("COMPLETE", rows=len(pair_features_rows))

        # --- full mode: Layer2 + mapping/falsification ---
        if run_mode == "full":
            requested_branches.append("layer2")
            implemented_branches.append("layer2")

            if assays_path is None:
                raise ValueError("assays_path is required for run_mode=full")

            assays_rows = read_records_table(assays_path)
            mapping_rows = build_mapping_table(pair_features_rows, assays_rows)
            fals_rows = build_falsification_table(pair_features_rows, assays_rows, donor_plan)

            mapping_tbl = write_records_table(out_dir / "mapping_table.parquet", mapping_rows)
            fals_tbl = write_records_table(out_dir / "falsification_table.parquet", fals_rows)
            mapping_validation_source = mapping_tbl.path
            falsification_validation_source = fals_tbl.path
            generated_outputs.extend([
                Path(mapping_tbl.path).name, Path(fals_tbl.path).name
            ])
            _record_materialization_event(
                output_materialization_events,
                output_fallback_reason_codes,
                logical_output="mapping_table.parquet",
                table_result=mapping_tbl,
            )
            _record_materialization_event(
                output_materialization_events,
                output_fallback_reason_codes,
                logical_output="falsification_table.parquet",
                table_result=fals_tbl,
            )

            layer2_result = run_layer2(
                mapping_rows, fals_rows,
                cv_seed=int(integrated.get("seeds", {}).get("cv_seed", config.random_seed)),
                bootstrap_seed=int(integrated.get("seeds", {}).get("bootstrap_seed", config.random_seed)),
                n_splits=n_splits,
                n_boot=n_boot,
            )
            branch_status_json["layer2"] = _branch_status(
                "COMPLETE", layer2_status=layer2_result.status
            )

        cap_eval = run_cap_batch_scv(
            run_id=run_id,
            pair_features_rows=pair_features_rows,
            layer2_result=layer2_result,
        )
        cap_eval_path = write_cap_batch_eval(out_dir / "cap_batch_eval.json", cap_eval)
        generated_outputs.append("cap_batch_eval.json")
        cap_invariant_errors, cap_invariant_warnings = validate_cap_artifact_invariants(
            mapping_source=mapping_validation_source,
            falsification_source=falsification_validation_source,
            cap_batch_eval_source=cap_eval.to_dict(),
        )
        schema_hard_errors.extend(cap_invariant_errors)
        warnings.extend(cap_invariant_warnings)

        eval_report = build_eval_report(
            run_id=run_id,
            cap_batch_eval_path=str(cap_eval_path),
            layer2_result=layer2_result,
            comparison_type=comparison_type,
            comparison_type_source=comparison_type_source,
            skip_reason_codes=sorted(set(skip_reason_codes)),
            inventory_json_errors=[],
            notes=warnings,
            pathyes_mode_requested=pathyes_mode_requested,
            pathyes_mode_resolved=pathyes_mode_resolved,
            pathyes_state_source=pathyes_state_source,
            pathyes_diagnostics_status=pathyes_diagnostics_status,
            pathyes_diagnostics_error_code=pathyes_diagnostics_error_code,
            pathyes_diagnostics_source=pathyes_diagnostics_source,
            pathyes_goal_precheck_passed=pathyes_goal_precheck_passed,
            pathyes_rule1_applicability=pathyes_rule1_applicability,
            pathyes_skip_code=pathyes_skip_code,
        )
        write_eval_report(out_dir / "eval_report.json", eval_report)
        generated_outputs.append("eval_report.json")

        qc_report = build_qc_report(
            run_id=run_id,
            conditions_run=["native", "shuffle_joint"],
            excluded_rows_count=0,
            warnings=warnings,
            result="PASS",
            comparison_type=comparison_type,
            comparison_type_source=comparison_type_source,
            skip_reason_codes=sorted(set(skip_reason_codes)),
            inventory_json_errors=[],
            pathyes_mode_requested=pathyes_mode_requested,
            pathyes_mode_resolved=pathyes_mode_resolved,
            pathyes_state_source=pathyes_state_source,
            pathyes_diagnostics_status=pathyes_diagnostics_status,
            pathyes_diagnostics_error_code=pathyes_diagnostics_error_code,
            pathyes_diagnostics_source=pathyes_diagnostics_source,
            pathyes_goal_precheck_passed=pathyes_goal_precheck_passed,
            pathyes_rule1_applicability=pathyes_rule1_applicability,
            pathyes_skip_code=pathyes_skip_code,
            extra={"pair_row_count": len(pair_features_rows)},
        )
        write_qc_report(out_dir / "qc_report.json", qc_report)
        generated_outputs.append("qc_report.json")

        collapse_spec = build_collapse_figure_spec(
            run_id=run_id,
            resource_profile=resource_profile,
            conditions=["native", "shuffle_joint"],
            comparison_type=comparison_type,
            comparison_type_source=comparison_type_source,
            skip_reason_codes=sorted(set(skip_reason_codes)),
            inventory_json_errors=[],
            pathyes_mode_requested=pathyes_mode_requested,
            pathyes_mode_resolved=pathyes_mode_resolved,
            pathyes_state_source=pathyes_state_source,
            pathyes_diagnostics_status=pathyes_diagnostics_status,
            pathyes_diagnostics_error_code=pathyes_diagnostics_error_code,
            pathyes_diagnostics_source=pathyes_diagnostics_source,
            pathyes_goal_precheck_passed=pathyes_goal_precheck_passed,
            pathyes_rule1_applicability=pathyes_rule1_applicability,
            pathyes_skip_code=pathyes_skip_code,
            cap_metrics={
                "native_pair_count": sum(
                    1 for r in pair_features_rows if r.get("pairing_role") == "native"
                ),
                "fals_pair_count": sum(
                    1 for r in pair_features_rows if r.get("pairing_role") == "matched_falsification"
                ),
                "cap_batch_eval_path": str(cap_eval_path),
            },
        )
        write_collapse_figure_spec(out_dir / "collapse_figure_spec.json", collapse_spec)
        generated_outputs.append("collapse_figure_spec.json")

    # --- manifest / inventory ---
    completion_basis_json = {
        "phase0_core_only": run_mode == "core-only",
        "run_mode": run_mode,
        "comparison_type": comparison_type,
        "comparison_type_source": comparison_type_source,
        "pathyes_mode_requested": pathyes_mode_requested,
        "pathyes_force_false_requested": pathyes_force_false_requested,
        "pathyes_mode_resolved": pathyes_mode_resolved,
        "pathyes_state_source": pathyes_state_source,
        "pathyes_diagnostics_status": pathyes_diagnostics_status,
        "pathyes_diagnostics_error_code": pathyes_diagnostics_error_code,
        "pathyes_diagnostics_source": pathyes_diagnostics_source,
        "pathyes_goal_precheck_passed": pathyes_goal_precheck_passed,
        "pathyes_rule1_applicability": pathyes_rule1_applicability,
        "pathyes_skip_code": pathyes_skip_code,
        "skip_reason_codes": sorted(set(skip_reason_codes)),
        "output_fallback_reason_codes": sorted(set(output_fallback_reason_codes)),
        "output_materialization_events": output_materialization_events,
        "required_outputs_by_mode": {
            m: _required_outputs_for_mode(m)
            for m in ("core-only", "core+rule1", "core+rule1+cap", "full")
        },
        "required_branches_by_mode": {
            m: required_branches_for_mode(m)
            for m in ("core-only", "core+rule1", "core+rule1+cap", "full")
        },
    }
    all_manifest_outputs = generated_outputs + [
        "run_manifest.json", "output_inventory.json", "replay_audit.json"
    ]
    required_for_mode = _required_outputs_for_mode(run_mode)

    # donor_plan のハッシュを manifest に正直に渡す（旧実装の object.__setattr__ バグを修正）
    manifest = build_integrated_manifest(
        run_id=run_id,
        repo_root=resolved_repo_root,
        repo_root_source=resolution.source,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        run_mode=run_mode,  # type: ignore[arg-type]
        resource_profile=resource_profile,
        requested_branches=requested_branches,
        implemented_branches=implemented_branches,
        generated_outputs=all_manifest_outputs,
        completion_basis_json=completion_basis_json,
        theta_rule1_table_id=theta_runtime_table.table_id,
        theta_rule1_table_version=theta_runtime_table.table_version,
        theta_rule1_table_digest=theta_runtime_table.table_digest,
        theta_rule1_table_source=theta_runtime_table.table_source,
        theta_rule1_runtime_contract=theta_runtime_table.runtime_contract,
        functional_score_dictionary_id=str(
            integrated.get("functional_score_dictionary_id", "functional-score-dict-v1")
        ),
        shuffle_universe_scope=str(
            integrated.get("shuffle_universe_scope", "target_family_motion_class")
        ),
        seeds={k: int(v) for k, v in dict(integrated.get("seeds", {})).items()},
        donor_plan=donor_plan,  # None の場合は manifest 内で None として記録される
    )
    write_integrated_manifest(out_dir / "run_manifest.json", manifest)

    provisional_completion_checks = build_completion_checks(
        run_dir=out_dir,
        run_mode=run_mode,  # type: ignore[arg-type]
        required_outputs=required_for_mode,
        generated_outputs=all_manifest_outputs,
        branch_status_json=branch_status_json,
        schema_hard_errors=schema_hard_errors,
        schema_warnings=schema_warnings,
    )
    provisional_inventory = build_output_inventory(
        run_id=run_id,
        run_mode=run_mode,  # type: ignore[arg-type]
        requested_branches=requested_branches,
        implemented_branches=implemented_branches,
        generated_outputs=all_manifest_outputs,
        warnings=warnings,
        branch_status_json=branch_status_json,
        completion_basis_json=completion_basis_json,
        completion_checks_json=provisional_completion_checks,
        repo_root_source=resolution.source,
        repo_root_resolved_path=str(resolved_repo_root),
        schema_hard_errors=schema_hard_errors,
        schema_warnings=schema_warnings,
    )
    write_output_inventory(out_dir / "output_inventory.json", provisional_inventory)

    final_completion_checks = build_completion_checks(
        run_dir=out_dir,
        run_mode=run_mode,  # type: ignore[arg-type]
        required_outputs=required_for_mode,
        generated_outputs=all_manifest_outputs,
        branch_status_json=branch_status_json,
        schema_hard_errors=schema_hard_errors,
        schema_warnings=schema_warnings,
    )
    inventory = build_output_inventory(
        run_id=run_id,
        run_mode=run_mode,  # type: ignore[arg-type]
        requested_branches=requested_branches,
        implemented_branches=implemented_branches,
        generated_outputs=all_manifest_outputs,
        warnings=warnings,
        branch_status_json=branch_status_json,
        completion_basis_json=completion_basis_json,
        completion_checks_json=final_completion_checks,
        repo_root_source=resolution.source,
        repo_root_resolved_path=str(resolved_repo_root),
        schema_hard_errors=schema_hard_errors,
        schema_warnings=schema_warnings,
    )
    write_output_inventory(out_dir / "output_inventory.json", inventory)
    replay_payload = run_replay_audit(manifest_path=out_dir / "run_manifest.json")
    write_replay_audit(out_dir / "replay_audit.json", replay_payload)

    _log.info(
        "run_integrated_v29 complete: run_id=%s, complete=%s, missing=%s",
        run_id, inventory.run_mode_complete, inventory.missing_outputs,
    )

    return {
        "run_id": run_id,
        "run_mode": run_mode,
        "repo_root": str(resolved_repo_root),
        "repo_root_source": resolution.source,
        "out_dir": str(out_dir),
        "generated_outputs": inventory.generated_outputs,
        "missing_outputs": inventory.missing_outputs,
        "run_mode_complete": inventory.run_mode_complete,
    }


def run_replay_audit_v29(*, manifest_path: Path) -> dict[str, Any]:
    """replay_audit を単独で実行するヘルパー。"""
    payload = run_replay_audit(manifest_path=manifest_path)
    write_replay_audit(manifest_path.parent / "replay_audit.json", payload)
    return payload
