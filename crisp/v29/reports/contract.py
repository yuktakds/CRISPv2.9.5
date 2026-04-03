from __future__ import annotations

from typing import Any

from crisp.config.models import ComparisonType, normalize_comparison_type

VALID_COMPARISON_TYPE_SOURCES = frozenset({
    "config_role_default",
    "explicit_override",
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


def build_report_contract_fields(
    *,
    comparison_type: str | None = None,
    comparison_type_source: str | None = None,
    skip_reason_codes: list[Any] | None = None,
    inventory_json_errors: list[dict[str, Any]] | list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "comparison_type": comparison_type,
        "comparison_type_source": (
            comparison_type_source
            if comparison_type_source in VALID_COMPARISON_TYPE_SOURCES
            else None
        ),
        "skip_reason_codes": normalize_skip_reason_codes(skip_reason_codes),
        "inventory_json_errors": normalize_inventory_json_errors(inventory_json_errors),
    }
