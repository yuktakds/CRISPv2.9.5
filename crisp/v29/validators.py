from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crisp.v29.inputs import load_molecule_rows
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
