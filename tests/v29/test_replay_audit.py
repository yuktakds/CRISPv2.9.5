from __future__ import annotations

from pathlib import Path

from crisp.v29.contracts import IntegratedRunManifest
from crisp.v29.manifest import build_completion_checks
from crisp.v29.writers import write_integrated_manifest, write_output_inventory
from crisp.v29.reports import run_replay_audit
from crisp.v29.contracts import OutputInventory


def test_replay_audit_passes_when_inventory_exists(tmp_path: Path) -> None:
    (tmp_path / 'output_inventory.json').write_text('{}', encoding='utf-8')
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
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='builtin:none', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}},
    )
    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode='core-only',
        required_outputs=['output_inventory.json'],
        generated_outputs=['output_inventory.json'],
        branch_status_json={'core': {'status': 'COMPLETE'}},
        schema_hard_errors=[],
        schema_warnings=[],
    )
    inventory = OutputInventory(
        run_id='r1', run_mode='core-only', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], missing_outputs=[], schema_validation={'status': 'PASS', 'hard_errors': [], 'warnings': [], 'errors': []}, warnings=[], run_mode_complete=True, branch_status_json={'core': {'status': 'COMPLETE'}}, completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}}, repo_root_source='cli', repo_root_resolved_path='/repo',
        completion_checks_json=checks,
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    write_output_inventory(tmp_path / 'output_inventory.json', inventory)
    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')
    assert payload['inventory_consistency'] is True
    assert payload['comparison_type'] == 'same-config'
    assert payload['comparison_type_source'] == 'config_role_default'
    assert payload['skip_reason_codes'] == []
    assert payload['inventory_json_errors'] == []
    assert payload['inventory_json_max_severity'] == 'none'
    assert payload['inventory_json_audit_status'] == 'AUDIT_READY'
    assert payload['inventory_drift_reason_codes'] == []


def test_replay_audit_detects_branch_status_completion_mismatch(tmp_path: Path) -> None:
    (tmp_path / 'output_inventory.json').write_text('{}', encoding='utf-8')
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
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='builtin:none', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}},
    )
    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode='core-only',
        required_outputs=['output_inventory.json'],
        generated_outputs=['output_inventory.json'],
        branch_status_json={'core': {'status': 'PENDING'}},
        schema_hard_errors=[],
        schema_warnings=[],
    )
    checks['run_mode_complete'] = True
    inventory = OutputInventory(
        run_id='r1', run_mode='core-only', requested_branches=['core'], implemented_branches=['core'],
        generated_outputs=['output_inventory.json'], missing_outputs=[], schema_validation={'status': 'PASS', 'hard_errors': [], 'warnings': [], 'errors': []},
        warnings=[], run_mode_complete=True, branch_status_json={'core': {'status': 'COMPLETE'}},
        completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}},
        completion_checks_json=checks,
        repo_root_source='cli', repo_root_resolved_path='/repo',
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    write_output_inventory(tmp_path / 'output_inventory.json', inventory)
    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')
    assert payload['inventory_consistency'] is False
    assert payload['inventory_branch_status_consistency'] is False
    assert 'DRIFT_BRANCH_STATUS' in payload['inventory_drift_reason_codes']


def test_replay_audit_detects_completion_checks_schema_drift(tmp_path: Path) -> None:
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
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='builtin:none', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}},
    )
    inventory = OutputInventory(
        run_id='r1', run_mode='core-only', requested_branches=['core'], implemented_branches=['core'],
        generated_outputs=['output_inventory.json'], missing_outputs=[], schema_validation={'status': 'PASS', 'hard_errors': [], 'warnings': [], 'errors': []},
        warnings=[], run_mode_complete=True, branch_status_json={'core': {'status': 'COMPLETE'}},
        completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}},
        completion_checks_json={'run_mode_complete': True},
        repo_root_source='cli', repo_root_resolved_path='/repo',
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    write_output_inventory(tmp_path / 'output_inventory.json', inventory)
    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')
    assert payload['inventory_consistency'] is False
    assert payload['inventory_completion_checks_schema_errors']
    assert 'DRIFT_COMPLETION_CHECKS_SCHEMA' in payload['inventory_drift_reason_codes']


def test_replay_audit_reports_invalid_inventory_json_without_crashing(tmp_path: Path) -> None:
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
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='builtin:none', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}},
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    (tmp_path / 'output_inventory.json').write_text('{', encoding='utf-8')

    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')

    assert payload['inventory_consistency'] is False
    assert payload['inventory_json_errors']
    assert payload['inventory_json_errors'][0]['code'] == 'OUTPUT_INVENTORY_JSON_DECODE_ERROR'
    assert payload['inventory_json_errors'][0]['severity'] == 'recoverable'
    assert payload['inventory_json_max_severity'] == 'recoverable'
    assert payload['inventory_json_audit_status'] == 'AUDIT_CONTINUABLE'
    assert 'DRIFT_INVENTORY_JSON_RECOVERABLE' in payload['inventory_drift_reason_codes']


