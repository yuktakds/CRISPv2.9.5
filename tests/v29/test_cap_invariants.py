from __future__ import annotations

import json
from pathlib import Path

from crisp.v29.cli import run_integrated_v29
from crisp.v29.contracts import CapBatchEval
from crisp.v29.tableio import write_records_table
from crisp.v29.validators import (
    validate_cap_artifact_invariants,
    validate_cap_batch_eval_invariants,
    validate_falsification_table_invariants,
    validate_mapping_table_invariants,
)


def _mapping_row(link_id: str = "link_1", **extra) -> dict:
    row = {
        "canonical_link_id": link_id,
        "molecule_id": "m1",
        "target_id": "tgt",
        "condition_hash": "cond",
        "functional_score": 1.0,
        "comb": 0.6,
        "P_hit": 0.7,
        "PAS": 0.8,
        "dist": 0.2,
        "LPCS": 0.3,
        "PCF": 0.4,
        "pairing_role": "native",
        "functional_score_dictionary_id": "functional-score-dict-v1",
    }
    row.update(extra)
    return row


def _fals_row(link_id: str = "link_1", **extra) -> dict:
    row = {
        "canonical_link_id": link_id,
        "molecule_id": "m1",
        "target_id": "tgt",
        "condition_hash": "cond",
        "functional_score": 1.0,
        "comb": 0.3,
        "P_hit": 0.2,
        "PAS": 0.1,
        "dist": 0.5,
        "LPCS": 0.6,
        "PCF": 0.7,
        "pairing_role": "matched_falsification",
        "shuffle_donor_pool_hash": "sha256:abc",
        "donor_plan_hash": "sha256:def",
        "functional_score_dictionary_id": "functional-score-dict-v1",
    }
    row.update(extra)
    return row


def test_validate_mapping_table_invariants_rejects_role_drift() -> None:
    errors, warnings = validate_mapping_table_invariants([
        _mapping_row(pairing_role="matched_falsification"),
    ])
    assert warnings == []
    assert "CAP_MAPPING_ROLE_INVALID:'matched_falsification'" in errors


def test_validate_falsification_table_invariants_rejects_duplicate_link() -> None:
    errors, _ = validate_falsification_table_invariants([
        _fals_row("link_1"),
        _fals_row("link_1"),
    ])
    assert "CAP_FALSIFICATION_DUPLICATE_CANONICAL_LINK:link_1" in errors


def test_validate_cap_batch_eval_invariants_rejects_truth_source_false() -> None:
    errors, warnings = validate_cap_batch_eval_invariants({
        "run_id": "r1",
        "status": "OK",
        "source_of_truth": False,
        "diagnostics_json": {},
        "reason_codes": [],
        "cap_batch_verdict": "PASS",
        "cap_batch_reason_code": None,
        "verdict_layer0": "PASS",
        "verdict_layer1": "PASS",
        "verdict_layer2": None,
        "verdict_final": "PASS",
    })
    assert warnings == []
    assert "CAP_BATCH_EVAL_TRUTH_SOURCE_FALSE" in errors


def test_validate_cap_artifact_invariants_rejects_fold_map_mismatch() -> None:
    errors, _ = validate_cap_artifact_invariants(
        mapping_source=[_mapping_row("link_a")],
        falsification_source=[_fals_row("link_b")],
    )
    assert "CAP_ARTIFACT_FOLD_MAP_MISMATCH" in errors


def _config_text(structure_path: str) -> str:
    return f"""target_name: tgt
config_role: smoke
expected_use: Pipeline health-check regime for end-to-end completion on real data.
allowed_comparisons: [cross-regime]
frozen_for_regression: false
pathway: covalent
pdb:
  path: {structure_path}
  model_id: 1
  altloc_policy: first
  include_hydrogens: false
residue_id_format: auth
target_cysteine: {{chain: A, residue_number: 1, insertion_code: '', atom_name: SG}}
anchor_atom_set:
  - {{chain: A, residue_number: 1, insertion_code: '', atom_name: SG}}
offtarget_cysteines:
  - {{chain: B, residue_number: 2, insertion_code: '', atom_name: SG}}
search_radius: 6.0
distance_threshold: 2.2
sampling: {{n_conformers: 1, n_rotations: 1, n_translations: 1, alpha: 0.5}}
anchoring: {{bond_threshold: 2.2, near_threshold: 3.5, epsilon: 0.1}}
offtarget: {{distance_threshold: 2.2, epsilon: 0.1}}
scv: {{confident_fail_threshold: 1, zero_feasible_abort: 4096}}
staging: {{retry_distance_lower: 2.2, retry_distance_upper: 3.5, far_target_threshold: 6.0, max_stage: 2}}
translation: {{local_fraction: 0.5, local_min_radius: 1.0, local_max_radius: 2.0, local_start_stage: 2}}
pat: {{path_model: TUNNEL, goal_mode: shell, grid_spacing: 0.5, probe_radius: 1.4, r_outer_margin: 2.0, blockage_pass_threshold: 0.5, top_k_poses: 4, goal_shell_clearance: 0.2, goal_shell_thickness: 1.0, surface_window_radius: 4.0}}
random_seed: 42
"""


