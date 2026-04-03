"""統合 run_manifest / output_inventory ビルダー。

設計書 §4A-4, 別紙 D §D5 に準拠。

修正:
  build_integrated_manifest に donor_plan 引数を追加し、
  cli.py での object.__setattr__ 回避パターンを廃止した。
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crisp.config.loader import load_target_config
from crisp.repro.hashing import (
    compute_compound_order_hash,
    compute_config_hash,
    compute_library_hash,
    compute_requirements_hash,
    compute_stageplan_hash,
    sha256_file,
)
from crisp.v29.contracts import IntegratedRunManifest, OutputInventory, RunMode
from crisp.v29.inputs import compute_joined_smiles, load_molecule_rows

_log = logging.getLogger(__name__)

_REQUIRED_BRANCHES_BY_MODE: dict[RunMode, list[str]] = {
    "core-only": ["core"],
    "core+rule1": ["core", "rule1"],
    "core+rule1+cap": ["core", "rule1", "cap"],
    "full": ["core", "rule1", "cap", "layer2"],
}


def required_branches_for_mode(run_mode: RunMode) -> list[str]:
    """run_mode ごとに completion 判定で要求する branch 名を返す。"""
    return list(_REQUIRED_BRANCHES_BY_MODE[run_mode])


def _materialized_output_candidates(required_name: str) -> list[str]:
    """required output 名に対応する実体ファイル候補を返す。"""
    candidates = [Path(required_name).name]
    required_path = Path(required_name)
    if required_path.suffix.lower() == ".parquet":
        candidates.append(required_path.with_suffix(".jsonl").name)
    return candidates


def build_completion_checks(
    *,
    run_dir: Path,
    run_mode: RunMode,
    required_outputs: list[str],
    generated_outputs: list[str],
    branch_status_json: dict[str, Any],
    schema_errors: list[str] | None = None,
) -> dict[str, Any]:
    """run_mode_complete 判定の machine-readable な根拠を構築する。"""
    required_output_names = [Path(name).name for name in required_outputs]
    generated_output_names = {Path(name).name for name in generated_outputs}
    declared_missing_outputs: list[str] = []
    materialized_output_paths: dict[str, str | None] = {}

    missing_output_files: list[str] = []
    empty_output_files: list[str] = []
    for name in required_output_names:
        candidates = _materialized_output_candidates(name)
        if not any(candidate in generated_output_names for candidate in candidates):
            declared_missing_outputs.append(name)

        existing_candidates: list[tuple[str, int]] = []
        for candidate in candidates:
            candidate_path = run_dir / candidate
            if not candidate_path.exists():
                continue
            try:
                existing_candidates.append((candidate, candidate_path.stat().st_size))
            except OSError:
                continue

        nonempty_candidate = next(
            (candidate for candidate, size in existing_candidates if size > 0),
            None,
        )
        materialized_name = (
            nonempty_candidate
            if nonempty_candidate is not None
            else (existing_candidates[0][0] if existing_candidates else None)
        )
        materialized_output_paths[name] = materialized_name
        if materialized_name is None:
            missing_output_files.append(name)
            continue
        if nonempty_candidate is None:
            if existing_candidates:
                empty_output_files.append(name)
            else:
                missing_output_files.append(name)

    required_branch_statuses: dict[str, str] = {}
    incomplete_required_branches: list[dict[str, str]] = []
    for branch in required_branches_for_mode(run_mode):
        branch_payload = branch_status_json.get(branch)
        status = (
            str(branch_payload.get("status"))
            if isinstance(branch_payload, dict) and branch_payload.get("status") is not None
            else "MISSING"
        )
        required_branch_statuses[branch] = status
        if status != "COMPLETE":
            incomplete_required_branches.append({"branch": branch, "status": status})

    normalized_schema_errors = [] if schema_errors is None else [str(err) for err in schema_errors]
    completion_blocker_outputs = sorted(
        set(declared_missing_outputs) | set(missing_output_files) | set(empty_output_files)
    )
    run_mode_complete = (
        not completion_blocker_outputs
        and not incomplete_required_branches
        and not normalized_schema_errors
    )

    return {
        "required_outputs": required_output_names,
        "materialized_output_paths": materialized_output_paths,
        "required_branches": required_branches_for_mode(run_mode),
        "declared_missing_outputs": declared_missing_outputs,
        "missing_output_files": missing_output_files,
        "empty_output_files": empty_output_files,
        "completion_blocker_outputs": completion_blocker_outputs,
        "required_branch_statuses": required_branch_statuses,
        "incomplete_required_branches": incomplete_required_branches,
        "schema_errors": normalized_schema_errors,
        "run_mode_complete": run_mode_complete,
    }


def build_integrated_manifest(
    *,
    run_id: str,
    repo_root: Path,
    repo_root_source: str,
    config_path: Path,
    library_path: Path,
    stageplan_path: Path,
    run_mode: RunMode,
    resource_profile: str,
    requested_branches: list[str],
    implemented_branches: list[str],
    generated_outputs: list[str],
    completion_basis_json: dict[str, Any],
    theta_rule1_table_id: str,
    functional_score_dictionary_id: str = "functional-score-dict-v1",
    shuffle_universe_scope: str = "target_family_motion_class",
    seeds: dict[str, int] | None = None,
    donor_plan: dict[str, Any] | None = None,
) -> IntegratedRunManifest:
    """IntegratedRunManifest を構築する。

    donor_plan 引数を受け取り shuffle_donor_pool_hash / donor_plan_hash を
    正直に設定する。旧実装は cli.py で object.__setattr__ を使っていたが廃止した。
    """
    config = load_target_config(config_path)
    structure_path = config.resolve_structure_path(repo_root)
    molecule_rows = load_molecule_rows(library_path)
    smiles_list = [str(r["smiles"]) for r in molecule_rows]
    joined_smiles = compute_joined_smiles(molecule_rows)

    _seed = seeds or {}
    default_seed = int(config.random_seed)

    import hashlib
    input_hash = "sha256:" + hashlib.sha256(joined_smiles.encode("utf-8")).hexdigest()

    shuffle_donor_pool_hash = None if donor_plan is None else donor_plan.get("shuffle_donor_pool_hash")
    donor_plan_hash = None if donor_plan is None else donor_plan.get("donor_plan_hash")

    _log.debug(
        "build_integrated_manifest: run_id=%s, run_mode=%s, donor_plan=%s",
        run_id, run_mode, "present" if donor_plan else "absent",
    )

    return IntegratedRunManifest(
        run_id=run_id,
        spec_version="v2.9.5",
        run_mode=run_mode,
        resource_profile=resource_profile,
        target_case_id=config.target_name,
        target_config_path=str(config_path),
        target_config_role=config.config_role,
        target_config_expected_use=config.expected_use,
        target_config_allowed_comparisons=config.allowed_comparison_values(),
        target_config_frozen_for_regression=config.frozen_for_regression,
        structure_path=str(structure_path),
        library_path=str(library_path),
        stageplan_path=str(stageplan_path),
        config_hash=compute_config_hash(config),
        input_hash=input_hash,
        requirements_hash=compute_requirements_hash(),
        library_hash=compute_library_hash(library_path),
        compound_order_hash=compute_compound_order_hash(smiles_list),
        staging_plan_hash=compute_stageplan_hash(stageplan_path),
        structure_file_digest=sha256_file(structure_path),
        rotation_seed=int(_seed.get("rotation_seed", default_seed)),
        shuffle_seed=int(_seed.get("shuffle_seed", default_seed)),
        bootstrap_seed=int(_seed.get("bootstrap_seed", default_seed)),
        cv_seed=int(_seed.get("cv_seed", default_seed)),
        label_shuffle_seed=int(_seed.get("label_shuffle_seed", default_seed)),
        shuffle_universe_scope=shuffle_universe_scope,
        shuffle_donor_pool_hash=shuffle_donor_pool_hash,
        donor_plan_hash=donor_plan_hash,
        functional_score_dictionary_id=functional_score_dictionary_id,
        theta_rule1_table_id=theta_rule1_table_id,
        requested_branches=requested_branches,
        implemented_branches=implemented_branches,
        generated_outputs=generated_outputs,
        repo_root_source=repo_root_source,
        repo_root_resolved_path=str(repo_root),
        completion_basis_json=completion_basis_json,
    )


def build_output_inventory(
    *,
    run_id: str,
    run_mode: RunMode,
    requested_branches: list[str],
    implemented_branches: list[str],
    generated_outputs: list[str],
    warnings: list[str],
    branch_status_json: dict[str, Any],
    completion_basis_json: dict[str, Any],
    completion_checks_json: dict[str, Any],
    repo_root_source: str,
    repo_root_resolved_path: str,
    schema_errors: list[str] | None = None,
) -> OutputInventory:
    """OutputInventory を構築する。"""
    schema_validation: dict[str, Any] = {
        "status": "PASS" if not schema_errors else "FAIL",
        "errors": [] if schema_errors is None else list(schema_errors),
        "checked_at_utc": datetime.now(UTC).isoformat(),
    }
    return OutputInventory(
        run_id=run_id,
        run_mode=run_mode,
        requested_branches=requested_branches,
        implemented_branches=implemented_branches,
        generated_outputs=generated_outputs,
        missing_outputs=list(completion_checks_json.get("completion_blocker_outputs", [])),
        schema_validation=schema_validation,
        warnings=warnings,
        run_mode_complete=bool(completion_checks_json.get("run_mode_complete", False)) and not schema_errors,
        branch_status_json=branch_status_json,
        completion_basis_json=completion_basis_json,
        completion_checks_json=completion_checks_json,
        repo_root_source=repo_root_source,
        repo_root_resolved_path=repo_root_resolved_path,
    )
