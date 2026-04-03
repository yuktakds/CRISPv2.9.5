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
    pathyes_mode_requested: str | None = None,
    pathyes_mode_resolved: str | None = None,
    pathyes_state_source: str | None = None,
    pathyes_diagnostics_status: str | None = None,
    pathyes_diagnostics_error_code: str | None = None,
    pathyes_diagnostics_source: str | None = None,
    pathyes_goal_precheck_passed: bool | None = None,
    pathyes_rule1_applicability: str | None = None,
    pathyes_skip_code: str | None = None,
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
        pathyes_mode_requested=pathyes_mode_requested,
        pathyes_mode_resolved=pathyes_mode_resolved,
        pathyes_state_source=pathyes_state_source,
        pathyes_diagnostics_status=pathyes_diagnostics_status,
        pathyes_diagnostics_error_code=pathyes_diagnostics_error_code,
        pathyes_diagnostics_source=pathyes_diagnostics_source,
        pathyes_goal_precheck_passed=pathyes_goal_precheck_passed,
        pathyes_rule1_applicability=pathyes_rule1_applicability,
        pathyes_skip_code=pathyes_skip_code,
    ))
    if extra:
        payload.update(extra)
    return payload
