from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from crisp.v3.contracts import (
    ChannelEvaluationResult,
    ChannelEvidence,
    EvidenceState,
    SCVObservationBundle,
    SidecarOptions,
    SidecarSnapshot,
)
from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    build_sidecar_layer0_authority_metadata,
    build_verdict_record_authority_fields,
    build_verdict_record_payload,
)
from crisp.v3.policy import (
    CAP_CHANNEL_NAME,
    CATALYTIC_CHANNEL_NAME,
    PATH_CHANNEL_NAME,
    SEMANTIC_POLICY_VERSION,
)
from crisp.v3.projectors.scv_components import (
    project_catalytic_rule3a_to_anchoring_input,
    project_thin_offtarget_to_offtarget_input,
)
from crisp.v3.readiness.consistency import RC2_INVENTORY_SOURCE, SIDECAR_INVENTORY_SOURCE
from crisp.v3.scv_bridge import SCVBridge
from crisp.v3.source_provenance import _resolve_catalytic_evidence_core_path


@dataclass(frozen=True, slots=True)
class Layer0AuthorityAssembly:
    authority_fields_payload: dict[str, Any]
    verdict_record_payload: dict[str, Any]
    bridge_diagnostics: dict[str, Any]
    enabled_channels: list[str]


def build_internal_full_scv_bundle(
    *,
    snapshot: SidecarSnapshot,
    path_evidences: list[ChannelEvidence],
    catalytic_result: ChannelEvaluationResult | None,
    offtarget_result: ChannelEvaluationResult | None,
    applicability_records: list[Any],
) -> SCVObservationBundle:
    component_evidences: list[ChannelEvidence] = list(path_evidences)
    if catalytic_result is not None and catalytic_result.evidence is not None:
        try:
            component_evidences.append(
                _anchoring_component_evidence(
                    catalytic_evidence=catalytic_result.evidence,
                    snapshot=snapshot,
                )
            )
        except ValueError:
            pass
    if offtarget_result is not None and offtarget_result.evidence is not None:
        try:
            component_evidences.append(
                _offtarget_component_evidence(
                    offtarget_evidence=offtarget_result.evidence,
                    snapshot=snapshot,
                )
            )
        except ValueError:
            pass
    return SCVBridge().bundle(
        run_id=snapshot.run_id,
        evidences=component_evidences,
        applicability_records=applicability_records,
        bridge_diagnostics_extra={
            "bundle_kind": "internal_full_scv",
            "operator_surface_active": False,
            "component_channels": [evidence.channel_name for evidence in component_evidences],
        },
    )


