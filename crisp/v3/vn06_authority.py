from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    LAYER0_AUTHORITY_MODE,
    M1_LAYER0_AUTHORITY_MODE,
    M1_SIDECAR_RUN_RECORD_ROLE,
    SIDECAR_RUN_RECORD_ARTIFACT,
    SIDECAR_RUN_RECORD_ROLE,
    TRANSFERRED_AUTHORITY_FIELDS,
    extract_sidecar_layer0_authority_mirror,
    sidecar_layer0_authority_artifact,
    sidecar_layer0_authority_mode,
    sidecar_run_record_role,
)
from crisp.v3.policy import VERDICT_RECORD_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class VerdictRecordAuthorityFieldSpec:
    legacy_source_field: str
    target_field: str
    comparison_mode: str
    mismatch_severity: str
    legacy_source_path: tuple[str, ...] = ()
    m1_expected_current_scope_value: Any = None
    m1_current_scope_invariant: bool = False
    default_when_comparator_disabled: Any = None


VERDICT_RECORD_AUTHORITY_FIELD_MAP = (
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="run_id",
        target_field="run_id",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        legacy_source_path=("run_id",),
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="output_root",
        target_field="output_root",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        legacy_source_path=("output_root",),
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="semantic_policy_version",
        target_field="semantic_policy_version",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        legacy_source_path=("semantic_policy_version",),
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="comparator_scope",
        target_field="comparator_scope",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        legacy_source_path=("comparator_scope",),
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="comparable_channels",
        target_field="comparable_channels",
        comparison_mode="set-equal",
        mismatch_severity="hard-block",
        legacy_source_path=("comparable_channels",),
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="v3_only_evidence_channels",
        target_field="v3_only_evidence_channels",
        comparison_mode="set-equal",
        mismatch_severity="hard-block",
        legacy_source_path=("v3_only_evidence_channels",),
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="channel_lifecycle_states",
        target_field="channel_lifecycle_states",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        legacy_source_path=("channel_lifecycle_states",),
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.full_verdict_computable",
        target_field="full_verdict_computable",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        legacy_source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "full_verdict_computable",
        ),
        default_when_comparator_disabled=False,
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.full_verdict_comparable_count",
        target_field="full_verdict_comparable_count",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        legacy_source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "full_verdict_comparable_count",
        ),
        default_when_comparator_disabled=0,
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.verdict_match_rate",
        target_field="verdict_match_rate",
        comparison_mode="nullable-exact",
        mismatch_severity="hard-block",
        legacy_source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "verdict_match_rate",
        ),
        default_when_comparator_disabled=None,
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.verdict_mismatch_rate",
        target_field="verdict_mismatch_rate",
        comparison_mode="nullable-exact",
        mismatch_severity="hard-block",
        legacy_source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "verdict_mismatch_rate",
        ),
        default_when_comparator_disabled=None,
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="bridge_diagnostics.bridge_comparison_summary.run_drift_report.path_component_match_rate",
        target_field="path_component_match_rate",
        comparison_mode="nullable-exact",
        mismatch_severity="hard-block",
        legacy_source_path=(
            "bridge_diagnostics",
            "bridge_comparison_summary",
            "run_drift_report",
            "path_component_match_rate",
        ),
        default_when_comparator_disabled=None,
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="current-scope invariant: v3_shadow_verdict must remain null during M-1",
        target_field="v3_shadow_verdict",
        comparison_mode="nullable-exact",
        mismatch_severity="hard-block",
        m1_expected_current_scope_value=None,
        m1_current_scope_invariant=True,
    ),
    VerdictRecordAuthorityFieldSpec(
        legacy_source_field="current-scope invariant: authority transfer must remain not executed during M-1",
        target_field="authority_transfer_complete",
        comparison_mode="exact",
        mismatch_severity="hard-block",
        m1_expected_current_scope_value=False,
        m1_current_scope_invariant=True,
    ),
)

