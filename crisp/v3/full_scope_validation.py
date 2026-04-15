from __future__ import annotations

from typing import Any, Mapping

from crisp.v3.contracts import SCVObservationBundle
from crisp.v3.migration_scope import (
    get_comparator_scope,
    get_internal_full_scv_channel,
    get_mapping_status,
    required_scv_components,
    scope_allows_full_verdict_aggregation,
)

FULL_SCOPE_VALIDATION_SCHEMA_VERSION = "crisp.v3.full_scope_validation/v1"
FULL_SCOPE_DENOMINATOR_SEMANTICS = {
    "coverage_drift_rate": "all_compounds",
    "applicability_drift_rate": "all_compounds",
    "verdict_match_rate": "full_verdict_comparable_subset",
    "verdict_mismatch_rate": "full_verdict_comparable_subset",
    "path_component_match_rate": "component_verdict_comparable_subset",
}


def build_full_scope_validation_payload(
    *,
    comparator_scope: str,
    comparable_channels: tuple[str, ...],
    v3_only_evidence_channels: tuple[str, ...],
    comparison_summary_payload: Mapping[str, Any] | None,
    run_drift_report_payload: Mapping[str, Any] | None,
    internal_full_scv_bundle: SCVObservationBundle | Mapping[str, Any] | None,
) -> dict[str, Any]:
    normalized_scope = get_comparator_scope(comparator_scope)
    required_components = required_scv_components()
    internal_component_channels = {
        component_name: get_internal_full_scv_channel(component_name)
        for component_name in required_components
    }
    mapping_status = {
        component_name: get_mapping_status(component_name)
        for component_name in required_components
    }
    observed_internal_channels = _observed_internal_channels(internal_full_scv_bundle)
    present_required_components = tuple(
        component_name
        for component_name in required_components
        if internal_component_channels[component_name] in observed_internal_channels
    )
    missing_required_components = tuple(
        component_name
        for component_name in required_components
        if component_name not in present_required_components
    )
    required_component_coverage_complete = not missing_required_components
    all_required_mappings_frozen = all(status == "FROZEN" for status in mapping_status.values())
    full_verdict_denominator_ready = all_required_mappings_frozen and required_component_coverage_complete

    summary_scope = _mapping_str(comparison_summary_payload, "comparison_scope")
    summary_comparable_channels = _mapping_tuple(comparison_summary_payload, "comparable_channels")
    summary_component_match_keys = _mapping_keys(comparison_summary_payload, "component_matches")
    run_report_scope = _mapping_str(run_drift_report_payload, "comparator_scope")
    run_report_comparable_channels = _mapping_tuple(run_drift_report_payload, "comparable_channels")
    verdict_match_rate = _mapping_value(run_drift_report_payload, "verdict_match_rate")
    verdict_mismatch_rate = _mapping_value(run_drift_report_payload, "verdict_mismatch_rate")
    path_component_match_rate = _mapping_value(run_drift_report_payload, "path_component_match_rate")
    cross_artifact_consistent = (
        summary_scope == normalized_scope
        and run_report_scope == normalized_scope
        and summary_comparable_channels == comparable_channels
        and run_report_comparable_channels == comparable_channels
    )
    verdict_rate_inactive = verdict_match_rate is None and verdict_mismatch_rate is None
    path_component_rate_retained = (
        verdict_match_rate is None
        or path_component_match_rate is None
        or path_component_match_rate != verdict_match_rate
    )
    return {
        "schema_version": FULL_SCOPE_VALIDATION_SCHEMA_VERSION,
        "comparator_scope": normalized_scope,
        "comparable_channels": list(comparable_channels),
        "v3_only_evidence_channels": list(v3_only_evidence_channels),
        "required_scv_components": list(required_components),
        "mapping_status": mapping_status,
        "internal_component_channels": internal_component_channels,
        "observed_internal_channels": list(observed_internal_channels),
        "present_required_components": list(present_required_components),
        "missing_required_components": list(missing_required_components),
        "required_component_coverage_complete": required_component_coverage_complete,
        "all_required_mappings_frozen": all_required_mappings_frozen,
        "full_verdict_denominator_ready": full_verdict_denominator_ready,
        "scope_allows_full_verdict_aggregation": scope_allows_full_verdict_aggregation(normalized_scope),
        "summary_scope": summary_scope,
        "summary_comparable_channels": list(summary_comparable_channels),
        "summary_component_match_keys": list(summary_component_match_keys),
        "run_report_scope": run_report_scope,
        "run_report_comparable_channels": list(run_report_comparable_channels),
        "cross_artifact_consistent": cross_artifact_consistent,
        "verdict_rate_inactive": verdict_rate_inactive,
        "path_component_rate_retained": path_component_rate_retained,
        "denominator_semantics": dict(FULL_SCOPE_DENOMINATOR_SEMANTICS),
    }


