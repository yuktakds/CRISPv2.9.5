from __future__ import annotations

from typing import Any, Mapping

from crisp.v3.policy import VERDICT_RECORD_SCHEMA_VERSION, VN06_READINESS_SCHEMA_VERSION

VN06_READINESS_ARTIFACT = "vn06_readiness.json"
VERDICT_RECORD_M1_AUTHORITY_FIELDS = (
    "run_id",
    "output_root",
    "semantic_policy_version",
    "comparator_scope",
    "comparable_channels",
    "v3_only_evidence_channels",
    "channel_lifecycle_states",
    "path_component_match_rate",
)
VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS = (
    "schema_version",
    "run_id",
    "output_root",
    "semantic_policy_version",
    "comparator_scope",
    "comparable_channels",
    "v3_only_evidence_channels",
    "channel_lifecycle_states",
    "full_verdict_computable",
    "full_verdict_comparable_count",
    "verdict_match_rate",
    "verdict_mismatch_rate",
    "path_component_match_rate",
    "v3_shadow_verdict",
    "authority_transfer_complete",
    "sidecar_run_record_artifact",
    "generator_manifest_artifact",
)
VN06_M2_TRIGGER_GATES = ("VN-01", "VN-02", "VN-03", "VN-04", "VN-05", "VN-06")


def _sidecar_run_drift_report(sidecar_run_record: Mapping[str, Any]) -> Mapping[str, Any]:
    bridge_diagnostics = sidecar_run_record.get("bridge_diagnostics") or {}
    bridge_summary = bridge_diagnostics.get("bridge_comparison_summary") or {}
    if not isinstance(bridge_summary, Mapping):
        return {}
    run_drift_report = bridge_summary.get("run_drift_report") or {}
    return run_drift_report if isinstance(run_drift_report, Mapping) else {}


def build_verdict_record_expected_pairs(sidecar_run_record: Mapping[str, Any]) -> dict[str, Any]:
    run_drift_report = _sidecar_run_drift_report(sidecar_run_record)
    return {
        "run_id": sidecar_run_record.get("run_id"),
        "output_root": sidecar_run_record.get("output_root"),
        "semantic_policy_version": sidecar_run_record.get("semantic_policy_version"),
        "comparator_scope": sidecar_run_record.get("comparator_scope"),
        "comparable_channels": list(sidecar_run_record.get("comparable_channels", ())),
        "v3_only_evidence_channels": list(sidecar_run_record.get("v3_only_evidence_channels", ())),
        "channel_lifecycle_states": dict(sidecar_run_record.get("channel_lifecycle_states", {})),
        "path_component_match_rate": run_drift_report.get("path_component_match_rate"),
    }


def collect_verdict_record_dual_write_mismatches(
    *,
    verdict_record: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
) -> tuple[str, ...]:
    mismatches: list[str] = []
    for field_name, expected_value in build_verdict_record_expected_pairs(sidecar_run_record).items():
        if verdict_record.get(field_name) != expected_value:
            mismatches.append(str(field_name))
    if verdict_record.get("authority_transfer_complete") is not False:
        mismatches.append("authority_transfer_complete")
    if verdict_record.get("v3_shadow_verdict") not in (None,):
        mismatches.append("v3_shadow_verdict")
    if verdict_record.get("verdict_match_rate") not in (None,):
        mismatches.append("verdict_match_rate")
    return tuple(mismatches)


def verdict_record_schema_missing_fields(verdict_record: Mapping[str, Any]) -> tuple[str, ...]:
    missing = [
        field_name
        for field_name in VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS
        if field_name not in verdict_record
    ]
    if verdict_record.get("schema_version") != VERDICT_RECORD_SCHEMA_VERSION:
        missing.append("schema_version_mismatch")
    return tuple(missing)


def evaluate_vn06_readiness(
    *,
    verdict_record: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
    manifest_outputs: list[Mapping[str, Any]],
) -> dict[str, Any]:
    schema_missing_fields = verdict_record_schema_missing_fields(verdict_record)
    dual_write_mismatches = collect_verdict_record_dual_write_mismatches(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
    )
    manifest_output_names = {
        str(item.get("relative_path"))
        for item in manifest_outputs
        if isinstance(item, Mapping)
    }
    manifest_registration_complete = "verdict_record.json" in manifest_output_names
    authority_transfer_not_yet_executed = verdict_record.get("authority_transfer_complete") is False
    schema_complete = not schema_missing_fields
    authority_transfer_executable = (
        schema_complete
        and not dual_write_mismatches
        and manifest_registration_complete
        and authority_transfer_not_yet_executed
    )
    return {
        "schema_version": VN06_READINESS_SCHEMA_VERSION,
        "verdict_record_schema_version_required": VERDICT_RECORD_SCHEMA_VERSION,
        "m1_authority_fields": list(VERDICT_RECORD_M1_AUTHORITY_FIELDS),
        "schema_complete": schema_complete,
        "schema_missing_fields": list(schema_missing_fields),
        "dual_write_mismatches": list(dual_write_mismatches),
        "dual_write_mismatch_count": len(dual_write_mismatches),
        "manifest_registration_complete": manifest_registration_complete,
        "authority_transfer_not_yet_executed": authority_transfer_not_yet_executed,
        "authority_transfer_executable": authority_transfer_executable,
        "exact_m2_trigger": {
            "requires_vn_gates": list(VN06_M2_TRIGGER_GATES),
            "requires_dual_write_mismatch_count": 0,
            "requires_manifest_registration_complete": True,
            "requires_human_explicit_decision": True,
        },
        "sidecar_run_record_backward_compatibility": {
            "m1_role": "canonical_layer0_authority",
            "m2_role": "backward_compatible_mirror",
            "retention_policy": "retain through M-2 cutover and keep until explicit removal ADR",
        },
    }
