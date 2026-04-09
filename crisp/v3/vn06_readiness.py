from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from crisp.v3.policy import VERDICT_RECORD_SCHEMA_VERSION, VN06_READINESS_SCHEMA_VERSION

VN06_READINESS_ARTIFACT = "vn06_readiness.json"
VN06_M1_SOAK_WINDOW_SIZE = 30
VN06_M2_TRIGGER_GATES = ("VN-01", "VN-02", "VN-03", "VN-04", "VN-05", "VN-06")


@dataclass(frozen=True, slots=True)
class VerdictRecordAuthorityFieldSpec:
    source_field: str
    target_field: str
    comparison_mode: str
    mismatch_severity: str
    source_path: tuple[str, ...] = ()
    expected_current_scope_value: Any = None
    current_scope_invariant: bool = False
    default_when_comparator_disabled: Any = None


VERDICT_RECORD_M1_AUTHORITY_FIELD_MAP = (
    VerdictRecordAuthorityFieldSpec(
        source_field="run_id",
        target_field="run_id",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        source_path=("run_id",),
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="output_root",
        target_field="output_root",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        source_path=("output_root",),
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="semantic_policy_version",
        target_field="semantic_policy_version",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        source_path=("semantic_policy_version",),
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="comparator_scope",
        target_field="comparator_scope",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        source_path=("comparator_scope",),
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="comparable_channels",
        target_field="comparable_channels",
        comparison_mode="set-equal",
        mismatch_severity="hard-block",
        source_path=("comparable_channels",),
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="v3_only_evidence_channels",
        target_field="v3_only_evidence_channels",
        comparison_mode="set-equal",
        mismatch_severity="hard-block",
        source_path=("v3_only_evidence_channels",),
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="channel_lifecycle_states",
        target_field="channel_lifecycle_states",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        source_path=("channel_lifecycle_states",),
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.full_verdict_computable",
        target_field="full_verdict_computable",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "full_verdict_computable",
        ),
        default_when_comparator_disabled=False,
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.full_verdict_comparable_count",
        target_field="full_verdict_comparable_count",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "full_verdict_comparable_count",
        ),
        default_when_comparator_disabled=0,
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.verdict_match_rate",
        target_field="verdict_match_rate",
        comparison_mode="nullable-exact",
        mismatch_severity="hard-block",
        source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "verdict_match_rate",
        ),
        default_when_comparator_disabled=None,
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.verdict_mismatch_rate",
        target_field="verdict_mismatch_rate",
        comparison_mode="nullable-exact",
        mismatch_severity="hard-block",
        source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "verdict_mismatch_rate",
        ),
        default_when_comparator_disabled=None,
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.path_component_match_rate",
        target_field="path_component_match_rate",
        comparison_mode="nullable-exact",
        mismatch_severity="hard-block",
        source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "path_component_match_rate",
        ),
        default_when_comparator_disabled=None,
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="current-scope invariant: v3_shadow_verdict must remain null during M-1",
        target_field="v3_shadow_verdict",
        comparison_mode="nullable-exact",
        mismatch_severity="hard-block",
        expected_current_scope_value=None,
        current_scope_invariant=True,
    ),
    VerdictRecordAuthorityFieldSpec(
        source_field="current-scope invariant: authority transfer must remain not executed during M-1",
        target_field="authority_transfer_complete",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        expected_current_scope_value=False,
        current_scope_invariant=True,
    ),
)

