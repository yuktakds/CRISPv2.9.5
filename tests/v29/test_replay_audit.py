from __future__ import annotations

from pathlib import Path

from crisp.v29.contracts import IntegratedRunManifest
from crisp.v29.writers import write_integrated_manifest, write_output_inventory
from crisp.v29.reports import run_replay_audit
from crisp.v29.contracts import OutputInventory


def test_replay_audit_passes_when_inventory_exists(tmp_path: Path) -> None:
    manifest = IntegratedRunManifest(
        run_id='r1', spec_version='v2.9.5', run_mode='core-only', resource_profile='smoke',
        target_case_id='t', target_config_path='cfg.yaml',
        target_config_role='benchmark',
        target_config_expected_use='Frozen regression baseline for parser, search, and reason-taxonomy changes.',
        target_config_allowed_comparisons=['same-config', 'cross-regime'],
        target_config_frozen_for_regression=True,
        structure_path='s.cif', library_path='lib.smi', stageplan_path='sp.json',
        config_hash='c', input_hash='i', requirements_hash='r', library_hash='l', compound_order_hash='o', staging_plan_hash='sp', structure_file_digest='sd',
        rotation_seed=1, shuffle_seed=1, bootstrap_seed=1, cv_seed=1, label_shuffle_seed=1, shuffle_universe_scope='target_family_motion_class', shuffle_donor_pool_hash=None, donor_plan_hash=None,
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='builtin:none', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'a': 1},
    )
    inventory = OutputInventory(
        run_id='r1', run_mode='core-only', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], missing_outputs=[], schema_validation={'status': 'PASS'}, warnings=[], run_mode_complete=True, branch_status_json={'core': {'status': 'COMPLETE'}}, completion_basis_json={'a': 1}, repo_root_source='cli', repo_root_resolved_path='/repo',
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    write_output_inventory(tmp_path / 'output_inventory.json', inventory)
    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')
    assert payload['inventory_consistency'] is True
