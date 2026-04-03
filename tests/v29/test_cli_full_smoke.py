from __future__ import annotations

import json
from pathlib import Path

from crisp.v29.cli import run_integrated_v29
from crisp.v29.tableio import write_records_table


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
'''


def test_run_integrated_v29_full_with_stubbed_core(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    (repo_root / 'pyproject.toml').write_text('[project]\nname="crisp"\nversion="0.0.0"\n', encoding='utf-8')
    structure = repo_root / 's.cif'
    structure.write_text('data_dummy\n', encoding='utf-8')
    cfg_path = repo_root / 'cfg.yaml'
    cfg_path.write_text(_config_text(structure), encoding='utf-8')
    lib_path = Path(write_records_table(repo_root / 'molecules.parquet', [
        {'molecule_id': 'm1', 'smiles': 'CCO', 'library_id': 'lib', 'input_order': 0},
        {'molecule_id': 'm2', 'smiles': 'CCN', 'library_id': 'lib', 'input_order': 1},
    ]).path)
    caps_path = Path(write_records_table(repo_root / 'caps.parquet', [
        {'cap_id': 'cap_native', 'target_id': 'tgt', 'axis_x': 1.0, 'axis_y': 0.0, 'axis_z': 0.0, 'polar_coords_json': '[]', 'motion_class': 'm', 'source_db': 'db', 'source_entry_id': 'e1', 'derivation_method': 'manual', 'is_canonical_cap': True},
        {'cap_id': 'cap_other', 'target_id': 'tgt', 'axis_x': 0.0, 'axis_y': 1.0, 'axis_z': 0.0, 'polar_coords_json': '[]', 'motion_class': 'm', 'source_db': 'db', 'source_entry_id': 'e2', 'derivation_method': 'manual', 'is_canonical_cap': False},
    ]).path)
    assays_path = Path(write_records_table(repo_root / 'assays.parquet', [
        {'canonical_link_id': 'x', 'molecule_id': 'm1', 'target_id': 'tgt', 'condition_hash': 'c1', 'functional_score_raw': 1.0, 'assay_type': 'activity', 'direction': 'increase', 'unit': 'a.u.'},
    ]).path)
    stageplan = repo_root / 'stageplan.json'
    stageplan.write_text('{}', encoding='utf-8')

    def fake_run_core_bridge(**kwargs):
        out_dir = kwargs['out_dir']
        write_records_table(out_dir / 'core_compounds.parquet', [{'run_id': out_dir.name, 'molecule_id': 'm1', 'target_id': 'tgt', 'core_verdict': 'PASS', 'core_reason_code': None, 'best_target_distance': 1.0, 'best_offtarget_distance': 5.0, 'final_stage': 1, 'config_hash': 'cfg', 'legacy_core_final_verdict': 'PASS'}])
        write_records_table(out_dir / 'evidence_core.parquet', [{'run_id': out_dir.name, 'molecule_id': 'm1', 'target_id': 'tgt', 'stage_id': 1, 'translation_type': 'global', 'trial_number': 1, 'stopped_at_trial': 1, 'early_stop_reason': None, 'anchoring_witness_pose_json': {}, 'anchoring_fail_certificate_json': {}, 'candidate_order_hash': 'h', 'near_band_triggered': False, 'proposal_policy_version': 'v29', 'config_hash': 'cfg', 'requirements_hash': 'req', 'input_hash': 'inp', 'core_verdict': 'PASS', 'core_reason_code': None, 'legacy_core_final_verdict': 'PASS'}])
        (out_dir / 'core_bridge_diagnostics.json').write_text(json.dumps({'ok': True}), encoding='utf-8')
        from crisp.v29.contracts import CoreBridgeResult
        return CoreBridgeResult(core_rows_path=str(out_dir / 'core_compounds.parquet'), evidence_core_path=str(out_dir / 'evidence_core.parquet'), diagnostics_path=str(out_dir / 'core_bridge_diagnostics.json'), config_hash='cfg', input_hash='inp', requirements_hash='req')

    monkeypatch.setattr('crisp.v29.cli.run_core_bridge', fake_run_core_bridge)
    result = run_integrated_v29(repo_root=repo_root, config_path=cfg_path, library_path=lib_path, stageplan_path=stageplan, out_dir=repo_root / 'out', run_mode='full', caps_path=caps_path, assays_path=assays_path)
    assert result['run_mode_complete'] is True
    assert (repo_root / 'out' / 'run_manifest.json').exists()
    assert (repo_root / 'out' / 'cap_batch_eval.json').exists()
