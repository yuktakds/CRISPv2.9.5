from __future__ import annotations

from pathlib import Path

from crisp.config.loader import load_target_config
from crisp.repro.manifest import (
    build_mef_run_sidecar_manifest,
    build_phase1_run_sidecar_manifest,
    build_run_manifest,
)


def _benchmark_config_text(structure_path: Path) -> str:
    return f"""target_name: tgt
config_role: benchmark
expected_use: Frozen regression baseline for parser, search, and reason-taxonomy changes.
allowed_comparisons:
  - same-config
  - cross-regime
frozen_for_regression: true
pathway: covalent
pdb:
  path: {structure_path.as_posix()}
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
sampling: {{n_conformers: 4, n_rotations: 16, n_translations: 8, alpha: 0.4}}
anchoring: {{bond_threshold: 2.2, near_threshold: 3.5, epsilon: 0.1}}
offtarget: {{distance_threshold: 2.2, epsilon: 0.1}}
scv: {{confident_fail_threshold: 1, zero_feasible_abort: 4096}}
staging: {{retry_distance_lower: 2.2, retry_distance_upper: 3.5, far_target_threshold: 6.0, max_stage: 2}}
translation: {{local_fraction: 0.5, local_min_radius: 1.0, local_max_radius: 2.0, local_start_stage: 2}}
pat: {{path_model: TUNNEL, goal_mode: shell, grid_spacing: 0.5, probe_radius: 1.4, r_outer_margin: 2.0, blockage_pass_threshold: 0.5, top_k_poses: 4, goal_shell_clearance: 0.2, goal_shell_thickness: 1.0, surface_window_radius: 4.0}}
random_seed: 42
"""


def test_manifests_capture_config_taxonomy_metadata(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    structure = repo_root / "s.cif"
    structure.write_text("data_dummy\n", encoding="utf-8")
    library = repo_root / "library.smi"
    library.write_text("CCO cmp1\n", encoding="utf-8")
    stageplan = repo_root / "stageplan.json"
    stageplan.write_text("{}", encoding="utf-8")
    config_path = repo_root / "benchmark.yaml"
    config_path.write_text(_benchmark_config_text(structure), encoding="utf-8")

    config = load_target_config(config_path)

    run_manifest = build_run_manifest(
        run_id="run-1",
        repo_root=repo_root,
        config_path=config_path,
        config=config,
        library_path=library,
        stageplan_path=stageplan,
    )
    assert run_manifest.target_config_role == "benchmark"
    assert run_manifest.target_config_expected_use == config.expected_use
    assert run_manifest.target_config_allowed_comparisons == ["same-config", "cross-regime"]
    assert run_manifest.target_config_frozen_for_regression is True

    mef_manifest = build_mef_run_sidecar_manifest(
        run_id="mef-1",
        config_path=config_path,
        config=config,
        library_path=library,
        report_path=repo_root / "mef_report.jsonl",
        summary_path=repo_root / "mef_summary.json",
        mef_pass_library_path=repo_root / "mef_pass.smi",
        mef_fail_library_path=repo_root / "mef_fail.smi",
        config_hash="cfg",
        requirements_hash="req",
    )
    assert mef_manifest.target_config_role == "benchmark"
    assert mef_manifest.target_config_frozen_for_regression is True

    phase1_manifest = build_phase1_run_sidecar_manifest(
        run_id="phase1-1",
        config=config,
        supplied_phase1_library_path=library,
        effective_phase1_library_path=library,
        mef_strategy="rerun",
        current_config_hash="cfg",
        current_requirements_hash="req",
        phase1_stage_accumulation_mode="current-accumulate-all-stages",
        cpg_local_offsets_mode="current",
        cpg_clash_mode="current",
        cpg_global_sampler_mode="current",
    )
    assert phase1_manifest.current_config_role == "benchmark"
    assert phase1_manifest.current_config_expected_use == config.expected_use
    assert phase1_manifest.current_config_allowed_comparisons == ["same-config", "cross-regime"]
    assert phase1_manifest.current_config_frozen_for_regression is True
