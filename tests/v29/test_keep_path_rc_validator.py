from __future__ import annotations

import json
from pathlib import Path

from crisp.v29.cli import run_integrated_v29
from crisp.v3.public_scope_validator import validate_keep_path_rc_run_directory
from tests.v29_smoke_helpers import make_stub_core_bridge, write_managed_theta_table, write_pat_diagnostics


def _write_fixture_config(repo_root: Path) -> tuple[Path, Path, Path]:
    (repo_root / "pyproject.toml").write_text('[project]\nname="crisp"\nversion="0.0.0"\n', encoding="utf-8")
    structure = repo_root / "s.cif"
    structure.write_text("data_dummy\n", encoding="utf-8")
    config_path = repo_root / "cfg.yaml"
    config_path.write_text(
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
    library_path = repo_root / "molecules.smi"
    library_path.write_text("CCO m1\n", encoding="utf-8")
    stageplan_path = repo_root / "stageplan.json"
    stageplan_path.write_text("{}", encoding="utf-8")
    return config_path, library_path, stageplan_path


def test_keep_path_rc_validator_accepts_integrated_v29_run(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path, library_path, stageplan_path = _write_fixture_config(repo_root)
    pat_diagnostics_path = write_pat_diagnostics(
        repo_root / "pat.json",
        goal_precheck_passed=True,
        extra_diagnostics={
            "blockage_ratio": 0.8,
            "apo_accessible_goal_voxels": 4,
            "feasible_count": 5,
            "witness_pose_id": "pose-1",
            "obstruction_path_ids": ["path-1"],
        },
    )
    theta_table_path = write_managed_theta_table(
        repo_root / "theta_rule1.parquet",
        config_path=config_path,
    )
    integrated_config_path = repo_root / "integrated.yaml"
    integrated_config_path.write_text(
        "\n".join(
            [
                "pathyes_mode: pat-backed",
                f"pat_diagnostics_path: {pat_diagnostics_path}",
                f"theta_rule1_table: {theta_table_path}",
                "v3_sidecar:",
                "  enabled: true",
                "v3_bridge_comparator:",
                "  enabled: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(library_path=library_path, target_id="tgt"),
    )

    out_dir = tmp_path / "run"
    result = run_integrated_v29(
        repo_root=repo_root,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        out_dir=out_dir,
        integrated_config_path=integrated_config_path,
        run_mode="core+rule1",
    )

    errors, warnings, diagnostics = validate_keep_path_rc_run_directory(out_dir)

    assert result["run_mode_complete"] is True
    assert errors == []
    assert warnings == []
    assert diagnostics["validation_passed"] is True


def test_keep_path_rc_validator_rejects_output_inventory_leak_from_integrated_run(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path, library_path, stageplan_path = _write_fixture_config(repo_root)
    pat_diagnostics_path = write_pat_diagnostics(
        repo_root / "pat.json",
        goal_precheck_passed=True,
        extra_diagnostics={"blockage_ratio": 0.8, "apo_accessible_goal_voxels": 4},
    )
    theta_table_path = write_managed_theta_table(
        repo_root / "theta_rule1.parquet",
        config_path=config_path,
    )
    integrated_config_path = repo_root / "integrated.yaml"
    integrated_config_path.write_text(
        "\n".join(
            [
                "pathyes_mode: pat-backed",
                f"pat_diagnostics_path: {pat_diagnostics_path}",
                f"theta_rule1_table: {theta_table_path}",
                "v3_sidecar:",
                "  enabled: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(library_path=library_path, target_id="tgt"),
    )

    out_dir = tmp_path / "run"
    run_integrated_v29(
        repo_root=repo_root,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        out_dir=out_dir,
        integrated_config_path=integrated_config_path,
        run_mode="core+rule1",
    )

    inventory_path = out_dir / "output_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["generated_outputs"].append("v3_sidecar/verdict_record.json")
    inventory_path.write_text(json.dumps(inventory, sort_keys=True), encoding="utf-8")

    errors, _, diagnostics = validate_keep_path_rc_run_directory(out_dir)

    assert "KEEP_PATH_RC_OUTPUT_INVENTORY_MUTATED:v3_sidecar/verdict_record.json" in errors
    assert diagnostics["validation_passed"] is False
