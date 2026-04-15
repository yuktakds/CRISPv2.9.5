from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crisp.config.loader import load_target_config
from crisp.config.models import TargetConfig
from crisp.repro.hashing import compute_config_hash
from crisp.v29.cap_truth import (
    CAP_TRUTH_SOURCE_REQUIRED_FIELDS,
    build_cap_truth_source_provenance,
)
from crisp.v29.inputs import load_molecule_rows
from crisp.v29.rule1_theta import ThetaRule1RuntimeTable
from crisp.v29.tableio import read_records_table


def validate_molecules_input(path: str | Path) -> tuple[list[str], list[str]]:
    try:
        rows = load_molecule_rows(path)
    except Exception as exc:
        return [str(exc)], []
    errors: list[str] = []
    warnings: list[str] = []
    required = {'molecule_id', 'smiles', 'library_id', 'input_order'}
    for row in rows:
        missing = [k for k in required if k not in row or row[k] in {None, ''}]
        if missing:
            errors.append(f'INPUT_SCHEMA_INVALID:{missing}')
            break
    return errors, warnings


def validate_pair_evidence_no_verdict(path: str | Path) -> tuple[list[str], list[str]]:
    rows = read_records_table(path)
    forbidden = {'verdict_layer0', 'verdict_layer1', 'verdict_layer2', 'verdict_final', 'reason_code'}
    errors = []
    if rows:
        overlap = forbidden & set(rows[0].keys())
        if overlap:
            errors.append(f'PAIR_EVIDENCE_ROW_UNIT_LEAK:{sorted(overlap)}')
    return errors, []


def validate_eval_report_no_verdict(eval_report: dict[str, Any]) -> tuple[list[str], list[str]]:
    forbidden = {'cap_batch_verdict', 'cap_batch_reason_code', 'verdict_layer0', 'verdict_layer1', 'verdict_layer2', 'verdict_final'}
    overlap = forbidden & set(eval_report.keys())
    return ([f'EVAL_REPORT_VERDICT_LEAK:{sorted(overlap)}'] if overlap else [], [])


