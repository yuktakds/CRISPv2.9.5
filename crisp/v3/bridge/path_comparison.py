from __future__ import annotations

from typing import Any

from crisp.v3.bridge.path_view import (
    PATH_APPLICABILITY_KEYS,
    PATH_EXPLORATION_KEYS,
    PATH_QUANTITATIVE_KEYS,
    PATH_WITNESS_KEYS,
    applicability_signature,
    path_view,
)
from crisp.v3.contracts import (
    CompoundDriftReport,
    CompoundPathComparability,
    DriftRecord,
    EvidenceState,
    SCVObservation,
    SCVObservationBundle,
    SCVVerdict,
)
from crisp.v3.policy import PATH_CHANNEL_NAME

_NON_COMPARABLE_DRIFT_KINDS = {"coverage_drift", "applicability_drift"}


def bundle_index(bundle: SCVObservationBundle) -> dict[str, SCVObservation]:
    return {observation.channel_name: observation for observation in bundle.observations}


def derive_component_evidence_state(
    observation: SCVObservation | None,
    path_payload: dict[str, Any],
) -> str | None:
    if observation is None:
        return None
    if observation.evidence_state is not None:
        return observation.evidence_state.value
    quantitative_metrics = path_payload["quantitative_metrics"]
    numeric_resolution_limited = quantitative_metrics["numeric_resolution_limited"]
    max_blockage_ratio = quantitative_metrics["max_blockage_ratio"]
    blockage_pass_threshold = path_payload["blockage_pass_threshold"]
    if numeric_resolution_limited is True:
        return EvidenceState.INSUFFICIENT.value
    if max_blockage_ratio is None or blockage_pass_threshold is None:
        return None
    if max_blockage_ratio >= blockage_pass_threshold:
        return EvidenceState.SUPPORTED.value
    return EvidenceState.REFUTED.value


def derive_component_verdict(
    observation: SCVObservation | None,
    path_payload: dict[str, Any],
) -> str | None:
    if observation is None:
        return None
    if observation.verdict is not None:
        return observation.verdict.value
    evidence_state = derive_component_evidence_state(observation, path_payload)
    if evidence_state == EvidenceState.SUPPORTED.value:
        return SCVVerdict.PASS.value
    if evidence_state == EvidenceState.REFUTED.value:
        return SCVVerdict.FAIL.value
    if evidence_state == EvidenceState.INSUFFICIENT.value:
        return SCVVerdict.UNCLEAR.value
    return None


def compare_path_channel(
    *,
    rc2_bundle: SCVObservationBundle,
    v3_bundle: SCVObservationBundle,
    rc2_observation: SCVObservation | None,
    v3_observation: SCVObservation | None,
) -> tuple[CompoundDriftReport, str]:
    drifts: list[DriftRecord] = []
    channel_coverage = "present_on_both_sides"
    if rc2_observation is None or v3_observation is None:
        channel_coverage = (
            "unavailable_on_both_sides"
            if rc2_observation is None and v3_observation is None
            else "unavailable_in_rc2_reference"
            if rc2_observation is None
            else "unavailable_in_v3_shadow"
        )
        drifts.append(
            DriftRecord(
                channel_name=PATH_CHANNEL_NAME,
                drift_kind="coverage_drift",
                message="channel unavailable on one side",
                details={
                    "rc2_present": rc2_observation is not None,
                    "v3_present": v3_observation is not None,
                },
            )
        )

    rc2_view = path_view(rc2_observation)
    v3_view = path_view(v3_observation)
    rc2_run_applicability = applicability_signature(rc2_bundle, channel_name=PATH_CHANNEL_NAME)
    v3_run_applicability = applicability_signature(v3_bundle, channel_name=PATH_CHANNEL_NAME)
    if rc2_run_applicability != v3_run_applicability:
        drifts.append(
            DriftRecord(
                channel_name=PATH_CHANNEL_NAME,
                drift_kind="applicability_drift",
                message="run-level applicability records differ",
                details={
                    "rc2": rc2_run_applicability,
                    "v3": v3_run_applicability,
                },
            )
        )

    if rc2_observation is not None and v3_observation is not None:
        for key in PATH_APPLICABILITY_KEYS:
            if rc2_view["applicability"][key] != v3_view["applicability"][key]:
                drifts.append(
                    DriftRecord(
                        channel_name=PATH_CHANNEL_NAME,
                        drift_kind="applicability_drift",
                        message=f"applicability differs: {key}",
                        details={
                            "field": key,
                            "rc2": rc2_view["applicability"][key],
                            "v3": v3_view["applicability"][key],
                        },
                    )
                )
        for section_name, keys in (
            ("quantitative_metrics", PATH_QUANTITATIVE_KEYS),
            ("exploration_slice", PATH_EXPLORATION_KEYS),
        ):
            for key in keys:
                if rc2_view[section_name][key] != v3_view[section_name][key]:
                    drifts.append(
                        DriftRecord(
                            channel_name=PATH_CHANNEL_NAME,
                            drift_kind="metrics_drift",
                            message=f"{section_name} differs: {key}",
                            details={
                                "section": section_name,
                                "metric": key,
                                "rc2": rc2_view[section_name][key],
                                "v3": v3_view[section_name][key],
                            },
                        )
                    )
        for key in PATH_WITNESS_KEYS:
            if rc2_view["witness_bundle"][key] != v3_view["witness_bundle"][key]:
                drifts.append(
                    DriftRecord(
                        channel_name=PATH_CHANNEL_NAME,
                        drift_kind="witness_drift",
                        message=f"witness differs: {key}",
                        details={
                            "field": key,
                            "rc2": rc2_view["witness_bundle"][key],
                            "v3": v3_view["witness_bundle"][key],
                        },
                    )
                )

    component_comparability = CompoundPathComparability.COMPONENT_VERDICT_COMPARABLE
    drift_kinds = {drift.drift_kind for drift in drifts}
    if drift_kinds & _NON_COMPARABLE_DRIFT_KINDS:
        component_comparability = CompoundPathComparability.NOT_COMPARABLE
    elif "metrics_drift" in drift_kinds:
        component_comparability = CompoundPathComparability.EVIDENCE_COMPARABLE

    rc2_component_verdict = derive_component_verdict(rc2_observation, rc2_view)
    v3_component_verdict = derive_component_verdict(v3_observation, v3_view)
    component_match = (
        None
        if component_comparability is CompoundPathComparability.NOT_COMPARABLE
        or rc2_component_verdict is None
        or v3_component_verdict is None
        else rc2_component_verdict == v3_component_verdict
    )
    return (
        CompoundDriftReport(
            channel_name=PATH_CHANNEL_NAME,
            component_comparability={PATH_CHANNEL_NAME: component_comparability.value},
            component_matches={PATH_CHANNEL_NAME: component_match},
            rc2_component_verdicts={PATH_CHANNEL_NAME: rc2_component_verdict},
            v3_component_verdicts={PATH_CHANNEL_NAME: v3_component_verdict},
            rc2_component_states={
                PATH_CHANNEL_NAME: derive_component_evidence_state(rc2_observation, rc2_view)
            },
            v3_component_states={
                PATH_CHANNEL_NAME: derive_component_evidence_state(v3_observation, v3_view)
            },
            v3_shadow_verdict=None,
            verdict_match=None,
            drifts=tuple(drifts),
        ),
        channel_coverage,
    )