def test_replay_audit_detects_completion_basis_drift(tmp_path: Path) -> None:
    (tmp_path / 'output_inventory.json').write_text('{}', encoding='utf-8')
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
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='builtin:none', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}, 'comparison_type': 'same-config'},
    )
    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode='core-only',
        required_outputs=['output_inventory.json'],
        generated_outputs=['output_inventory.json'],
        branch_status_json={'core': {'status': 'COMPLETE'}},
        schema_hard_errors=[],
        schema_warnings=[],
    )
    inventory = OutputInventory(
        run_id='r1', run_mode='core-only', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json'], missing_outputs=[], schema_validation={'status': 'PASS', 'hard_errors': [], 'warnings': [], 'errors': []}, warnings=[], run_mode_complete=True, branch_status_json={'core': {'status': 'COMPLETE'}}, completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}, 'comparison_type': 'cross-regime'}, repo_root_source='cli', repo_root_resolved_path='/repo',
        completion_checks_json=checks,
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    write_output_inventory(tmp_path / 'output_inventory.json', inventory)

    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')

    assert payload['inventory_consistency'] is False
    assert payload['inventory_completion_basis_consistency'] is False
    assert 'DRIFT_COMPARISON_TYPE' in payload['inventory_drift_reason_codes']


def test_replay_audit_reports_missing_theta_resolution_trace_for_rule1_runs(tmp_path: Path) -> None:
    (tmp_path / 'output_inventory.json').write_text('{}', encoding='utf-8')
    manifest = IntegratedRunManifest(
        run_id='r1', spec_version='v2.9.5', run_mode='core+rule1', resource_profile='smoke',
        target_case_id='t', target_config_path='cfg.yaml',
        target_config_role='benchmark',
        target_config_expected_use='Frozen regression baseline for parser, search, and reason-taxonomy changes.',
        target_config_allowed_comparisons=['same-config', 'cross-regime'],
        target_config_frozen_for_regression=True,
        structure_path='s.cif', library_path='lib.smi', stageplan_path='sp.json',
        config_hash='c', input_hash='i', requirements_hash='r', library_hash='l', compound_order_hash='o', staging_plan_hash='sp', structure_file_digest='sd',
        rotation_seed=1, shuffle_seed=1, bootstrap_seed=1, cv_seed=1, label_shuffle_seed=1, shuffle_universe_scope='target_family_motion_class', shuffle_donor_pool_hash=None, donor_plan_hash=None,
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='table:theta',
        requested_branches=['core', 'rule1'], implemented_branches=['core', 'rule1'], generated_outputs=['output_inventory.json'],
        repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'required_outputs_by_mode': {'core+rule1': ['output_inventory.json']}},
    )
    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode='core+rule1',
        required_outputs=['output_inventory.json'],
        generated_outputs=['output_inventory.json'],
        branch_status_json={'core': {'status': 'COMPLETE'}, 'rule1': {'status': 'COMPLETE'}},
        schema_hard_errors=[],
        schema_warnings=[],
    )
    inventory = OutputInventory(
        run_id='r1', run_mode='core+rule1', requested_branches=['core', 'rule1'], implemented_branches=['core', 'rule1'], generated_outputs=['output_inventory.json'], missing_outputs=[], schema_validation={'status': 'PASS', 'hard_errors': [], 'warnings': [], 'errors': []}, warnings=[], run_mode_complete=True, branch_status_json={'core': {'status': 'COMPLETE'}, 'rule1': {'status': 'COMPLETE'}}, completion_basis_json={'required_outputs_by_mode': {'core+rule1': ['output_inventory.json']}}, repo_root_source='cli', repo_root_resolved_path='/repo',
        completion_checks_json=checks,
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    write_output_inventory(tmp_path / 'output_inventory.json', inventory)

    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')

    assert payload['theta_rule1_resolution_available'] is False
    assert payload['theta_rule1_consistency'] is False
    assert payload['result'] == 'UNCLEAR'


def test_replay_audit_reads_rule3_trace_summary_sidecar(tmp_path: Path) -> None:
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
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='builtin:none', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json', 'rule3_trace_summary.json'], repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}},
    )
    checks = build_completion_checks(
        run_dir=tmp_path,
        run_mode='core-only',
        required_outputs=['output_inventory.json'],
        generated_outputs=['output_inventory.json', 'rule3_trace_summary.json'],
        branch_status_json={'core': {'status': 'COMPLETE'}},
        schema_hard_errors=[],
        schema_warnings=[],
    )
    inventory = OutputInventory(
        run_id='r1', run_mode='core-only', requested_branches=['core'], implemented_branches=['core'], generated_outputs=['output_inventory.json', 'rule3_trace_summary.json'], missing_outputs=[], schema_validation={'status': 'PASS', 'hard_errors': [], 'warnings': [], 'errors': []}, warnings=[], run_mode_complete=True, branch_status_json={'core': {'status': 'COMPLETE'}}, completion_basis_json={'required_outputs_by_mode': {'core-only': ['output_inventory.json']}}, repo_root_source='cli', repo_root_resolved_path='/repo',
        completion_checks_json=checks,
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    write_output_inventory(tmp_path / 'output_inventory.json', inventory)
    (tmp_path / 'rule3_trace_summary.json').write_text(
        '{"record_count":1,"run_summary":{"ordering_distribution":[{"ordering_label":"struct_conn","count":1}],"proposal_handling_totals":{"selected_top_n":1}},"summary_version":"rule3_trace_summary/v1","top_n_limit":3}',
        encoding='utf-8',
    )

    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')

    assert payload['rule3_trace_summary_available'] is True
    assert payload['rule3_trace_summary_record_count'] == 1
    assert payload['rule3_trace_summary_top_n_limit'] == 3
    assert payload['rule3_trace_ordering_distribution'] == [{'ordering_label': 'struct_conn', 'count': 1}]
    assert payload['rule3_trace_proposal_handling_totals'] == {'selected_top_n': 1}


def test_replay_audit_reports_stale_manifest_missing_required_outputs(tmp_path: Path) -> None:
    manifest = IntegratedRunManifest(
        run_id='r1', spec_version='v2.9.5', run_mode='core+rule1', resource_profile='smoke',
        target_case_id='t', target_config_path='cfg.yaml',
        target_config_role='benchmark',
        target_config_expected_use='Frozen regression baseline for parser, search, and reason-taxonomy changes.',
        target_config_allowed_comparisons=['same-config', 'cross-regime'],
        target_config_frozen_for_regression=True,
        structure_path='s.cif', library_path='lib.smi', stageplan_path='sp.json',
        config_hash='c', input_hash='i', requirements_hash='r', library_hash='l', compound_order_hash='o', staging_plan_hash='sp', structure_file_digest='sd',
        rotation_seed=1, shuffle_seed=1, bootstrap_seed=1, cv_seed=1, label_shuffle_seed=1, shuffle_universe_scope='target_family_motion_class', shuffle_donor_pool_hash=None, donor_plan_hash=None,
        functional_score_dictionary_id='functional-score-dict-v1', theta_rule1_table_id='builtin:none', requested_branches=['core', 'rule1'], implemented_branches=['core', 'rule1'], generated_outputs=['output_inventory.json'],
        repo_root_source='cli', repo_root_resolved_path='/repo', completion_basis_json={'required_outputs_by_mode': {'core+rule1': ['output_inventory.json', 'rule1_assessments.parquet']}},
    )
    inventory = OutputInventory(
        run_id='r1', run_mode='core+rule1', requested_branches=['core', 'rule1'], implemented_branches=['core', 'rule1'], generated_outputs=['output_inventory.json'], missing_outputs=[], schema_validation={'status': 'PASS', 'hard_errors': [], 'warnings': [], 'errors': []}, warnings=[], run_mode_complete=True, branch_status_json={'core': {'status': 'COMPLETE'}, 'rule1': {'status': 'COMPLETE'}}, completion_basis_json={'required_outputs_by_mode': {'core+rule1': ['output_inventory.json', 'rule1_assessments.parquet']}}, repo_root_source='cli', repo_root_resolved_path='/repo',
        completion_checks_json={'schema_version': 'v1', 'required_outputs': [], 'materialized_output_paths': {}, 'required_branches': [], 'declared_missing_outputs': [], 'missing_output_files': [], 'empty_output_files': [], 'completion_blocker_outputs': [], 'required_branch_statuses': {}, 'incomplete_required_branches': [], 'schema_hard_errors': [], 'schema_warnings': [], 'schema_validation_status': 'PASS', 'run_mode_complete': True},
    )
    write_integrated_manifest(tmp_path / 'run_manifest.json', manifest)
    write_output_inventory(tmp_path / 'output_inventory.json', inventory)

    payload = run_replay_audit(manifest_path=tmp_path / 'run_manifest.json')

    assert payload['stale_manifest_detected'] is True
    assert payload['manifest_missing_required_outputs'] == ['rule1_assessments.parquet']
