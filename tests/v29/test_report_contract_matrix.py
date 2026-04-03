from __future__ import annotations

import json
from pathlib import Path

from crisp.v29.contracts import IntegratedRunManifest, OutputInventory
from crisp.v29.manifest import build_completion_checks
from crisp.v29.reports import run_replay_audit
from crisp.v29.validation import run_validation_batch
from crisp.v29.writers import write_integrated_manifest, write_output_inventory


def test_report_contract_fields_align_across_validation_and_replay(tmp_path: Path) -> None:
    completion_basis = {
        "comparison_type": "cross-regime",
        "comparison_type_source": "explicit_override",
        "skip_reason_codes": ["SKIP_PATHYES_BOOTSTRAP"],
        "pathyes_mode_requested": "pat-backed",
        "pathyes_mode_resolved": "pat-backed",
        "pathyes_state_source": "pat_diagnostics_json",
        "pathyes_diagnostics_status": "loaded",
        "pathyes_diagnostics_source": "D:/runs/r1/pat.json",
        "pathyes_goal_precheck_passed": True,
        "pathyes_rule1_applicability": "PATH_EVALUABLE",
        "required_outputs_by_mode": {
            "core-only": ["output_inventory.json"],
        },
    }
    manifest = IntegratedRunManifest(
        run_id="r1",
        spec_version="v2.9.5",
        run_mode="core-only",
        resource_profile="smoke",
        target_case_id="t",
        target_config_path="cfg.yaml",
        target_config_role="benchmark",
        target_config_expected_use="Frozen regression baseline for parser, search, and reason-taxonomy changes.",
        target_config_allowed_comparisons=["same-config", "cross-regime"],
        target_config_frozen_for_regression=True,
        structure_path="s.cif",
        library_path="lib.smi",
        stageplan_path="sp.json",
        config_hash="c",
        input_hash="i",
        requirements_hash="r",
        library_hash="l",
        compound_order_hash="o",
        staging_plan_hash="sp",
        structure_file_digest="sd",
        rotation_seed=1,
        shuffle_seed=1,
        bootstrap_seed=1,
        cv_seed=1,
        label_shuffle_seed=1,
        shuffle_universe_scope="target_family_motion_class",
        shuffle_donor_pool_hash=None,
        donor_plan_hash=None,
        functional_score_dictionary_id="functional-score-dict-v1",
        theta_rule1_table_id="builtin:none",
        requested_branches=["core"],
        implemented_branches=["core"],
        generated_outputs=["output_inventory.json"],
        repo_root_source="cli",
        repo_root_resolved_path="/repo",
        completion_basis_json=completion_basis,
    )
    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode="core-only",
        required_outputs=["output_inventory.json"],
        generated_outputs=["output_inventory.json"],
        branch_status_json={"core": {"status": "COMPLETE"}},
        schema_hard_errors=[],
        schema_warnings=[],
    )
    inventory = OutputInventory(
        run_id="r1",
        run_mode="core-only",
        requested_branches=["core"],
        implemented_branches=["core"],
        generated_outputs=["output_inventory.json"],
        missing_outputs=[],
        schema_validation={"status": "PASS", "hard_errors": [], "warnings": [], "errors": []},
        warnings=[],
        run_mode_complete=True,
        branch_status_json={"core": {"status": "COMPLETE"}},
        completion_basis_json=completion_basis,
        completion_checks_json=checks,
        repo_root_source="cli",
        repo_root_resolved_path="/repo",
    )

    manifest_path = write_integrated_manifest(tmp_path / "run_manifest.json", manifest)
    write_output_inventory(tmp_path / "output_inventory.json", inventory)

    validation_result = run_validation_batch(manifest_path, "smoke", tmp_path / "reports")
    qc = json.loads(Path(validation_result.qc_report_path).read_text(encoding="utf-8"))
    eval_report = json.loads(Path(validation_result.eval_report_path).read_text(encoding="utf-8"))
    collapse = json.loads(Path(validation_result.collapse_figure_spec_path).read_text(encoding="utf-8"))
    replay = run_replay_audit(manifest_path=manifest_path)

    for payload in (qc, eval_report, collapse, replay):
        assert payload["comparison_type"] == "cross-regime"
        assert payload["comparison_type_source"] == "explicit_override"
        assert payload["skip_reason_codes"] == ["SKIP_PATHYES_BOOTSTRAP"]
        assert payload["inventory_json_errors"] == []
        assert payload["pathyes_mode_requested"] == "pat-backed"
        assert payload["pathyes_mode_resolved"] == "pat-backed"
        assert payload["pathyes_state_source"] == "pat_diagnostics_json"
        assert payload["pathyes_diagnostics_status"] == "loaded"
        assert payload["pathyes_diagnostics_source"] == "D:/runs/r1/pat.json"
        assert payload["pathyes_goal_precheck_passed"] is True
        assert payload["pathyes_rule1_applicability"] == "PATH_EVALUABLE"
