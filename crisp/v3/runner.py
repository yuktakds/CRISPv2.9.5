from __future__ import annotations

from pathlib import Path
from typing import Any

from crisp.v3.artifacts.sink import ArtifactSink
from crisp.v3.builder_provenance import _observation_index, build_builder_provenance_payload
from crisp.v3.contracts import (
    ArtifactPolicy,
    BridgeComparatorOptions,
    SidecarOptions,
    SidecarRunResult,
    SidecarSnapshot,
)
from crisp.v3.current_public_scope import (
    CURRENT_PUBLIC_COMPARABLE_CHANNELS,
    CURRENT_PUBLIC_COMPARATOR_SCOPE,
    derive_v3_only_evidence_channels,
)
from crisp.v3.policy import (
    CAP_CHANNEL_NAME,
    CATALYTIC_CHANNEL_NAME,
    PATH_CHANNEL_NAME,
    SEMANTIC_POLICY_VERSION,
)
from crisp.v3.preconditions import build_preconditions_readiness, derive_truth_source_record
from crisp.v3.report_guards import guarded_operator_artifacts
from crisp.v3.runner_artifacts import (
    SidecarInvariantError,
    emit_bundle_artifacts,
    emit_semantic_policy_artifact,
    emit_shadow_stability_artifacts,
    finalize_sidecar_run,
    rc2_output_state,
)
from crisp.v3.runner_authority import (
    assemble_layer0_authority,
    build_internal_full_scv_bundle,
)
from crisp.v3.runner_channels import derive_channel_states, execute_channels
from crisp.v3.runner_comparator import empty_comparator_execution, run_bridge_comparator
from crisp.v3.scv_bridge import SCVBridge
from crisp.v3.vn06_readiness import VN06_READINESS_ARTIFACT

CORE_CHANNEL_NAMES = (PATH_CHANNEL_NAME, CAP_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME)


def build_sidecar_snapshot(
    *,
    run_id: str,
    run_mode: str,
    repo_root: str,
    out_dir: str | Path,
    config_path: str | Path,
    integrated_config_path: str | Path | None,
    resource_profile: str,
    comparison_type: str | None,
    pathyes_mode_requested: str | None,
    pathyes_force_false_requested: bool,
    pat_diagnostics_path: str | Path | None,
    config: Any,
    rc2_generated_outputs: list[str],
    cap_pair_features_path: str | Path | None = None,
    core_compounds_path: str | Path | None = None,
) -> SidecarSnapshot:
    return SidecarSnapshot(
        run_id=run_id,
        run_mode=run_mode,
        repo_root=str(repo_root),
        out_dir=str(out_dir),
        config_path=str(config_path),
        integrated_config_path=(
            None if integrated_config_path is None else str(integrated_config_path)
        ),
        resource_profile=resource_profile,
        comparison_type=comparison_type,
        pathyes_mode_requested=pathyes_mode_requested,
        pathyes_force_false_requested=pathyes_force_false_requested,
        pat_diagnostics_path=(None if pat_diagnostics_path is None else str(pat_diagnostics_path)),
        config=config,
        rc2_generated_outputs=tuple(rc2_generated_outputs),
        cap_pair_features_path=(
            None if cap_pair_features_path is None else str(cap_pair_features_path)
        ),
        core_compounds_path=(
            None if core_compounds_path is None else str(core_compounds_path)
        ),
    )


