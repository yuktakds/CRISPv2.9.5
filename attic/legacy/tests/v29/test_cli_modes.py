from __future__ import annotations

import json
from pathlib import Path

from crisp.config.loader import load_target_config
from crisp.repro.hashing import compute_config_hash
from crisp.v29.cli import _required_outputs_for_mode, run_integrated_v29
from crisp.v29.rule1_theta import (
    ThetaRule1RuntimeError,
    write_theta_rule1_calibration_table,
)
from crisp.v29.tableio import write_records_table


def test_required_outputs_for_cap_mode_include_cap_reports() -> None:
    required = _required_outputs_for_mode("core+rule1+cap")
    assert "cap_batch_eval.json" in required
    assert "qc_report.json" in required
    assert "eval_report.json" in required
    assert "collapse_figure_spec.json" in required


def test_required_outputs_for_full_mode_include_validation_reports() -> None:
    required = _required_outputs_for_mode("full")
    assert "mapping_table.parquet" in required
    assert "falsification_table.parquet" in required
    assert "cap_batch_eval.json" in required
    assert "qc_report.json" in required
    assert "eval_report.json" in required
    assert "collapse_figure_spec.json" in required


def test_run_integrated_v29_records_machine_readable_skip_reason_codes(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pyproject.toml").write_text('[project]\nname="crisp"\nversion="0.0.0"\n', encoding="utf-8")
    structure = repo_root / "s.cif"
    structure.write_text("data_dummy\n", encoding="utf-8")
    cfg_path = repo_root / "cfg.yaml"
    cfg_path.write_text(
        f"""target_name: tgt
config_role: smoke
expected_use: Pipeline health-check regime for end-to-end completion on real data.
allowed_comparisons: [cross-regime]
frozen_for_regression: false
pathway: covalent
pdb:
  path: {structure}
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
""",
        encoding="utf-8",
    )
    lib_path = Path(write_records_table(repo_root / "molecules.parquet", [
        {"molecule_id": "m1", "smiles": "CCO", "library_id": "lib", "input_order": 0},
    ]).path)
    stageplan = repo_root / "stageplan.json"
    stageplan.write_text("{}", encoding="utf-8")
    integrated_cfg = repo_root / "integrated.yaml"
    integrated_cfg.write_text(
        "pathyes_mode: bootstrap\npathyes_force_false: true\n",
        encoding="utf-8",
    )
    events: list[tuple[str, str]] = []

    class _Reporter:
        def progress(self, message: str) -> None:
            events.append(("progress", message))

        def warn(self, message: str) -> None:
            events.append(("warn", message))

        def skip(self, message: str) -> None:
            events.append(("skip", message))

    def fake_run_core_bridge(**kwargs):
        out_dir = kwargs["out_dir"]
        core_table = write_records_table(out_dir / "core_compounds.parquet", [{
            "run_id": out_dir.name, "molecule_id": "m1", "target_id": "tgt",
            "core_verdict": "PASS", "core_reason_code": None, "best_target_distance": 1.0,
            "best_offtarget_distance": 5.0, "final_stage": 1, "config_hash": "cfg",
            "legacy_core_final_verdict": "PASS",
        }])
        evidence_table = write_records_table(out_dir / "evidence_core.parquet", [{
            "run_id": out_dir.name, "molecule_id": "m1", "target_id": "tgt",
            "stage_id": 1, "translation_type": "global", "trial_number": 1,
            "stopped_at_trial": 1, "early_stop_reason": None,
            "anchoring_witness_pose_json": {}, "anchoring_fail_certificate_json": {},
            "candidate_order_hash": "h", "near_band_triggered": False,
            "proposal_policy_version": "v29", "config_hash": "cfg",
            "requirements_hash": "req", "input_hash": "inp", "core_verdict": "PASS",
            "core_reason_code": None, "legacy_core_final_verdict": "PASS",
            "stage_history_json": [],
        }])
        (out_dir / "core_bridge_diagnostics.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        from crisp.v29.contracts import CoreBridgeResult
        return CoreBridgeResult(
            core_rows_path=core_table.path,
            core_compounds_path=core_table.path,
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

    monkeypatch.setattr("crisp.v29.cli.run_core_bridge", fake_run_core_bridge)
    run_integrated_v29(
        repo_root=repo_root,
        config_path=cfg_path,
        library_path=lib_path,
        stageplan_path=stageplan,
        out_dir=repo_root / "out",
        integrated_config_path=integrated_cfg,
        run_mode="core+rule1",
        reporter=_Reporter(),
    )

    manifest = json.loads((repo_root / "out" / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["completion_basis_json"]["comparison_type"] == "cross-regime"
    assert manifest["completion_basis_json"]["comparison_type_source"] == "config_role_default"
    assert manifest["completion_basis_json"]["skip_reason_codes"] == ["SKIP_PATHYES_BOOTSTRAP"]
    assert manifest["completion_basis_json"]["output_fallback_reason_codes"] == [
        "FALLBACK_PARQUET_WRITE_FAILED"
    ]
    evidence_event = next(
        event for event in manifest["completion_basis_json"]["output_materialization_events"]
        if event["logical_output"] == "evidence_core.parquet"
    )
    assert evidence_event["fallback_used"] is True
    assert evidence_event["fallback_reason_code"] == "FALLBACK_PARQUET_WRITE_FAILED"
    assert ("skip", "SKIP_PATHYES_BOOTSTRAP") in events
    assert any(level == "progress" and message == "branch=core start" for level, message in events)
    assert any(level == "progress" and message == "branch=rule1 start" for level, message in events)


def test_run_integrated_v29_traces_pat_backed_diagnostics_state(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pyproject.toml").write_text('[project]\nname="crisp"\nversion="0.0.0"\n', encoding="utf-8")
    structure = repo_root / "s.cif"
    structure.write_text("data_dummy\n", encoding="utf-8")
    cfg_path = repo_root / "cfg.yaml"
    cfg_path.write_text(
        f"""target_name: tgt
config_role: benchmark
expected_use: Frozen regression baseline for parser, search, and reason-taxonomy changes.
allowed_comparisons: [same-config, cross-regime]
frozen_for_regression: true
pathway: covalent
pdb:
  path: {structure}
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
""",
        encoding="utf-8",
    )
    lib_path = Path(write_records_table(repo_root / "molecules.parquet", [
        {"molecule_id": "m1", "smiles": "CCO", "library_id": "lib", "input_order": 0},
    ]).path)
    stageplan = repo_root / "stageplan.json"
    stageplan.write_text("{}", encoding="utf-8")
    cfg_hash = compute_config_hash(load_target_config(cfg_path))
    theta_table = write_theta_rule1_calibration_table(
        repo_root / "theta_rule1_table.parquet",
        values_by_key={"default": 1.0, "tgt": 0.8},
        table_version="2026-04-03",
        table_source="benchmark:cfg.yaml seed=42 cohort=dev",
        benchmark_config_path=str(cfg_path),
        benchmark_config_hash=cfg_hash,
        calibration_seed=42,
        calibration_cohort="dev",
        calibrated_by="test-suite",
    )
    integrated_cfg = repo_root / "integrated.yaml"
    integrated_cfg.write_text(
        f"pathyes_mode: pat-backed\ntheta_rule1_table: {theta_table.path}\n",
        encoding="utf-8",
    )

    def fake_run_core_bridge(**kwargs):
        out_dir = kwargs["out_dir"]
        core_table = write_records_table(out_dir / "core_compounds.parquet", [{
            "run_id": out_dir.name, "molecule_id": "m1", "target_id": "tgt",
            "core_verdict": "PASS", "core_reason_code": None, "best_target_distance": 1.0,
            "best_offtarget_distance": 5.0, "final_stage": 1, "config_hash": "cfg",
            "legacy_core_final_verdict": "PASS",
        }])
        evidence_table = write_records_table(out_dir / "evidence_core.parquet", [{
            "run_id": out_dir.name, "molecule_id": "m1", "target_id": "tgt",
            "stage_id": 1, "translation_type": "global", "trial_number": 1,
            "stopped_at_trial": 1, "early_stop_reason": None,
            "anchoring_witness_pose_json": {}, "anchoring_fail_certificate_json": {},
            "candidate_order_hash": "h", "near_band_triggered": False,
            "proposal_policy_version": "v29", "config_hash": "cfg",
            "requirements_hash": "req", "input_hash": "inp", "core_verdict": "PASS",
            "core_reason_code": None, "legacy_core_final_verdict": "PASS",
            "stage_history_json": [],
        }])
        (out_dir / "core_bridge_diagnostics.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        from crisp.v29.contracts import CoreBridgeResult
        return CoreBridgeResult(
            core_rows_path=core_table.path,
            core_compounds_path=core_table.path,
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

    monkeypatch.setattr("crisp.v29.cli.run_core_bridge", fake_run_core_bridge)
    run_integrated_v29(
        repo_root=repo_root,
        config_path=cfg_path,
        library_path=lib_path,
        stageplan_path=stageplan,
        out_dir=repo_root / "out-pat",
        integrated_config_path=integrated_cfg,
        run_mode="core+rule1",
    )

    manifest = json.loads((repo_root / "out-pat" / "run_manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads((repo_root / "out-pat" / "output_inventory.json").read_text(encoding="utf-8"))

    assert manifest["completion_basis_json"]["pathyes_mode_requested"] == "pat-backed"
    assert manifest["completion_basis_json"]["pathyes_mode_resolved"] == "pat-backed"
    assert manifest["completion_basis_json"]["pathyes_diagnostics_status"] == "missing"
    assert manifest["completion_basis_json"]["pathyes_diagnostics_error_code"] == "PAT_DIAGNOSTICS_PATH_NOT_PROVIDED"
    assert manifest["completion_basis_json"]["pathyes_rule1_applicability"] == "PATH_NOT_EVALUABLE"
    assert manifest["completion_basis_json"]["pathyes_skip_code"] == "SKIP_PATHYES_PAT_DIAGNOSTICS_MISSING"
    assert manifest["completion_basis_json"]["skip_reason_codes"] == ["SKIP_PATHYES_PAT_DIAGNOSTICS_MISSING"]
    assert manifest["theta_rule1_table_version"] == "2026-04-03"
    assert manifest["theta_rule1_table_source"] == "benchmark:cfg.yaml seed=42 cohort=dev"
    assert manifest["theta_rule1_table_digest"].startswith("sha256:")
    assert manifest["theta_rule1_runtime_contract"] == "crisp.v29.theta_rule1.runtime/v1"
    assert inventory["branch_status_json"]["rule1"]["pathyes_diagnostics_status"] == "missing"
    assert inventory["branch_status_json"]["rule1"]["pathyes_skip_code"] == "SKIP_PATHYES_PAT_DIAGNOSTICS_MISSING"


def test_run_integrated_v29_requires_managed_theta_table_for_pat_backed_rule1(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pyproject.toml").write_text('[project]\nname="crisp"\nversion="0.0.0"\n', encoding="utf-8")
    structure = repo_root / "s.cif"
    structure.write_text("data_dummy\n", encoding="utf-8")
    cfg_path = repo_root / "cfg.yaml"
    cfg_path.write_text(
        f"""target_name: tgt
config_role: benchmark
expected_use: Frozen regression baseline for parser, search, and reason-taxonomy changes.
allowed_comparisons: [same-config, cross-regime]
frozen_for_regression: true
pathway: covalent
pdb:
  path: {structure}
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
""",
        encoding="utf-8",
    )
    lib_path = Path(write_records_table(repo_root / "molecules.parquet", [
        {"molecule_id": "m1", "smiles": "CCO", "library_id": "lib", "input_order": 0},
    ]).path)
    stageplan = repo_root / "stageplan.json"
    stageplan.write_text("{}", encoding="utf-8")
    integrated_cfg = repo_root / "integrated.yaml"
    integrated_cfg.write_text(
        "pathyes_mode: pat-backed\n",
        encoding="utf-8",
    )

    def fake_run_core_bridge(**kwargs):
        out_dir = kwargs["out_dir"]
        core_table = write_records_table(out_dir / "core_compounds.parquet", [{
            "run_id": out_dir.name, "molecule_id": "m1", "target_id": "tgt",
            "core_verdict": "PASS", "core_reason_code": None, "best_target_distance": 1.0,
            "best_offtarget_distance": 5.0, "final_stage": 1, "config_hash": "cfg",
            "legacy_core_final_verdict": "PASS",
        }])
        evidence_table = write_records_table(out_dir / "evidence_core.parquet", [{
            "run_id": out_dir.name, "molecule_id": "m1", "target_id": "tgt",
            "stage_id": 1, "translation_type": "global", "trial_number": 1,
            "stopped_at_trial": 1, "early_stop_reason": None,
            "anchoring_witness_pose_json": {}, "anchoring_fail_certificate_json": {},
            "candidate_order_hash": "h", "near_band_triggered": False,
            "proposal_policy_version": "v29", "config_hash": "cfg",
            "requirements_hash": "req", "input_hash": "inp", "core_verdict": "PASS",
            "core_reason_code": None, "legacy_core_final_verdict": "PASS",
            "stage_history_json": [],
        }])
        (out_dir / "core_bridge_diagnostics.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        from crisp.v29.contracts import CoreBridgeResult
        return CoreBridgeResult(
            core_rows_path=core_table.path,
            core_compounds_path=core_table.path,
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

    monkeypatch.setattr("crisp.v29.cli.run_core_bridge", fake_run_core_bridge)

    try:
        run_integrated_v29(
            repo_root=repo_root,
            config_path=cfg_path,
            library_path=lib_path,
            stageplan_path=stageplan,
            out_dir=repo_root / "out-pat-no-theta",
            integrated_config_path=integrated_cfg,
            run_mode="core+rule1",
        )
    except ThetaRule1RuntimeError as exc:
        assert exc.code == "THETA_RULE1_TABLE_MISSING"
    else:
        raise AssertionError("expected managed theta_rule1 table requirement to fail")
