from __future__ import annotations

from typing import Any

from crisp.config.models import ComparisonType, normalize_comparison_type

VALID_COMPARISON_TYPE_SOURCES = frozenset({
    "config_role_default",
    "explicit_override",
})
VALID_PATHYES_MODES = frozenset({
    "bootstrap",
    "pat-backed",
})
VALID_PATHYES_DIAGNOSTICS_STATUSES = frozenset({
    "bootstrap",
    "loaded",
    "missing",
    "invalid",
})
VALID_RULE1_APPLICABILITY = frozenset({
    "PATH_EVALUABLE",
    "PATH_NOT_EVALUABLE",
})
_SEVERITY_ORDER = {
    "warning": 1,
    "recoverable": 2,
    "fatal": 3,
}


def normalize_skip_reason_codes(values: list[Any] | None) -> list[str]:
    if values is None:
        return []
    return list(dict.fromkeys(str(value) for value in values))


def normalize_inventory_json_errors(
    values: list[dict[str, Any]] | list[Any] | None,
) -> list[dict[str, str]]:
    if values is None:
        return []
    normalized: list[dict[str, str]] = []
    for value in values:
        if isinstance(value, dict):
            code = str(value.get("code") or "UNKNOWN_JSON_ERROR")
            severity = str(value.get("severity") or "warning").lower()
            message = str(value.get("message") or code)
        else:
            code = str(value)
            severity = "warning"
            message = str(value)
        if severity not in _SEVERITY_ORDER:
            severity = "warning"
        normalized.append({
            "code": code,
            "severity": severity,
            "message": message,
        })
    return normalized


def inventory_json_max_severity(values: list[dict[str, Any]] | list[Any] | None) -> str:
    normalized = normalize_inventory_json_errors(values)
    if not normalized:
        return "none"
    return max(
        (item["severity"] for item in normalized),
        key=lambda severity: _SEVERITY_ORDER.get(severity, 0),
    )


def inventory_json_audit_status(values: list[dict[str, Any]] | list[Any] | None) -> str:
    max_severity = inventory_json_max_severity(values)
    if max_severity == "fatal":
        return "AUDIT_BLOCKED"
    if max_severity in {"recoverable", "warning"}:
        return "AUDIT_CONTINUABLE"
    return "AUDIT_READY"


def resolve_report_comparison_metadata(
    *,
    manifest: dict[str, Any],
    completion_basis: dict[str, Any],
) -> tuple[str | None, str | None]:
    raw_type = completion_basis.get("comparison_type")
    if raw_type is not None:
        try:
            comparison_type = normalize_comparison_type(str(raw_type)).value
            raw_source = completion_basis.get("comparison_type_source")
            if raw_source in VALID_COMPARISON_TYPE_SOURCES:
                return comparison_type, str(raw_source)
            return comparison_type, "explicit_override"
        except ValueError:
            pass

    role = manifest.get("target_config_role")
    if role == "benchmark":
        return ComparisonType.SAME_CONFIG.value, "config_role_default"
    if role in {"lowsampling", "smoke", "production"}:
        return ComparisonType.CROSS_REGIME.value, "config_role_default"
    return None, None


def resolve_report_pathyes_metadata(*, completion_basis: dict[str, Any]) -> dict[str, Any]:
    raw_requested_mode = completion_basis.get("pathyes_mode_requested")
    raw_resolved_mode = completion_basis.get("pathyes_mode_resolved")
    raw_diagnostics_status = completion_basis.get("pathyes_diagnostics_status")
    raw_rule1_applicability = completion_basis.get("pathyes_rule1_applicability")
    raw_goal_precheck = completion_basis.get("pathyes_goal_precheck_passed")

    return {
        "pathyes_mode_requested": (
            str(raw_requested_mode) if raw_requested_mode in VALID_PATHYES_MODES else None
        ),
        "pathyes_mode_resolved": (
            str(raw_resolved_mode) if raw_resolved_mode in VALID_PATHYES_MODES else None
        ),
        "pathyes_state_source": (
            None
            if completion_basis.get("pathyes_state_source") is None
            else str(completion_basis.get("pathyes_state_source"))
        ),
        "pathyes_diagnostics_status": (
            str(raw_diagnostics_status)
            if raw_diagnostics_status in VALID_PATHYES_DIAGNOSTICS_STATUSES
            else None
        ),
        "pathyes_diagnostics_error_code": (
            None
            if completion_basis.get("pathyes_diagnostics_error_code") is None
            else str(completion_basis.get("pathyes_diagnostics_error_code"))
        ),
        "pathyes_diagnostics_source": (
            None
            if completion_basis.get("pathyes_diagnostics_source") is None
            else str(completion_basis.get("pathyes_diagnostics_source"))
        ),
        "pathyes_goal_precheck_passed": (
            raw_goal_precheck if isinstance(raw_goal_precheck, bool) else None
        ),
        "pathyes_rule1_applicability": (
            str(raw_rule1_applicability)
            if raw_rule1_applicability in VALID_RULE1_APPLICABILITY
            else None
        ),
        "pathyes_skip_code": (
            None
            if completion_basis.get("pathyes_skip_code") is None
            else str(completion_basis.get("pathyes_skip_code"))
        ),
    }


def build_report_contract_fields(
    *,
    comparison_type: str | None = None,
    comparison_type_source: str | None = None,
    skip_reason_codes: list[Any] | None = None,
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
) -> dict[str, Any]:
    provenance = {} if cap_truth_source_provenance is None else dict(cap_truth_source_provenance)
    return {
        "comparison_type": comparison_type,
        "comparison_type_source": (
            comparison_type_source
            if comparison_type_source in VALID_COMPARISON_TYPE_SOURCES
            else None
        ),
        "skip_reason_codes": normalize_skip_reason_codes(skip_reason_codes),
        "inventory_json_errors": normalize_inventory_json_errors(inventory_json_errors),
        "cap_truth_source_path": provenance.get("cap_truth_source_path"),
        "cap_truth_source_digest": provenance.get("cap_truth_source_digest"),
        "cap_truth_source_run_id": provenance.get("cap_truth_source_run_id"),
        "cap_truth_source_keys": list(provenance.get("cap_truth_source_keys", [])),
        "cap_truth_source_layer_consistency": (
            provenance.get("cap_truth_source_layer_consistency")
            if isinstance(provenance.get("cap_truth_source_layer_consistency"), bool)
            else None
        ),
        "cap_truth_source_status": provenance.get("cap_truth_source_status"),
        "pathyes_mode_requested": (
            pathyes_mode_requested if pathyes_mode_requested in VALID_PATHYES_MODES else None
        ),
        "pathyes_mode_resolved": (
            pathyes_mode_resolved if pathyes_mode_resolved in VALID_PATHYES_MODES else None
        ),
        "pathyes_state_source": pathyes_state_source,
        "pathyes_diagnostics_status": (
            pathyes_diagnostics_status
            if pathyes_diagnostics_status in VALID_PATHYES_DIAGNOSTICS_STATUSES
            else None
        ),
        "pathyes_diagnostics_error_code": pathyes_diagnostics_error_code,
        "pathyes_diagnostics_source": pathyes_diagnostics_source,
        "pathyes_goal_precheck_passed": (
            pathyes_goal_precheck_passed
            if isinstance(pathyes_goal_precheck_passed, bool)
            else None
        ),
        "pathyes_rule1_applicability": (
            pathyes_rule1_applicability
            if pathyes_rule1_applicability in VALID_RULE1_APPLICABILITY
            else None
        ),
        "pathyes_skip_code": pathyes_skip_code,
    }