def audit_full_scope_validation_payload(
    *,
    payload: Mapping[str, Any],
    comparator_scope: str,
    comparable_channels: tuple[str, ...],
    v3_only_evidence_channels: tuple[str, ...],
    comparison_summary_payload: Mapping[str, Any] | None,
    run_drift_report_payload: Mapping[str, Any] | None,
    internal_full_scv_bundle: Mapping[str, Any] | SCVObservationBundle | None,
) -> tuple[str, ...]:
    findings: list[str] = []
    expected_payload = build_full_scope_validation_payload(
        comparator_scope=comparator_scope,
        comparable_channels=comparable_channels,
        v3_only_evidence_channels=v3_only_evidence_channels,
        comparison_summary_payload=comparison_summary_payload,
        run_drift_report_payload=run_drift_report_payload,
        internal_full_scv_bundle=internal_full_scv_bundle,
    )
    for field_name in (
        "comparator_scope",
        "comparable_channels",
        "v3_only_evidence_channels",
        "required_scv_components",
        "mapping_status",
        "internal_component_channels",
        "observed_internal_channels",
        "present_required_components",
        "missing_required_components",
        "required_component_coverage_complete",
        "all_required_mappings_frozen",
        "full_verdict_denominator_ready",
        "scope_allows_full_verdict_aggregation",
        "summary_scope",
        "summary_comparable_channels",
        "summary_component_match_keys",
        "run_report_scope",
        "run_report_comparable_channels",
        "cross_artifact_consistent",
        "verdict_rate_inactive",
        "path_component_rate_retained",
        "denominator_semantics",
    ):
        if _normalized_field_value(field_name, payload.get(field_name)) != _normalized_field_value(
            field_name,
            expected_payload.get(field_name),
        ):
            findings.append(f"P3 {field_name} mismatch")
    return tuple(findings)


def _observed_internal_channels(
    bundle: SCVObservationBundle | Mapping[str, Any] | None,
) -> tuple[str, ...]:
    if bundle is None:
        return ()
    if isinstance(bundle, Mapping):
        observations = bundle.get("observations")
        if not isinstance(observations, list):
            return ()
        return tuple(
            sorted(
                str(observation.get("channel_name"))
                for observation in observations
                if isinstance(observation, Mapping) and observation.get("channel_name") is not None
            )
        )
    return tuple(sorted(str(observation.channel_name) for observation in bundle.observations))


def _mapping_str(payload: Mapping[str, Any] | None, field_name: str) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    value = payload.get(field_name)
    return None if value is None else str(value)


def _mapping_tuple(payload: Mapping[str, Any] | None, field_name: str) -> tuple[str, ...]:
    if not isinstance(payload, Mapping):
        return ()
    value = payload.get(field_name)
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value)


def _mapping_keys(payload: Mapping[str, Any] | None, field_name: str) -> tuple[str, ...]:
    if not isinstance(payload, Mapping):
        return ()
    value = payload.get(field_name)
    if not isinstance(value, Mapping):
        return ()
    return tuple(sorted(str(key) for key in value.keys()))


def _mapping_value(payload: Mapping[str, Any] | None, field_name: str) -> Any:
    if not isinstance(payload, Mapping):
        return None
    return payload.get(field_name)


def _normalized_field_value(field_name: str, value: Any) -> Any:
    tuple_fields = {
        "comparable_channels",
        "v3_only_evidence_channels",
        "required_scv_components",
        "observed_internal_channels",
        "present_required_components",
        "missing_required_components",
        "summary_comparable_channels",
        "summary_component_match_keys",
        "run_report_comparable_channels",
    }
    dict_fields = {
        "mapping_status",
        "internal_component_channels",
        "denominator_semantics",
    }
    if field_name in tuple_fields:
        if not isinstance(value, (list, tuple)):
            return ()
        return tuple(str(item) for item in value)
    if field_name in dict_fields:
        if not isinstance(value, Mapping):
            return {}
        return {str(key): str(item) for key, item in value.items()}
    return value