def run_sidecar(
    *,
    snapshot: SidecarSnapshot,
    options: SidecarOptions,
    comparator_options: BridgeComparatorOptions | None = None,
) -> SidecarRunResult | None:
    if not options.enabled:
        return None
    if comparator_options is None:
        comparator_options = BridgeComparatorOptions()
    emit_debug_artifacts = options.artifact_policy == ArtifactPolicy.FULL

    run_dir = Path(snapshot.out_dir)
    sidecar_root = run_dir / options.output_dirname
    rc2_state_before, rc2_digest_before = rc2_output_state(
        run_dir,
        sidecar_dirname=options.output_dirname,
    )

    sink = ArtifactSink(sidecar_root, semantic_policy_version=SEMANTIC_POLICY_VERSION)
    emit_semantic_policy_artifact(sink=sink)

    execution = execute_channels(snapshot=snapshot, options=options)
    bundle = SCVBridge().bundle(
        run_id=snapshot.run_id,
        evidences=execution.evidences,
        applicability_records=execution.applicability_records,
    )
    internal_full_bundle = (
        build_internal_full_scv_bundle(
            snapshot=snapshot,
            path_evidences=execution.path_evidences,
            catalytic_result=execution.catalytic_result,
            offtarget_result=execution.offtarget_result,
            applicability_records=execution.applicability_records,
        )
        if emit_debug_artifacts
        else None
    )
    builder_provenance_payload = build_builder_provenance_payload(
        snapshot=snapshot,
        options=options,
        bundle=bundle,
        applicability_records=execution.applicability_records,
    )
    emit_bundle_artifacts(
        sink=sink,
        options=options,
        bundle=bundle,
        path_evidences=execution.path_evidences,
        cap_evidences=execution.cap_evidences,
        catalytic_evidences=execution.catalytic_evidences,
        builder_provenance_payload=builder_provenance_payload,
        internal_full_bundle=internal_full_bundle,
    )

    channel_evidence_states = {
        channel_name: (
            None
            if observation.evidence_state is None
            else observation.evidence_state.value
        )
        for channel_name, observation in _observation_index(bundle).items()
    }
    for channel_name in CORE_CHANNEL_NAMES:
        channel_evidence_states.setdefault(channel_name, None)

    comparator_execution = empty_comparator_execution()
    if comparator_options.enabled:
        comparator_execution = run_bridge_comparator(
            snapshot=snapshot,
            bundle=bundle,
            sink=sink,
            emit_debug_artifacts=emit_debug_artifacts,
        )

    if emit_debug_artifacts:
        _, rc2_digest_midrun = rc2_output_state(
            run_dir,
            sidecar_dirname=options.output_dirname,
        )
        emit_shadow_stability_artifacts(
            sink=sink,
            run_id=snapshot.run_id,
            rc2_digest_before=rc2_digest_before,
            rc2_digest_midrun=rc2_digest_midrun,
            run_drift_report_payload=comparator_execution.run_drift_report_payload,
        )

    path_channel_state, cap_channel_state, catalytic_channel_state = derive_channel_states(
        options=options,
        execution=execution,
    )
    channel_lifecycle_states = {
        PATH_CHANNEL_NAME: path_channel_state.value,
        CAP_CHANNEL_NAME: cap_channel_state.value,
        CATALYTIC_CHANNEL_NAME: catalytic_channel_state.value,
    }
    v3_only_evidence_channels = list(
        derive_v3_only_evidence_channels(channel_lifecycle_states)
    )
    comparable_channels = list(CURRENT_PUBLIC_COMPARABLE_CHANNELS)
    if comparator_execution.comparable_channels:
        comparable_channels = list(comparator_execution.comparable_channels)
    if comparator_execution.v3_only_evidence_channels:
        v3_only_evidence_channels = list(comparator_execution.v3_only_evidence_channels)
    guarded_ops = guarded_operator_artifacts(
        bridge_comparator_enabled=comparator_options.enabled,
    )
    preconditions_readiness_payload = build_preconditions_readiness(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        channel_states={
            PATH_CHANNEL_NAME: path_channel_state,
            CAP_CHANNEL_NAME: cap_channel_state,
            CATALYTIC_CHANNEL_NAME: catalytic_channel_state,
        },
        truth_source_records={
            channel_id: derive_truth_source_record(builder_provenance_payload["channels"][channel_id])
            for channel_id in CORE_CHANNEL_NAMES
        },
        comparable_channels=tuple(comparable_channels),
        comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
        verdict_comparability=(
            "not_comparable"
            if comparator_execution.comparison_summary_payload is None
            else str(
                comparator_execution.comparison_summary_payload.get(
                    "verdict_comparability",
                    "not_comparable",
                )
            )
        ),
        path_adapter_coverage_frozen=True,
        path_bridge_consumer_present=True,
        path_final_verdict_comparability_defined=True,
        report_guard_enabled=True,
        rc2_output_inventory_mutated=False,
        v3_lanes_required=False,
        channel_blockers={
            PATH_CHANNEL_NAME: (),
            CAP_CHANNEL_NAME: (
                "cap_not_in_current_comparable_channels",
                "cap_comparator_contract_open",
            ),
            CATALYTIC_CHANNEL_NAME: (
                "catalytic_rule3a_public_projection_pending",
                "rule3_catalytic_split_adr_open",
            ),
        },
        artifact_descriptors=sink.descriptor_payload(),
        builder_provenance_artifact="builder_provenance.json",
        sidecar_run_record_artifact="sidecar_run_record.json",
        generator_manifest_artifact="generator_manifest.json",
        preconditions_artifact="preconditions_readiness.json",
        operator_report_artifacts=guarded_ops,
        guarded_operator_artifacts=guarded_ops,
        additional_required_artifacts=("verdict_record.json", VN06_READINESS_ARTIFACT),
    )

    _, rc2_digest_after = rc2_output_state(
        run_dir,
        sidecar_dirname=options.output_dirname,
    )
    authority = assemble_layer0_authority(
        snapshot=snapshot,
        options=options,
        bundle=bundle,
        output_root=str(sidecar_root),
        comparison_summary_payload=comparator_execution.comparison_summary_payload,
        run_drift_report_payload=comparator_execution.run_drift_report_payload,
        comparable_channels=comparable_channels,
        v3_only_evidence_channels=v3_only_evidence_channels,
        path_channel_state=path_channel_state.value,
        cap_channel_state=cap_channel_state.value,
        catalytic_channel_state=catalytic_channel_state.value,
        emit_debug_artifacts=emit_debug_artifacts,
    )

    return finalize_sidecar_run(
        sink=sink,
        snapshot=snapshot,
        options=options,
        run_dir=run_dir,
        rc2_state_before=rc2_state_before,
        rc2_digest_before=rc2_digest_before,
        rc2_digest_after=rc2_digest_after,
        bundle=bundle,
        applicability_records=execution.applicability_records,
        channel_evidence_states=channel_evidence_states,
        channel_comparability=comparator_execution.channel_comparability,
        path_component_match=comparator_execution.path_component_match,
        builder_provenance_payload=builder_provenance_payload,
        preconditions_readiness_payload=preconditions_readiness_payload,
        authority=authority,
    )
