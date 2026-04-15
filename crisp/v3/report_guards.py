from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    SIDECAR_RUN_RECORD_ROLE,
    sidecar_layer0_authority_artifact,
    sidecar_run_record_role,
)
from crisp.v3.current_public_scope import (
    CATALYTIC_PUBLIC_COMPARABLE_COMPONENT,
    CURRENT_PUBLIC_COMPARABLE_CHANNELS,
)
from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.policy import CATALYTIC_CHANNEL_NAME, PATH_CHANNEL_NAME
from crisp.v3.rp3_activation import (
    ActivationDecisionState,
    ActivationUnit,
    RuntimeActivationContext,
    VNGateState,
    check_forbidden_surfaces,
    may_render_numeric_verdict_rates,
    may_render_v3_shadow_verdict,
)
from crisp.v3.vn06_readiness import collect_verdict_record_dual_write_mismatches


@dataclass(frozen=True, slots=True)
class OperatorSurfaceSpec:
    artifact_name: str
    title_label: str
    render_format: str = "markdown"
    rc2_label_fragment: str = "primary"
    v3_label_fragment: str = "secondary"


OPERATOR_SURFACE_SPECS = {
    "bridge_operator_summary.md": OperatorSurfaceSpec(
        artifact_name="bridge_operator_summary.md",
        title_label="[exploratory] Bridge Operator Summary",
    ),
    "eval_report.json": OperatorSurfaceSpec(
        artifact_name="eval_report.json",
        title_label="[exploratory] Eval Report",
        render_format="json",
    ),
    "qc_report.json": OperatorSurfaceSpec(
        artifact_name="qc_report.json",
        title_label="[exploratory] QC Report",
        render_format="json",
    ),
    "collapse_figure_spec.json": OperatorSurfaceSpec(
        artifact_name="collapse_figure_spec.json",
        title_label="[exploratory] Collapse Figure Spec",
        render_format="json",
    ),
}
EXPLORATORY_OPERATOR_ARTIFACTS = ("bridge_operator_summary.md",)
PRIMARY_CHANNEL_LIFECYCLE_STATES = {
    "disabled",
    "applicability_only",
    "observation_materialized",
}
CURRENT_PUBLIC_COMPARABLE_CHANNEL_SET = set(CURRENT_PUBLIC_COMPARABLE_CHANNELS)


class ReportGuardError(ValueError):
    pass


