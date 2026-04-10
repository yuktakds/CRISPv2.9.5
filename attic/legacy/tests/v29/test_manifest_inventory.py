from __future__ import annotations

from pathlib import Path
import json

from crisp.v29.contracts import IntegratedRunManifest, OutputInventory
from crisp.v29.manifest import (
    COMPLETION_CHECKS_REQUIRED_KEYS,
    COMPLETION_CHECKS_SCHEMA_VERSION,
    build_completion_checks,
    build_output_inventory,
    validate_completion_checks_schema,
)
from crisp.v29.writers import write_integrated_manifest, write_output_inventory


def test_manifest_and_inventory_roundtrip(tmp_path: Path) -> None:
    manifest = IntegratedRunManifest(
        run_id="r1", spec_version="v2.9.5", run_mode="core-only", resource_profile="smoke",
        target_case_id="t", target_config_path="cfg.yaml",
        target_config_role="benchmark",
        target_config_expected_use="Frozen regression baseline for parser, search, and reason-taxonomy changes.",
        target_config_allowed_comparisons=["same-config", "cross-regime"],
        target_config_frozen_for_regression=True,
        structure_path="s.cif", library_path="lib.smi", stageplan_path="stage.json",
        config_hash="c", input_hash="i", requirements_hash="r", library_hash="l", compound_order_hash="o", staging_plan_hash="sp",
        structure_file_digest="sd", rotation_seed=1, shuffle_seed=1, bootstrap_seed=1, cv_seed=1, label_shuffle_seed=1,
        shuffle_universe_scope="target_family_motion_class", shuffle_donor_pool_hash=None, donor_plan_hash=None,
        functional_score_dictionary_id="functional-score-dict-v1", theta_rule1_table_id="builtin:none",
        requested_branches=["core"], implemented_branches=["core"], generated_outputs=["run_manifest.json"],
        repo_root_source="cli", repo_root_resolved_path="/repo", completion_basis_json={"a": 1},
    )
    (tmp_path / "run_manifest.json").write_text("{}", encoding="utf-8")
    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode="core-only",
        required_outputs=["run_manifest.json"],
        generated_outputs=["run_manifest.json"],
        branch_status_json={"core": {"status": "COMPLETE"}},
        schema_hard_errors=[],
        schema_warnings=[],
    )
    inventory = OutputInventory(
        run_id="r1", run_mode="core-only", requested_branches=["core"], implemented_branches=["core"],
        generated_outputs=["run_manifest.json"], missing_outputs=[], schema_validation={"status": "PASS", "hard_errors": [], "warnings": [], "errors": []},
        warnings=[], run_mode_complete=True, branch_status_json={"core": {"status": "COMPLETE"}},
        completion_basis_json={"a": 1}, completion_checks_json=checks,
        repo_root_source="cli", repo_root_resolved_path="/repo",
    )
    mp = write_integrated_manifest(tmp_path / "run_manifest.json", manifest)
    ip = write_output_inventory(tmp_path / "output_inventory.json", inventory)
    assert json.loads(mp.read_text(encoding="utf-8"))["run_id"] == "r1"
    assert json.loads(ip.read_text(encoding="utf-8"))["run_mode_complete"] is True


def test_build_completion_checks_rejects_empty_outputs_and_incomplete_branch(tmp_path: Path) -> None:
    (tmp_path / "core_compounds.parquet").write_text("data", encoding="utf-8")
    (tmp_path / "evidence_core.parquet").write_text("data", encoding="utf-8")
    (tmp_path / "run_manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "output_inventory.json").write_text("", encoding="utf-8")

    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode="core-only",
        required_outputs=[
            "core_compounds.parquet",
            "evidence_core.parquet",
            "run_manifest.json",
            "output_inventory.json",
        ],
        generated_outputs=[
            "core_compounds.parquet",
            "evidence_core.parquet",
            "run_manifest.json",
            "output_inventory.json",
        ],
        branch_status_json={"core": {"status": "PENDING"}},
        schema_hard_errors=[],
        schema_warnings=[],
    )

    assert checks["run_mode_complete"] is False
    assert checks["schema_version"] == COMPLETION_CHECKS_SCHEMA_VERSION
    assert set(checks) == set(COMPLETION_CHECKS_REQUIRED_KEYS)
    assert validate_completion_checks_schema(checks) == []
    assert checks["empty_output_files"] == ["output_inventory.json"]
    assert checks["required_branch_statuses"] == {"core": "PENDING"}
    assert checks["incomplete_required_branches"] == [{"branch": "core", "status": "PENDING"}]


def test_build_output_inventory_separates_schema_warnings_from_hard_errors(tmp_path: Path) -> None:
    (tmp_path / "output_inventory.json").write_text("{}", encoding="utf-8")
    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode="core-only",
        required_outputs=["output_inventory.json"],
        generated_outputs=["output_inventory.json"],
        branch_status_json={"core": {"status": "COMPLETE"}},
        schema_hard_errors=[],
        schema_warnings=["INPUT_SCHEMA_WARN:example"],
    )
    inventory = build_output_inventory(
        run_id="r1",
        run_mode="core-only",
        requested_branches=["core"],
        implemented_branches=["core"],
        generated_outputs=["output_inventory.json"],
        warnings=[],
        branch_status_json={"core": {"status": "COMPLETE"}},
        completion_basis_json={"required_outputs_by_mode": {"core-only": ["output_inventory.json"]}},
        completion_checks_json=checks,
        repo_root_source="cli",
        repo_root_resolved_path="/repo",
        schema_hard_errors=[],
        schema_warnings=["INPUT_SCHEMA_WARN:example"],
    )

    assert inventory.run_mode_complete is True
    assert inventory.schema_validation["status"] == "WARN"
    assert inventory.schema_validation["hard_errors"] == []
    assert inventory.schema_validation["warnings"] == ["INPUT_SCHEMA_WARN:example"]
