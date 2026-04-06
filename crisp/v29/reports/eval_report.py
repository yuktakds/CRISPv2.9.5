from __future__ import annotations

from typing import Any

from crisp.v29.contracts import Layer2Result
from .contract import build_report_contract_fields


def build_eval_report(
    *,
    run_id: str,
    cap_batch_eval_path: str | None,
    layer2_result: Layer2Result | None,
    comparison_type: str | None = None,
    comparison_type_source: str | None = None,
    skip_reason_codes: list[str] | None = None,
    inventory_json_errors: list[dict[str, Any]] | list[Any] | None = None,
    cap_truth_source_provenance: dict[str, Any] | None = None,
    pathyes_mode_requested: str | None = None,
    pathyes_mode_resolved: str | None = None,
    pathyes_state_source: str | None = None,
    pathyes_diagnostics_status: str | None = None,
    pathyes_diagnostics_error_code: str | None = None,
    pathyes_diagnostics_source: str | None = None,
    pathyes_goal_precheck_passed: bool | None = None,
    pathyes_rule1_applicability: str | None = None,
    pathyes_skip_code: str | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'run_id': run_id,
        'cap_batch_eval_path': cap_batch_eval_path,
        'notes': [] if notes is None else list(notes),
    }
    payload.update(build_report_contract_fields(
        comparison_type=comparison_type,
        comparison_type_source=comparison_type_source,
        skip_reason_codes=skip_reason_codes,
        inventory_json_errors=inventory_json_errors,
        cap_truth_source_provenance=cap_truth_source_provenance,
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
    if layer2_result is not None:
        payload['layer2_metrics'] = {
            'status': layer2_result.status,
            'n_rows_mapping': layer2_result.n_rows_mapping,
            'n_rows_falsification': layer2_result.n_rows_falsification,
            'cv_r2_m1_base': layer2_result.cv_r2_m1_base,
            'cv_r2_m1_full': layer2_result.cv_r2_m1_full,
            'cv_r2_m2_base': layer2_result.cv_r2_m2_base,
            'cv_r2_m2_full': layer2_result.cv_r2_m2_full,
            'delta_cv_r2_m1': layer2_result.delta_cv_r2_m1,
            'delta_cv_r2_m2': layer2_result.delta_cv_r2_m2,
            'bootstrap_ci_m1': layer2_result.bootstrap_ci_m1,
            'bootstrap_ci_m2': layer2_result.bootstrap_ci_m2,
            'r_shuffle_joint': layer2_result.r_shuffle_joint,
            'diagnostics_json': layer2_result.diagnostics_json,
        }
    return payload
