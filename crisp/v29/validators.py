from __future__ import annotations

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