def _load_rows(source: str | Path | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(source, list):
        return source
    return read_records_table(source)


def _load_json_payload(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return source
    payload = Path(source).read_text(encoding='utf-8')
    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        raise TypeError(f'Expected object payload, got {type(loaded).__name__}')
    return loaded


def validate_theta_rule1_runtime_table(
    runtime_table: ThetaRule1RuntimeTable,
    *,
    config: TargetConfig,
    config_path: str | Path | None = None,
    resolution_trace: dict[str, Any] | None = None,
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    diagnostics: dict[str, Any] = {
        'table_id': runtime_table.table_id,
        'table_version': runtime_table.table_version,
        'table_digest': runtime_table.table_digest,
        'table_source': runtime_table.table_source,
        'runtime_contract': runtime_table.runtime_contract,
        'table_status': runtime_table.table_status,
        'current_config_path': None if config_path is None else str(Path(config_path).resolve()),
        'current_config_role': config.config_role,
        'current_target_name': config.target_name,
        'current_pathway': config.pathway,
        'calibration_metadata': dict(runtime_table.calibration_metadata),
    }
    if resolution_trace is not None:
        diagnostics.update({
            'resolution_candidates': list(resolution_trace.get('resolution_candidates', [])),
            'resolved_lookup_key': resolution_trace.get('resolved_lookup_key'),
            'resolution_status': resolution_trace.get('resolution_status'),
            'theta_rule1': resolution_trace.get('theta_rule1'),
        })

    if runtime_table.table_id.startswith('builtin:'):
        diagnostics['validator_errors'] = []
        diagnostics['validator_warnings'] = []
        return errors, warnings, diagnostics

    benchmark_path_raw = runtime_table.calibration_metadata.get('benchmark_config_path')
    benchmark_hash_expected = runtime_table.calibration_metadata.get('benchmark_config_hash')
    benchmark_path = Path(str(benchmark_path_raw)).resolve()
    diagnostics['benchmark_config_path_resolved'] = str(benchmark_path)

    if not benchmark_path.exists():
        errors.append('THETA_RULE1_PROVENANCE_CONFIG_MISSING')
        diagnostics['benchmark_config_loaded'] = False
    else:
        diagnostics['benchmark_config_loaded'] = True
        benchmark_config = load_target_config(benchmark_path)
        benchmark_hash_observed = compute_config_hash(benchmark_config)
        diagnostics['benchmark_config_hash_observed'] = benchmark_hash_observed
        diagnostics['benchmark_config_role_observed'] = benchmark_config.config_role
        if benchmark_config.config_role != 'benchmark':
            errors.append('THETA_RULE1_PROVENANCE_ROLE_MISMATCH')
        if benchmark_hash_expected is not None and benchmark_hash_observed != str(benchmark_hash_expected):
            errors.append('THETA_RULE1_PROVENANCE_HASH_MISMATCH')

        scope_mismatch_fields: list[str] = []
        if benchmark_config.target_name != config.target_name:
            scope_mismatch_fields.append('target_name')
        if benchmark_config.pathway != config.pathway:
            scope_mismatch_fields.append('pathway')
        diagnostics['scope_mismatch_fields'] = scope_mismatch_fields
        if scope_mismatch_fields:
            errors.append(f'THETA_RULE1_SCOPE_MISMATCH:{scope_mismatch_fields}')

    resolution_status = diagnostics.get('resolution_status')
    if resolution_status == 'missing_lookup':
        errors.append('THETA_RULE1_SCOPE_MISMATCH:NO_MATCHING_LOOKUP_KEY')
    elif resolution_status == 'pathway_fallback':
        warnings.append('THETA_RULE1_LOOKUP_PATHWAY_FALLBACK')
    elif resolution_status == 'default_fallback':
        warnings.append('THETA_RULE1_LOOKUP_DEFAULT_FALLBACK')

    diagnostics['validator_errors'] = sorted(set(errors))
    diagnostics['validator_warnings'] = sorted(set(warnings))
    return sorted(set(errors)), sorted(set(warnings)), diagnostics


def validate_cap_truth_source_reconciliation(
    *,
    cap_batch_eval_source: str | Path | dict[str, Any],
    eval_report_source: str | Path | dict[str, Any] | None = None,
    qc_report_source: str | Path | dict[str, Any] | None = None,
    collapse_figure_spec_source: str | Path | dict[str, Any] | None = None,
    replay_audit_source: str | Path | dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    cap_payload = _load_json_payload(cap_batch_eval_source)
    provenance = build_cap_truth_source_provenance(
        cap_payload if isinstance(cap_batch_eval_source, dict) else cap_batch_eval_source
    )

    if not provenance['cap_truth_source_layer_consistency']:
        errors.append('CAP_TRUTH_SOURCE_LAYER_MISMATCH')
    if provenance['cap_truth_source_status'] != 'verified':
        errors.append('CAP_TRUTH_SOURCE_NOT_VERIFIED')

    report_sources = {
        'eval_report': eval_report_source,
        'qc_report': qc_report_source,
        'collapse_figure_spec': collapse_figure_spec_source,
        'replay_audit': replay_audit_source,
    }
    for label, source in report_sources.items():
        if source is None:
            continue
        payload = _load_json_payload(source)
        missing = [key for key in CAP_TRUTH_SOURCE_REQUIRED_FIELDS if key not in payload]
        if missing:
            errors.append(f'CAP_TRUTH_SOURCE_FIELDS_MISSING:{label}:{missing}')
            continue
        for key in CAP_TRUTH_SOURCE_REQUIRED_FIELDS:
            if payload.get(key) != provenance.get(key):
                errors.append(f'CAP_TRUTH_SOURCE_MISMATCH:{label}:{key}')
        if payload.get('run_id') != provenance.get('cap_truth_source_run_id'):
            errors.append(f'CAP_TRUTH_SOURCE_RUN_ID_MISMATCH:{label}')
        if payload.get('cap_truth_source_layer_consistency') is not True:
            errors.append(f'CAP_TRUTH_SOURCE_LAYER_MISMATCH:{label}')

    if cap_payload.get('diagnostics_json', {}).get('layer2') is None and cap_payload.get('verdict_layer2') not in {None, 'UNCLEAR'}:
        warnings.append('CAP_TRUTH_SOURCE_LAYER2_DIAGNOSTICS_MISSING')

    return sorted(set(errors)), sorted(set(warnings))


def validate_mapping_table_invariants(
    source: str | Path | list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    rows = _load_rows(source)
    errors: list[str] = []
    warnings: list[str] = []
    required = {
        'canonical_link_id', 'molecule_id', 'target_id', 'condition_hash',
        'functional_score', 'comb', 'P_hit', 'PAS', 'dist', 'LPCS', 'PCF',
        'pairing_role', 'functional_score_dictionary_id',
    }
    seen_links: set[str] = set()
    forbidden = {
        'shuffle_donor_pool_hash', 'donor_plan_hash',
        'verdict_layer0', 'verdict_layer1', 'verdict_layer2', 'verdict_final',
        'cap_batch_verdict', 'cap_batch_reason_code',
    }
    for row in rows:
        missing = sorted(key for key in required if key not in row)
        if missing:
            errors.append(f'CAP_MAPPING_MISSING_COLUMNS:{missing}')
            break
        if row.get('pairing_role') != 'native':
            errors.append(f'CAP_MAPPING_ROLE_INVALID:{row.get("pairing_role")!r}')
        link_id = str(row.get('canonical_link_id'))
        if link_id in seen_links:
            errors.append(f'CAP_MAPPING_DUPLICATE_CANONICAL_LINK:{link_id}')
        seen_links.add(link_id)
        overlap = forbidden & set(row)
        if overlap:
            errors.append(f'CAP_MAPPING_ROW_UNIT_LEAK:{sorted(overlap)}')
        if row.get('functional_score_dictionary_id') != 'functional-score-dict-v1':
            errors.append(
                f'CAP_MAPPING_FUNCTIONAL_SCORE_DICT_INVALID:{row.get("functional_score_dictionary_id")!r}'
            )
    return sorted(set(errors)), warnings


def validate_falsification_table_invariants(
    source: str | Path | list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    rows = _load_rows(source)
    errors: list[str] = []
    warnings: list[str] = []
    required = {
        'canonical_link_id', 'molecule_id', 'target_id', 'condition_hash',
        'functional_score', 'comb', 'P_hit', 'PAS', 'dist', 'LPCS', 'PCF',
        'pairing_role', 'shuffle_donor_pool_hash', 'donor_plan_hash',
        'functional_score_dictionary_id',
    }
    seen_links: set[str] = set()
    forbidden = {
        'verdict_layer0', 'verdict_layer1', 'verdict_layer2', 'verdict_final',
        'cap_batch_verdict', 'cap_batch_reason_code',
    }
    for row in rows:
        missing = sorted(key for key in required if key not in row)
        if missing:
            errors.append(f'CAP_FALSIFICATION_MISSING_COLUMNS:{missing}')
            break
        if row.get('pairing_role') != 'matched_falsification':
            errors.append(f'CAP_FALSIFICATION_ROLE_INVALID:{row.get("pairing_role")!r}')
        link_id = str(row.get('canonical_link_id'))
        if link_id in seen_links:
            errors.append(f'CAP_FALSIFICATION_DUPLICATE_CANONICAL_LINK:{link_id}')
        seen_links.add(link_id)
        overlap = forbidden & set(row)
        if overlap:
            errors.append(f'CAP_FALSIFICATION_ROW_UNIT_LEAK:{sorted(overlap)}')
        if row.get('functional_score_dictionary_id') != 'functional-score-dict-v1':
            errors.append(
                f'CAP_FALSIFICATION_FUNCTIONAL_SCORE_DICT_INVALID:{row.get("functional_score_dictionary_id")!r}'
            )
    return sorted(set(errors)), warnings


def validate_cap_batch_eval_invariants(
    source: str | Path | dict[str, Any],
) -> tuple[list[str], list[str]]:
    payload = _load_json_payload(source)
    errors: list[str] = []
    warnings: list[str] = []
    allowed_verdicts = {'PASS', 'FAIL', 'UNCLEAR', None}
    required = {'run_id', 'status', 'source_of_truth', 'diagnostics_json', 'reason_codes'}
    missing = sorted(key for key in required if key not in payload)
    if missing:
        errors.append(f'CAP_BATCH_EVAL_MISSING_KEYS:{missing}')
        return errors, warnings
    if payload.get('source_of_truth') is not True:
        errors.append('CAP_BATCH_EVAL_TRUTH_SOURCE_FALSE')
    if payload.get('verdict_final') != payload.get('cap_batch_verdict'):
        errors.append('CAP_BATCH_EVAL_VERDICT_FINAL_MISMATCH')
    for key in ('cap_batch_verdict', 'verdict_layer0', 'verdict_layer1', 'verdict_layer2', 'verdict_final'):
        if payload.get(key) not in allowed_verdicts:
            errors.append(f'CAP_BATCH_EVAL_VERDICT_INVALID:{key}:{payload.get(key)!r}')
    reason_codes = payload.get('reason_codes')
    if not isinstance(reason_codes, list):
        errors.append('CAP_BATCH_EVAL_REASON_CODES_NOT_LIST')
        reason_codes = []
    primary_reason = payload.get('cap_batch_reason_code')
    if primary_reason is not None and primary_reason not in reason_codes:
        errors.append('CAP_BATCH_EVAL_PRIMARY_REASON_NOT_IN_REASON_CODES')
    verdict = payload.get('cap_batch_verdict')
    if verdict == 'PASS' and primary_reason is not None:
        errors.append('CAP_BATCH_EVAL_PASS_WITH_REASON_CODE')
    if verdict in {'FAIL', 'UNCLEAR'} and primary_reason is None:
        warnings.append('CAP_BATCH_EVAL_NONPASS_WITHOUT_PRIMARY_REASON')
    return sorted(set(errors)), sorted(set(warnings))


def validate_cap_artifact_invariants(
    *,
    mapping_source: str | Path | list[dict[str, Any]] | None = None,
    falsification_source: str | Path | list[dict[str, Any]] | None = None,
    cap_batch_eval_source: str | Path | dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    mapping_rows: list[dict[str, Any]] | None = None
    fals_rows: list[dict[str, Any]] | None = None

    if mapping_source is not None:
        mapping_rows = _load_rows(mapping_source)
        e, w = validate_mapping_table_invariants(mapping_rows)
        errors.extend(e)
        warnings.extend(w)

    if falsification_source is not None:
        fals_rows = _load_rows(falsification_source)
        e, w = validate_falsification_table_invariants(fals_rows)
        errors.extend(e)
        warnings.extend(w)

    if cap_batch_eval_source is not None:
        e, w = validate_cap_batch_eval_invariants(cap_batch_eval_source)
        errors.extend(e)
        warnings.extend(w)

    if mapping_rows is not None and fals_rows is not None and mapping_rows and fals_rows:
        mapping_ids = {str(row['canonical_link_id']) for row in mapping_rows}
        fals_ids = {str(row['canonical_link_id']) for row in fals_rows}
        if mapping_ids != fals_ids:
            errors.append('CAP_ARTIFACT_FOLD_MAP_MISMATCH')

    return sorted(set(errors)), sorted(set(warnings))