def test_run_integrated_v29_records_cap_invariant_errors(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pyproject.toml").write_text('[project]\nname="crisp"\nversion="0.0.0"\n', encoding="utf-8")
    structure = repo_root / "s.cif"
    structure.write_text("data_dummy\n", encoding="utf-8")
    cfg_path = repo_root / "cfg.yaml"
    cfg_path.write_text(_config_text(str(structure)), encoding="utf-8")
    lib_path = Path(write_records_table(repo_root / "molecules.parquet", [
        {"molecule_id": "m1", "smiles": "CCO", "library_id": "lib", "input_order": 0},
    ]).path)
    caps_path = Path(write_records_table(repo_root / "caps.parquet", [
        {"cap_id": "cap_native", "target_id": "tgt", "axis_x": 1.0, "axis_y": 0.0, "axis_z": 0.0, "polar_coords_json": "[]", "motion_class": "m", "source_db": "db", "source_entry_id": "e1", "derivation_method": "manual", "is_canonical_cap": True},
    ]).path)
    stageplan = repo_root / "stageplan.json"
    stageplan.write_text("{}", encoding="utf-8")

    def fake_run_core_bridge(**kwargs):
        out_dir = kwargs["out_dir"]
        core_table = write_records_table(out_dir / "core_compounds.parquet", [{
            "run_id": out_dir.name,
            "molecule_id": "m1",
            "target_id": "tgt",
            "core_verdict": "PASS",
            "core_reason_code": None,
            "best_target_distance": 1.0,
            "best_offtarget_distance": 5.0,
            "final_stage": 1,
            "config_hash": "cfg",
            "legacy_core_final_verdict": "PASS",
        }])
        evidence_table = write_records_table(out_dir / "evidence_core.parquet", [{
            "run_id": out_dir.name,
            "molecule_id": "m1",
            "target_id": "tgt",
            "stage_id": 1,
            "translation_type": "global",
            "trial_number": 1,
            "stopped_at_trial": 1,
            "early_stop_reason": None,
            "anchoring_witness_pose_json": {},
            "anchoring_fail_certificate_json": {},
            "candidate_order_hash": "h",
            "near_band_triggered": False,
            "proposal_policy_version": "v29",
            "config_hash": "cfg",
            "requirements_hash": "req",
            "input_hash": "inp",
            "core_verdict": "PASS",
            "core_reason_code": None,
            "legacy_core_final_verdict": "PASS",
            "stage_history_json": [],
        }])
        (out_dir / "core_bridge_diagnostics.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        from crisp.v29.contracts import CoreBridgeResult

        return CoreBridgeResult(
            core_rows_path=core_table.path,
            evidence_core_path=evidence_table.path,
            diagnostics_path=str(out_dir / "core_bridge_diagnostics.json"),
            config_hash="cfg",
            input_hash="inp",
            requirements_hash="req",
            materialization_events=[
                core_table.to_materialization_event(logical_output="core_compounds.parquet"),
                evidence_table.to_materialization_event(logical_output="evidence_core.parquet"),
            ],
        )

    def fake_run_cap_batch_scv(**kwargs):
        return CapBatchEval(
            run_id=kwargs["run_id"],
            status="OK",
            cap_batch_verdict="PASS",
            cap_batch_reason_code=None,
            source_of_truth=False,
            verdict_layer0="PASS",
            verdict_layer1="PASS",
            verdict_layer2=None,
            verdict_final="PASS",
            reason_codes=[],
            diagnostics_json={},
        )

    monkeypatch.setattr("crisp.v29.cli.run_core_bridge", fake_run_core_bridge)
    monkeypatch.setattr("crisp.v29.cli.run_cap_batch_scv", fake_run_cap_batch_scv)

    result = run_integrated_v29(
        repo_root=repo_root,
        config_path=cfg_path,
        library_path=lib_path,
        stageplan_path=stageplan,
        out_dir=repo_root / "out",
        run_mode="core+rule1+cap",
        caps_path=caps_path,
    )

    assert result["run_mode_complete"] is False
    inventory = json.loads((repo_root / "out" / "output_inventory.json").read_text(encoding="utf-8"))
    assert "CAP_BATCH_EVAL_TRUTH_SOURCE_FALSE" in inventory["schema_validation"]["hard_errors"]
    replay = json.loads((repo_root / "out" / "replay_audit.json").read_text(encoding="utf-8"))
    assert replay["cap_invariant_consistency"] is False
    assert "CAP_BATCH_EVAL_TRUTH_SOURCE_FALSE" in replay["cap_invariant_errors"]