VERDICT_RECORD_M1_AUTHORITY_FIELDS = tuple(
    spec.target_field for spec in VERDICT_RECORD_M1_AUTHORITY_FIELD_MAP
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


def _mapping_get(
    payload: Mapping[str, Any],
    path: tuple[str, ...],
) -> tuple[bool, Any]:
    current: Any = payload
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _field_map_payload() -> list[dict[str, str]]:
    return [
        {
            "source_field": spec.source_field,
            "target_field": spec.target_field,
            "comparison_mode": spec.comparison_mode,
            "mismatch_severity": spec.mismatch_severity,
        }
        for spec in VERDICT_RECORD_M1_AUTHORITY_FIELD_MAP
    ]


def _bridge_comparator_enabled(sidecar_run_record: Mapping[str, Any]) -> bool:
    bridge_diagnostics = sidecar_run_record.get("bridge_diagnostics") or {}
    if isinstance(bridge_diagnostics, Mapping):
        explicit = bridge_diagnostics.get("bridge_comparator_enabled")
        if isinstance(explicit, bool):
            return explicit
        return isinstance(bridge_diagnostics.get("bridge_comparison_summary"), Mapping)
    return False


def _normalize_value(*, comparison_mode: str, value: Any) -> Any:
    if comparison_mode == "set-equal":
        if value is None:
            return frozenset()
        if isinstance(value, (list, tuple, set, frozenset)):
            return frozenset(value)
    return value


def _values_match(*, comparison_mode: str, actual_value: Any, expected_value: Any) -> bool:
    return _normalize_value(comparison_mode=comparison_mode, value=actual_value) == _normalize_value(
        comparison_mode=comparison_mode,
        value=expected_value,
    )


def _collect_expected_pairs_and_source_gaps(
    sidecar_run_record: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    expected_pairs: dict[str, Any] = {}
    source_gaps: list[str] = []
    comparator_enabled = _bridge_comparator_enabled(sidecar_run_record)
    for spec in VERDICT_RECORD_M1_AUTHORITY_FIELD_MAP:
        if spec.current_scope_invariant:
            expected_pairs[spec.target_field] = spec.expected_current_scope_value
            continue
        found, expected_value = _mapping_get(sidecar_run_record, spec.source_path)
        if not found:
            if not comparator_enabled and spec.source_path[:3] == (
                "bridge_diagnostics",
                "bridge_comparison_summary",
                "run_drift_report",
            ):
                expected_pairs[spec.target_field] = spec.default_when_comparator_disabled
                continue
            source_gaps.append(spec.target_field)
            continue
        expected_pairs[spec.target_field] = expected_value
    return expected_pairs, tuple(source_gaps)


def build_verdict_record_expected_pairs(sidecar_run_record: Mapping[str, Any]) -> dict[str, Any]:
    expected_pairs, source_gaps = _collect_expected_pairs_and_source_gaps(sidecar_run_record)
    if source_gaps:
        raise ValueError(
            "sidecar_run_record missing verdict_record authority source fields: "
            + ", ".join(source_gaps)
        )
    return expected_pairs


def collect_verdict_record_dual_write_source_gaps(
    *,
    sidecar_run_record: Mapping[str, Any],
) -> tuple[str, ...]:
    _, source_gaps = _collect_expected_pairs_and_source_gaps(sidecar_run_record)
    return source_gaps


def collect_verdict_record_dual_write_mismatches(
    *,
    verdict_record: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
) -> tuple[str, ...]:
    expected_pairs, source_gaps = _collect_expected_pairs_and_source_gaps(sidecar_run_record)
    mismatches: list[str] = [f"source_missing:{target_field}" for target_field in source_gaps]
    for spec in VERDICT_RECORD_M1_AUTHORITY_FIELD_MAP:
        if spec.target_field in source_gaps:
            continue
        if not _values_match(
            comparison_mode=spec.comparison_mode,
            actual_value=verdict_record.get(spec.target_field),
            expected_value=expected_pairs.get(spec.target_field),
        ):
            mismatches.append(str(spec.target_field))
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


def verdict_record_operator_surface_inactive(verdict_record: Mapping[str, Any]) -> bool:
    return (
        verdict_record.get("v3_shadow_verdict") is None
        and verdict_record.get("verdict_match_rate") is None
        and verdict_record.get("verdict_mismatch_rate") is None
    )


def evaluate_vn06_soak_window(
    *,
    readiness_history: Sequence[Mapping[str, Any]],
    required_window_size: int = VN06_M1_SOAK_WINDOW_SIZE,
) -> dict[str, Any]:
    window = list(readiness_history)[-required_window_size:]
    dual_write_mismatch_zero = (
        len(window) >= required_window_size
        and all(int(item.get("dual_write_mismatch_count", 1)) == 0 for item in window)
    )
    manifest_registration_complete = (
        len(window) >= required_window_size
        and all(bool(item.get("manifest_registration_complete")) for item in window)
    )
    schema_complete = (
        len(window) >= required_window_size
        and all(bool(item.get("schema_complete")) for item in window)
    )
    operator_surface_inactive = (
        len(window) >= required_window_size
        and all(bool(item.get("current_run_operator_surface_inactive")) for item in window)
    )
    return {
        "required_window_size": required_window_size,
        "observed_window_size": len(window),
        "required_consecutive_runs": required_window_size,
        "dual_write_mismatch_zero_streak": dual_write_mismatch_zero,
        "manifest_registration_complete_streak": manifest_registration_complete,
        "schema_complete_streak": schema_complete,
        "operator_surface_inactive_streak": operator_surface_inactive,
        "window_passed": (
            dual_write_mismatch_zero
            and manifest_registration_complete
            and schema_complete
            and operator_surface_inactive
        ),
    }


def evaluate_vn06_readiness(
    *,
    verdict_record: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
    manifest_outputs: list[Mapping[str, Any]],
) -> dict[str, Any]:
    schema_missing_fields = verdict_record_schema_missing_fields(verdict_record)
    dual_write_source_gaps = collect_verdict_record_dual_write_source_gaps(
        sidecar_run_record=sidecar_run_record,
    )
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
    current_run_operator_surface_inactive = verdict_record_operator_surface_inactive(verdict_record)
    current_run_passes_m1_soak_conditions = (
        schema_complete
        and not dual_write_mismatches
        and manifest_registration_complete
        and current_run_operator_surface_inactive
    )
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
        "m1_authority_field_map": _field_map_payload(),
        "m1_authority_source_map_complete": not dual_write_source_gaps,
        "m1_authority_source_gaps": list(dual_write_source_gaps),
        "schema_complete": schema_complete,
        "schema_missing_fields": list(schema_missing_fields),
        "dual_write_mismatches": list(dual_write_mismatches),
        "dual_write_mismatch_count": len(dual_write_mismatches),
        "manifest_registration_complete": manifest_registration_complete,
        "current_run_operator_surface_inactive": current_run_operator_surface_inactive,
        "current_run_passes_m1_soak_conditions": current_run_passes_m1_soak_conditions,
        "m1_soak_requirement": {
            "required_window_size": VN06_M1_SOAK_WINDOW_SIZE,
            "required_consecutive_runs": VN06_M1_SOAK_WINDOW_SIZE,
            "requires_dual_write_mismatch_count": 0,
            "requires_manifest_registration_complete": True,
            "requires_schema_complete": True,
            "requires_operator_surface_inactive": True,
        },
        "authority_transfer_not_yet_executed": authority_transfer_not_yet_executed,
        "authority_transfer_executable": authority_transfer_executable,
        "authority_transfer_requires_separate_m2_decision": True,
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