def _is_numeric(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _has_rendered_verdict_rate(value: Any) -> bool:
    return value not in (None, "N/A")


def _build_runtime_activation_context(
    source: Mapping[str, Any],
    *,
    full_verdict_computable: Any,
    denominator_contract_satisfied: Any,
) -> RuntimeActivationContext:
    activation_decisions = source.get("activation_decisions", {})
    if not isinstance(activation_decisions, Mapping):
        activation_decisions = {}
    vn_gate_state = source.get("vn_gate_state", {})
    if not isinstance(vn_gate_state, Mapping):
        vn_gate_state = {}
    vn_gates = source.get("vn_gates", {})
    if not isinstance(vn_gates, Mapping):
        vn_gates = {}

    def _vn_flag(flat_key: str, legacy_key: str) -> bool:
        if flat_key in vn_gate_state:
            return bool(vn_gate_state.get(flat_key))
        legacy_gate = vn_gates.get(legacy_key)
        if isinstance(legacy_gate, Mapping):
            return bool(legacy_gate.get("passed", False))
        return False

    return RuntimeActivationContext(
        decision=ActivationDecisionState(
            v3_shadow_verdict_accepted=bool(
                activation_decisions.get(ActivationUnit.V3_SHADOW_VERDICT.value, False)
            ),
            numeric_verdict_rates_accepted=bool(
                activation_decisions.get(ActivationUnit.NUMERIC_VERDICT_RATES.value, False)
            ),
        ),
        vn_gate=VNGateState(
            vn_01=_vn_flag("vn_01", "VN-01"),
            vn_02=_vn_flag("vn_02", "VN-02"),
            vn_03=_vn_flag("vn_03", "VN-03"),
            vn_04=_vn_flag("vn_04", "VN-04"),
            vn_05=_vn_flag("vn_05", "VN-05"),
            vn_06=_vn_flag("vn_06", "VN-06"),
        ),
        full_verdict_computable=bool(full_verdict_computable),
        denominator_contract_satisfied=bool(denominator_contract_satisfied),
    )


def enforce_channel_semantics(
    *,
    comparable_channels: Iterable[str],
    v3_only_evidence_channels: Iterable[str],
    component_matches: Mapping[str, Any] | None = None,
    channel_lifecycle_states: Mapping[str, Any] | None = None,
) -> None:
    comparable = tuple(str(channel_name) for channel_name in comparable_channels)
    v3_only = tuple(str(channel_name) for channel_name in v3_only_evidence_channels)
    if set(comparable) - CURRENT_PUBLIC_COMPARABLE_CHANNEL_SET:
        raise ReportGuardError(
            "comparable_channels contains channel outside the current public comparable set"
        )
    if set(comparable) & set(v3_only):
        raise ReportGuardError("v3-only evidence channels must not appear in comparable_channels")
    if component_matches is not None and set(map(str, component_matches.keys())) & set(v3_only):
        raise ReportGuardError("v3-only evidence channels must not appear in component_matches")
    _enforce_catalytic_comparable_invariant(
        comparable_channels=comparable,
        component_matches=component_matches,
    )
    if channel_lifecycle_states is not None:
        normalized_states = {
            str(channel_name): str(state)
            for channel_name, state in channel_lifecycle_states.items()
        }
        for channel_name, state in normalized_states.items():
            if state not in PRIMARY_CHANNEL_LIFECYCLE_STATES:
                raise ReportGuardError(f"{channel_name} has invalid channel_lifecycle_state")
        for channel_name in v3_only:
            if normalized_states.get(channel_name) != "observation_materialized":
                raise ReportGuardError("v3-only evidence channel must be observation_materialized")


def _enforce_catalytic_comparable_invariant(
    *,
    comparable_channels: Iterable[str],
    component_matches: Mapping[str, Any] | None,
) -> None:
    comparable = {str(channel_name) for channel_name in comparable_channels}
    if CATALYTIC_CHANNEL_NAME not in comparable:
        return
    if component_matches is None:
        raise ReportGuardError("catalytic comparable requires catalytic_rule3a component_matches entry")
    normalized_keys = {str(key) for key in component_matches.keys()}
    if CATALYTIC_PUBLIC_COMPARABLE_COMPONENT not in normalized_keys:
        if CATALYTIC_CHANNEL_NAME in normalized_keys:
            raise ReportGuardError("catalytic component_matches key is forbidden; use catalytic_rule3a")
        raise ReportGuardError("catalytic comparable requires catalytic_rule3a component_matches entry")
    if CATALYTIC_CHANNEL_NAME in normalized_keys:
        raise ReportGuardError("catalytic component_matches key is forbidden; use catalytic_rule3a")


def enforce_inventory_authority_split(*, metadata: Mapping[str, Any]) -> None:
    inventory_authority = metadata.get("inventory_authority")
    if not isinstance(inventory_authority, Mapping):
        raise ReportGuardError("inventory_authority metadata is required")
    expected = build_inventory_authority_payload(rc2_output_inventory_mutated=False)
    for field_name, expected_value in expected.items():
        if inventory_authority.get(field_name) != expected_value:
            raise ReportGuardError(f"inventory_authority {field_name} mismatch")


def enforce_exploratory_report_guard(
    *,
    metadata: Mapping[str, Any],
    sections: Iterable[Mapping[str, Any]],
) -> None:
    semantic_policy_version = metadata.get("semantic_policy_version")
    if not semantic_policy_version:
        raise ReportGuardError("semantic_policy_version is required")

    verdict_comparability = metadata.get("verdict_comparability")
    verdict_match_rate = metadata.get("verdict_match_rate")
    verdict_mismatch_rate = metadata.get("verdict_mismatch_rate")
    v3_shadow_verdict = metadata.get("v3_shadow_verdict")
    section_list = [dict(section) for section in sections]
    ctx = _build_runtime_activation_context(
        metadata,
        full_verdict_computable=metadata.get("full_verdict_computable", False),
        denominator_contract_satisfied=metadata.get(
            "denominator_contract_satisfied",
            verdict_comparability == "fully_comparable",
        ),
    )
    shadow_renderable = may_render_v3_shadow_verdict(ctx)
    numeric_rates_renderable = may_render_numeric_verdict_rates(ctx)
    numeric_rates_present = (
        _has_rendered_verdict_rate(verdict_match_rate)
        or _has_rendered_verdict_rate(verdict_mismatch_rate)
    )
    component_matches = metadata.get("component_matches")
    component_match_keys = (
        [str(key) for key in component_matches.keys()]
        if isinstance(component_matches, Mapping)
        else []
    )
    forbidden_surface_errors = check_forbidden_surfaces(
        ctx=ctx,
        comparable_channels=[str(item) for item in metadata.get("comparable_channels", ())],
        component_match_keys=component_match_keys,
        mixed_summary_requested=any(
            section.get("semantic_source") == "mixed"
            for section in section_list
        ),
        numeric_rates_present=numeric_rates_present,
    )
    if numeric_rates_present and not numeric_rates_renderable:
        numeric_guard_error = (
            "numeric verdict rates present while runtime activation conditions are unmet"
        )
        if numeric_guard_error not in forbidden_surface_errors:
            forbidden_surface_errors.append(numeric_guard_error)
    if v3_shadow_verdict is not None and not shadow_renderable:
        raise ReportGuardError(
            "v3_shadow_verdict must remain inactive while runtime activation conditions are unmet"
        )
    if forbidden_surface_errors:
        translated_errors = [
            "mixed semantic source is forbidden"
            if error == "mixed rc2/v3 aggregate summaries are forbidden"
            else error
            for error in forbidden_surface_errors
        ]
        raise ReportGuardError("; ".join(translated_errors))
    enforce_channel_semantics(
        comparable_channels=metadata.get("comparable_channels", ()),
        v3_only_evidence_channels=metadata.get("v3_only_evidence_channels", ()),
        component_matches=metadata.get("component_matches"),
        channel_lifecycle_states=metadata.get("channel_lifecycle_states"),
    )

    rc2_indices: list[int] = []
    v3_indices: list[int] = []
    for index, section in enumerate(section_list):
        semantic_source = section.get("semantic_source")
        label = str(section.get("label", ""))

        if semantic_source not in {"rc2", "v3"}:
            raise ReportGuardError("unknown semantic source is forbidden")

        if semantic_source == "v3" and "[exploratory]" not in label:
            raise ReportGuardError("v3 section must carry [exploratory] label")
        if semantic_source == "v3" and "secondary" not in label.lower():
            raise ReportGuardError("v3 section must carry secondary label")

        if semantic_source == "rc2" and "[exploratory]" in label:
            raise ReportGuardError("rc2 primary section must not carry [exploratory] label")
        if semantic_source == "rc2" and "primary" not in label.lower():
            raise ReportGuardError("rc2 section must carry primary label")

        if semantic_source == "rc2":
            rc2_indices.append(index)
        if semantic_source == "v3":
            v3_indices.append(index)

    if not rc2_indices:
        raise ReportGuardError("rc2 primary section is required")
    if not v3_indices:
        raise ReportGuardError("v3 secondary section is required")
    if rc2_indices[0] != 0:
        raise ReportGuardError("rc2 primary section must be first")
    if max(rc2_indices) > min(v3_indices):
        raise ReportGuardError("v3 secondary sections must follow rc2 primary sections")


def guarded_operator_artifacts(*, bridge_comparator_enabled: bool) -> tuple[str, ...]:
    return EXPLORATORY_OPERATOR_ARTIFACTS if bridge_comparator_enabled else ()


def attach_guarded_exploratory_payload(
    *,
    artifact_name: str,
    payload: Mapping[str, Any],
    metadata: Mapping[str, Any],
    sections: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    surface_spec = OPERATOR_SURFACE_SPECS.get(artifact_name)
    if surface_spec is None:
        raise ReportGuardError(f"unknown operator-facing artifact: {artifact_name}")

    section_list = [dict(section) for section in sections]
    if not section_list:
        return dict(payload)

    enforce_inventory_authority_split(metadata=metadata)
    enforce_exploratory_report_guard(metadata=metadata, sections=section_list)

    guarded_payload = dict(payload)
    guarded_payload["semantic_policy_version"] = metadata["semantic_policy_version"]
    guarded_payload["verdict_comparability"] = metadata.get("verdict_comparability")
    guarded_payload["verdict_match_rate"] = metadata.get("verdict_match_rate")
    if "verdict_mismatch_rate" in metadata:
        guarded_payload["verdict_mismatch_rate"] = metadata.get("verdict_mismatch_rate")
    guarded_payload["inventory_authority"] = dict(metadata["inventory_authority"])
    if "comparator_scope" in metadata:
        guarded_payload["comparator_scope"] = metadata["comparator_scope"]
    if "comparable_channels" in metadata:
        guarded_payload["comparable_channels"] = list(metadata["comparable_channels"])
    if "v3_only_evidence_channels" in metadata:
        guarded_payload["v3_only_evidence_channels"] = list(metadata["v3_only_evidence_channels"])
    if "channel_lifecycle_states" in metadata:
        guarded_payload["channel_lifecycle_states"] = dict(metadata["channel_lifecycle_states"])
    if "activation_decisions" in metadata:
        guarded_payload["activation_decisions"] = dict(metadata["activation_decisions"])
    if "vn_gate_state" in metadata:
        guarded_payload["vn_gate_state"] = dict(metadata["vn_gate_state"])
    if "full_verdict_computable" in metadata:
        guarded_payload["full_verdict_computable"] = bool(metadata["full_verdict_computable"])
    if "denominator_contract_satisfied" in metadata:
        guarded_payload["denominator_contract_satisfied"] = bool(
            metadata["denominator_contract_satisfied"]
        )
    if "suppressed_surfaces" in metadata:
        guarded_payload["suppressed_surfaces"] = list(metadata["suppressed_surfaces"])
    if "promotion_gate_results" in metadata:
        guarded_payload["promotion_gate_results"] = dict(metadata["promotion_gate_results"])
    guarded_payload["operator_surface_contract"] = {
        "artifact_name": surface_spec.artifact_name,
        "title_label": surface_spec.title_label,
        "render_format": surface_spec.render_format,
        "rc2_label_fragment": surface_spec.rc2_label_fragment,
        "v3_label_fragment": surface_spec.v3_label_fragment,
    }
    guarded_payload["exploratory_sections"] = section_list
    return guarded_payload


def render_guarded_exploratory_report(
    *,
    artifact_name: str,
    metadata: Mapping[str, Any],
    sections: Iterable[Mapping[str, Any]],
    lines: Iterable[str],
) -> str:
    surface_spec = OPERATOR_SURFACE_SPECS.get(artifact_name)
    if surface_spec is None:
        raise ReportGuardError(f"unknown operator-facing artifact: {artifact_name}")
    enforce_inventory_authority_split(metadata=metadata)
    enforce_exploratory_report_guard(metadata=metadata, sections=sections)
    rendered = "\n".join(lines) + "\n"
    if surface_spec.title_label not in rendered:
        raise ReportGuardError(f"{artifact_name} missing exploratory title label")
    if "semantic_policy_version" not in rendered:
        raise ReportGuardError(f"{artifact_name} must render semantic_policy_version")
    if metadata.get("v3_only_evidence_channels") and "[v3-only]" not in rendered:
        raise ReportGuardError(f"{artifact_name} must render [v3-only] labels for v3-only evidence")
    return rendered


def enforce_candidacy_report_guard(
    *,
    payload: Mapping[str, Any],
    sections: Iterable[Mapping[str, Any]] = (),
) -> None:
    if payload.get("required_matrix_mutation_allowed") is not False:
        raise ReportGuardError("candidacy report must not allow required matrix mutation")
    if payload.get("human_explicit_decision_required") is not True:
        raise ReportGuardError("candidacy report must require human explicit decision")
    operator_surface = payload.get("operator_surface", {})
    if not isinstance(operator_surface, Mapping):
        raise ReportGuardError("candidacy report operator_surface is required")
    if payload.get("v3_shadow_verdict") not in (None,):
        raise ReportGuardError("PR pass must not auto-activate v3_shadow_verdict")
    if payload.get("verdict_match_rate") not in (None, "N/A"):
        raise ReportGuardError("candidacy report must not activate verdict_match_rate")
    label = str(operator_surface.get("label", ""))
    if "[exploratory]" not in label:
        raise ReportGuardError("candidacy status must stay in [exploratory] operator surface")
    for section in sections:
        if section.get("semantic_source") == "rc2" and "candidacy" in str(section.get("label", "")).lower():
            raise ReportGuardError("candidacy status must not appear in primary verdict section")


def enforce_verdict_record_dual_write_guard(
    *,
    verdict_record: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
) -> None:
    mismatches = collect_verdict_record_dual_write_mismatches(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
    )
    if mismatches:
        raise ReportGuardError(f"verdict_record dual-write mismatch: {mismatches[0]}")
    if verdict_record.get("v3_shadow_verdict") is not None:
        raise ReportGuardError("verdict_record must keep v3_shadow_verdict inactive before public inclusion")
    if verdict_record.get("verdict_match_rate") is not None:
        raise ReportGuardError("verdict_record must keep verdict_match_rate inactive before public inclusion")
    if verdict_record.get("verdict_mismatch_rate") is not None:
        raise ReportGuardError("verdict_record must keep verdict_mismatch_rate inactive before public inclusion")
    if verdict_record.get("authority_transfer_complete") is True:
        if sidecar_layer0_authority_artifact(sidecar_run_record) != CANONICAL_LAYER0_AUTHORITY_ARTIFACT:
            raise ReportGuardError(
                "sidecar_run_record must reference verdict_record.json as canonical Layer 0 authority"
            )
        if sidecar_run_record_role(sidecar_run_record) != SIDECAR_RUN_RECORD_ROLE:
            raise ReportGuardError(
                "sidecar_run_record must be marked as backward_compatible_mirror after M-2 cutover"
            )


def enforce_shadow_stability_campaign_guard(*, payload: Mapping[str, Any]) -> None:
    window_size = int(payload.get("required_window_size", 0))
    if window_size != 30:
        raise ReportGuardError("shadow stability campaign must require a 30-run window")
    if payload.get("campaign_passed") is True:
        if payload.get("sidecar_invariant_green") is not True:
            raise ReportGuardError("campaign_passed requires sidecar_invariant_green")
        if payload.get("metrics_drift_zero") is not True:
            raise ReportGuardError("campaign_passed requires metrics_drift_zero")
        if payload.get("windows_streak_green") is not True:
            raise ReportGuardError("campaign_passed requires windows_streak_green")
        if payload.get("digest_stable") is not True:
            raise ReportGuardError("campaign_passed requires digest_stable")
