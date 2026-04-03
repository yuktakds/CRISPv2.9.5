from __future__ import annotations

import json
from pathlib import Path

from crisp.config.loader import load_target_config
from crisp.v29.pathyes import resolve_pathyes_state


def _config_text(structure_path: str) -> str:
    return f'''target_name: tgt
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
'''.replace('\n ', '\n')


def test_resolve_pathyes_state_pat_backed(tmp_path: Path) -> None:
    structure = tmp_path / 's.cif'
    structure.write_text('data_dummy\n', encoding='utf-8')
    cfg_path = tmp_path / 'cfg.yaml'
    cfg_path.write_text(_config_text(structure), encoding='utf-8')
    cfg = load_target_config(cfg_path)
    pat = tmp_path / 'pat.json'
    pat.write_text(json.dumps({'supported_path_model': True, 'goal_precheck_passed': True, 'pat_run_diagnostics_json': {'mode': 'pat-backed'}}), encoding='utf-8')
    state = resolve_pathyes_state(config=cfg, mode='pat-backed', pat_diagnostics_path=pat)
    assert state.goal_precheck_passed is True
    assert state.rule1_applicability == 'PATH_EVALUABLE'
