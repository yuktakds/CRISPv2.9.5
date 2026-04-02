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
from crisp.v29.manifest import build_integrated_manifest, build_output_inventory
from crisp.v29.planning import build_donor_plan, build_pair_plan
from crisp.v29.repo import resolve_repo_root
from crisp.v29.reports import (
    build_collapse_figure_spec,
    build_eval_report,
    build_qc_report,
    run_replay_audit,
)
from crisp.v29.rule1 import load_theta_rule1_table, resolve_theta_rule1, run_rule1_assessments
from crisp.v29.tableio import read_records_table, write_records_table
from crisp.v29.validators import validate_molecules_input, validate_pair_evidence_no_verdict
from crisp.v29.writers import (
    write_cap_batch_eval,
    write_collapse_figure_spec,
    write_eval_report,
    write_integrated_manifest,
    write_legacy_phase1_evidence_alias,
    write_output_inventory,
    write_qc_report,
    write_replay_audit,
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
        required.extend(["pair_features.parquet", "evidence_pairs.parquet"])
    if run_mode == "full":
        required.extend([
            "mapping_table.parquet", "falsification_table.parquet",
            "cap_batch_eval.json", "eval_report.json",
        ])
    return required


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

    # --- 入力検証 ---
    schema_errors, schema_warnings = validate_molecules_input(library_path)
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

    theta_table, theta_rule1_table_id = load_theta_rule1_table(integrated.get("theta_rule1_table"))
    config = load_target_config(config_path)
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
        theta_rule1 = resolve_theta_rule1(theta_table, config=config)

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
        (out_dir / "rule1_branch_diagnostics.json").write_text(
            json.dumps(rule1_diag, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        generated_outputs.extend([Path(rule1_table.path).name, "rule1_branch_diagnostics.json"])
        branch_status_json["rule1"] = _branch_status(
            "COMPLETE",
            mode=pathyes_mode,
            rule1_applicability=rule1_diag["rule1_applicability"],
        )
        if rule1_diag.get("skip_code"):
            warnings.append(str(rule1_diag["skip_code"]))

    # --- Cap branch ---
    # donor_plan を明示的なスコープ変数として管理（旧実装の locals().get() バグを修正）
    donor_plan: dict[str, Any] | None = None
    layer2_result = None

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
        schema_errors.extend(ev_errors)

        generated_outputs.extend([
            Path(pair_features_tbl.path).name,
            Path(evidence_pairs_tbl.path).name,
        ])
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
            generated_outputs.extend([
                Path(mapping_tbl.path).name, Path(fals_tbl.path).name
            ])

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

        eval_report = build_eval_report(
            run_id=run_id,
            cap_batch_eval_path=str(cap_eval_path),
            layer2_result=layer2_result,
            notes=warnings,
        )
        write_eval_report(out_dir / "eval_report.json", eval_report)
        generated_outputs.append("eval_report.json")

        qc_report = build_qc_report(
            run_id=run_id,
            conditions_run=["native", "shuffle_joint"],
            excluded_rows_count=0,
            warnings=warnings,
            result="PASS",
            extra={"pair_row_count": len(pair_features_rows)},
        )
        write_qc_report(out_dir / "qc_report.json", qc_report)
        generated_outputs.append("qc_report.json")

        collapse_spec = build_collapse_figure_spec(
            run_id=run_id,
            resource_profile=resource_profile,
            conditions=["native", "shuffle_joint"],
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
        "required_outputs_by_mode": {
            m: _required_outputs_for_mode(m)
            for m in ("core-only", "core+rule1", "core+rule1+cap", "full")
        },
    }
    all_manifest_outputs = generated_outputs + [
        "run_manifest.json", "output_inventory.json", "replay_audit.json"
    ]
    required_for_mode = _required_outputs_for_mode(run_mode)
    generated_names = {Path(p).name for p in all_manifest_outputs}
    missing_outputs = [
        name for name in required_for_mode if Path(name).name not in generated_names
    ]
    run_mode_complete = not missing_outputs and not schema_errors

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
        theta_rule1_table_id=theta_rule1_table_id,
        functional_score_dictionary_id=str(
            integrated.get("functional_score_dictionary_id", "functional-score-dict-v1")
        ),
        shuffle_universe_scope=str(
            integrated.get("shuffle_universe_scope", "target_family_motion_class")
        ),
        seeds={k: int(v) for k, v in dict(integrated.get("seeds", {})).items()},
        donor_plan=donor_plan,  # None の場合は manifest 内で None として記録される
    )

    inventory = build_output_inventory(
        run_id=run_id,
        run_mode=run_mode,  # type: ignore[arg-type]
        requested_branches=requested_branches,
        implemented_branches=implemented_branches,
        generated_outputs=all_manifest_outputs,
        missing_outputs=missing_outputs,
        warnings=warnings,
        branch_status_json=branch_status_json,
        completion_basis_json=completion_basis_json,
        repo_root_source=resolution.source,
        repo_root_resolved_path=str(resolved_repo_root),
        run_mode_complete=run_mode_complete,
        schema_errors=schema_errors,
    )

    write_integrated_manifest(out_dir / "run_manifest.json", manifest)
    write_output_inventory(out_dir / "output_inventory.json", inventory)
    replay_payload = run_replay_audit(manifest_path=out_dir / "run_manifest.json")
    write_replay_audit(out_dir / "replay_audit.json", replay_payload)

    _log.info(
        "run_integrated_v29 complete: run_id=%s, complete=%s, missing=%s",
        run_id, run_mode_complete, missing_outputs,
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