VERDICT_RECORD_AUTHORITY_FIELDS = tuple(
    spec.target_field for spec in VERDICT_RECORD_AUTHORITY_FIELD_MAP
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


def determine_authority_phase(
    *,
    verdict_record: Mapping[str, Any] | None,
    sidecar_run_record: Mapping[str, Any],
) -> str:
    if verdict_record is not None and verdict_record.get("authority_transfer_complete") is True:
        return LAYER0_AUTHORITY_MODE
    if extract_sidecar_layer0_authority_mirror(sidecar_run_record):
        return LAYER0_AUTHORITY_MODE
    if sidecar_layer0_authority_mode(sidecar_run_record) == LAYER0_AUTHORITY_MODE:
        return LAYER0_AUTHORITY_MODE
    return M1_LAYER0_AUTHORITY_MODE


def field_map_payload(*, authority_phase: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in VERDICT_RECORD_AUTHORITY_FIELD_MAP:
        source_field = spec.legacy_source_field
        if authority_phase == LAYER0_AUTHORITY_MODE:
            source_field = f"bridge_diagnostics.layer0_authority_mirror.{spec.target_field}"
        rows.append(
            {
                "source_field": source_field,
                "target_field": spec.target_field,
                "comparison_mode": spec.comparison_mode,
                "mismatch_severity": spec.mismatch_severity,
            }
        )
    return rows


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
    *,
    sidecar_run_record: Mapping[str, Any],
    verdict_record: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any], tuple[str, ...]]:
    authority_phase = determine_authority_phase(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
    )
    if authority_phase == LAYER0_AUTHORITY_MODE:
        mirror = extract_sidecar_layer0_authority_mirror(sidecar_run_record)
        expected_pairs: dict[str, Any] = {}
        source_gaps: list[str] = []
        for field_name in TRANSFERRED_AUTHORITY_FIELDS:
            if field_name not in mirror:
                source_gaps.append(field_name)
                continue
            expected_pairs[field_name] = mirror.get(field_name)
        return authority_phase, expected_pairs, tuple(source_gaps)

    expected_pairs = {}
    source_gaps = []
    comparator_enabled = _bridge_comparator_enabled(sidecar_run_record)
    for spec in VERDICT_RECORD_AUTHORITY_FIELD_MAP:
        if spec.m1_current_scope_invariant:
            expected_pairs[spec.target_field] = spec.m1_expected_current_scope_value
            continue
        found, expected_value = _mapping_get(sidecar_run_record, spec.legacy_source_path)
        if not found:
            if not comparator_enabled and spec.legacy_source_path[:3] == (
                "bridge_diagnostics",
                "bridge_comparison_summary",
                "run_drift_report",
            ):
                expected_pairs[spec.target_field] = spec.default_when_comparator_disabled
                continue
            source_gaps.append(spec.target_field)
            continue
        expected_pairs[spec.target_field] = expected_value
    return authority_phase, expected_pairs, tuple(source_gaps)


def build_verdict_record_expected_pairs(
    sidecar_run_record: Mapping[str, Any],
    *,
    verdict_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _, expected_pairs, source_gaps = _collect_expected_pairs_and_source_gaps(
        sidecar_run_record=sidecar_run_record,
        verdict_record=verdict_record,
    )
    if source_gaps:
        raise ValueError(
            "sidecar_run_record missing verdict_record authority source fields: "
            + ", ".join(source_gaps)
        )
    return expected_pairs


def collect_verdict_record_dual_write_source_gaps(
    *,
    sidecar_run_record: Mapping[str, Any],
    verdict_record: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    _, _, source_gaps = _collect_expected_pairs_and_source_gaps(
        sidecar_run_record=sidecar_run_record,
        verdict_record=verdict_record,
    )
    return source_gaps


def collect_verdict_record_dual_write_mismatches(
    *,
    verdict_record: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
) -> tuple[str, ...]:
    _, expected_pairs, source_gaps = _collect_expected_pairs_and_source_gaps(
        sidecar_run_record=sidecar_run_record,
        verdict_record=verdict_record,
    )
    mismatches: list[str] = [f"source_missing:{target_field}" for target_field in source_gaps]
    for spec in VERDICT_RECORD_AUTHORITY_FIELD_MAP:
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
