from __future__ import annotations

from typing import Any

from .contract import build_report_contract_fields


def build_qc_report(
    *,
    run_id: str,
    conditions_run: list[str],
    excluded_rows_count: int,
    warnings: list[str],
    result: str,
    comparison_type: str | None = None,
    comparison_type_source: str | None = None,
    skip_reason_codes: list[str] | None = None,
    inventory_json_errors: list[dict[str, Any]] | list[Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        'run_id': run_id,
        'conditions_run': list(conditions_run),
        'excluded_rows_count': int(excluded_rows_count),
        'warnings': list(warnings),
        'result': result,
    }
    payload.update(build_report_contract_fields(
        comparison_type=comparison_type,
        comparison_type_source=comparison_type_source,
        skip_reason_codes=skip_reason_codes,
        inventory_json_errors=inventory_json_errors,
    ))
    if extra:
        payload.update(extra)
    return payload
