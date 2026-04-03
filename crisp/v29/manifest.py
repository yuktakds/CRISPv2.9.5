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
    missing_outputs: list[str],
    warnings: list[str],
    branch_status_json: dict[str, Any],
    completion_basis_json: dict[str, Any],
    repo_root_source: str,
    repo_root_resolved_path: str,
    run_mode_complete: bool,
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
        missing_outputs=missing_outputs,
        schema_validation=schema_validation,
        warnings=warnings,
        run_mode_complete=run_mode_complete and not schema_errors,
        branch_status_json=branch_status_json,
        completion_basis_json=completion_basis_json,
        repo_root_source=repo_root_source,
        repo_root_resolved_path=repo_root_resolved_path,
    )