def assemble_layer0_authority(
    *,
    snapshot: SidecarSnapshot,
    options: SidecarOptions,
    bundle: SCVObservationBundle,
    output_root: str,
    comparison_summary_payload: dict[str, Any] | None,
    run_drift_report_payload: dict[str, Any] | None,
    comparable_channels: list[str],
    v3_only_evidence_channels: list[str],
    path_channel_state: str,
    cap_channel_state: str,
    catalytic_channel_state: str,
    emit_debug_artifacts: bool,
) -> Layer0AuthorityAssembly:
    channel_lifecycle_states = {
        PATH_CHANNEL_NAME: path_channel_state,
        CAP_CHANNEL_NAME: cap_channel_state,
        CATALYTIC_CHANNEL_NAME: catalytic_channel_state,
    }
    enabled_channels = [PATH_CHANNEL_NAME]
    if options.cap_enabled:
        enabled_channels.append(CAP_CHANNEL_NAME)
    if options.catalytic_enabled:
        enabled_channels.append(CATALYTIC_CHANNEL_NAME)

    authority_fields_payload = build_verdict_record_authority_fields(
        run_id=snapshot.run_id,
        output_root=output_root,
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        comparator_scope="path_only_partial",
        comparable_channels=comparable_channels,
        v3_only_evidence_channels=v3_only_evidence_channels,
        channel_lifecycle_states=channel_lifecycle_states,
        full_verdict_computable=(
            False
            if run_drift_report_payload is None
            else bool(run_drift_report_payload.get("full_verdict_computable", False))
        ),
        full_verdict_comparable_count=(
            0
            if run_drift_report_payload is None
            else int(run_drift_report_payload.get("full_verdict_comparable_count", 0))
        ),
        verdict_match_rate=(
            None if run_drift_report_payload is None else run_drift_report_payload.get("verdict_match_rate")
        ),
        verdict_mismatch_rate=(
            None if run_drift_report_payload is None else run_drift_report_payload.get("verdict_mismatch_rate")
        ),
        path_component_match_rate=(
            None if run_drift_report_payload is None else run_drift_report_payload.get("path_component_match_rate")
        ),
        v3_shadow_verdict=None,
        authority_transfer_complete=True,
    )
    verdict_record_payload = build_verdict_record_payload(
        authority_fields=authority_fields_payload,
    )
    bridge_diagnostics = {
        **dict(bundle.bridge_diagnostics),
        "comparison_type": snapshot.comparison_type,
        "pathyes_mode_requested": snapshot.pathyes_mode_requested,
        "resource_profile": snapshot.resource_profile,
        "cap_channel_enabled": options.cap_enabled,
        "cap_pair_features_path": snapshot.cap_pair_features_path,
        "catalytic_channel_enabled": options.catalytic_enabled,
        "catalytic_evidence_core_path": _resolve_catalytic_evidence_core_path(snapshot),
        "builder_provenance_artifact": "builder_provenance.json",
        "preconditions_readiness_artifact": "preconditions_readiness.json",
        "generator_manifest_artifact": "generator_manifest.json",
        "sidecar_inventory_authority": SIDECAR_INVENTORY_SOURCE,
        "rc2_inventory_authority": RC2_INVENTORY_SOURCE,
        "bridge_comparator_enabled": comparison_summary_payload is not None,
        "bridge_comparison_summary": comparison_summary_payload,
        "bridge_operator_summary_artifact": (
            "bridge_operator_summary.md" if comparison_summary_payload is not None else None
        ),
        "verdict_record_artifact": "verdict_record.json",
        "vn06_readiness_artifact": "vn06_readiness.json",
        "canonical_layer0_authority_artifact": CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
        **build_sidecar_layer0_authority_metadata(
            verdict_record_payload=verdict_record_payload,
        ),
    }
    if emit_debug_artifacts:
        bridge_diagnostics["internal_full_scv_observation_bundle_artifact"] = (
            "internal_full_scv_observation_bundle.json"
        )
        bridge_diagnostics["shadow_stability_campaign_artifact"] = "shadow_stability_campaign.json"
    return Layer0AuthorityAssembly(
        authority_fields_payload=authority_fields_payload,
        verdict_record_payload=verdict_record_payload,
        bridge_diagnostics=bridge_diagnostics,
        enabled_channels=enabled_channels,
    )


def _anchoring_component_evidence(
    *,
    catalytic_evidence: ChannelEvidence,
    snapshot: SidecarSnapshot,
) -> ChannelEvidence:
    anchoring_input = project_catalytic_rule3a_to_anchoring_input(catalytic_evidence.payload)
    best_target_distance = float(anchoring_input.best_target_distance)
    if best_target_distance <= float(snapshot.config.anchoring.bond_threshold):
        state = EvidenceState.SUPPORTED
    elif best_target_distance <= float(snapshot.config.anchoring.near_threshold):
        state = EvidenceState.INSUFFICIENT
    else:
        state = EvidenceState.REFUTED
    return ChannelEvidence(
        channel_name="scv_anchoring",
        family="SCV_ANCHORING",
        state=state,
        payload={
            "quantitative_metrics": {
                "best_target_distance": best_target_distance,
            },
            "projector_source": "catalytic_rule3a_projector",
        },
        source="catalytic_rule3a_projector",
        bridge_metrics={
            "truth_source_kind": "catalytic_rule3a_projector",
            "mapping_status": "FROZEN",
        },
    )


def _offtarget_component_evidence(
    *,
    offtarget_evidence: ChannelEvidence,
    snapshot: SidecarSnapshot,
) -> ChannelEvidence:
    offtarget_input = project_thin_offtarget_to_offtarget_input(offtarget_evidence.payload)
    best_offtarget_distance = float(offtarget_input.best_offtarget_distance)
    state = (
        EvidenceState.SUPPORTED
        if best_offtarget_distance >= float(snapshot.config.offtarget.distance_threshold)
        else EvidenceState.REFUTED
    )
    return ChannelEvidence(
        channel_name="scv_offtarget",
        family="SCV_OFFTARGET",
        state=state,
        payload={
            "quantitative_metrics": {
                "best_offtarget_distance": best_offtarget_distance,
            },
            "projector_source": "thin_offtarget_channel_wrapper",
        },
        source="thin_offtarget_channel_wrapper",
        bridge_metrics={
            "truth_source_kind": "thin_offtarget_channel_wrapper",
            "mapping_status": "FROZEN",
        },
    )
