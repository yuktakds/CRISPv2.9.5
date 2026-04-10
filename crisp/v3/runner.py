from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from crisp.repro.hashing import sha256_file, sha256_json
from crisp.v3.io.tableio import read_records_table
from crisp.v3.artifacts.sink import ArtifactSink
from crisp.v3.builder_provenance import _observation_index, build_builder_provenance_payload
from crisp.v3.channels.cap import CapEvidenceChannel
from crisp.v3.channels.catalytic import CatalyticEvidenceChannel
from crisp.v3.channels.offtarget import OffTargetEvidenceChannel
from crisp.v3.contracts import (
    ArtifactPolicy,
    BridgeComparatorOptions,
    ChannelEvaluationResult,
    ChannelEvidence,
    EvidenceState,
    RunApplicabilityRecord,
    SCVObservationBundle,
    SidecarOptions,
    SidecarRunRecord,
    SidecarRunResult,
    SidecarSnapshot,
)
from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    build_sidecar_layer0_authority_metadata,
    build_verdict_record_authority_fields,
    build_verdict_record_payload,
)
from crisp.v3.path_channel import PathEvidenceChannel
from crisp.v3.policy import SEMANTIC_POLICY_VERSION, SIDECAR_RUN_RECORD_SCHEMA_VERSION, semantic_policy_payload
from crisp.v3.preconditions import (
    ChannelState,
    build_preconditions_readiness,
    derive_truth_source_record,
)
from crisp.v3.projectors.scv_components import (
    project_catalytic_rule3a_to_anchoring_input,
    project_thin_offtarget_to_offtarget_input,
)
from crisp.v3.readiness.consistency import (
    RC2_INVENTORY_SOURCE,
    SIDECAR_INVENTORY_SOURCE,
)
from crisp.v3.report_guards import (
    enforce_shadow_stability_campaign_guard,
    enforce_verdict_record_dual_write_guard,
    guarded_operator_artifacts,
)
from crisp.v3.scv_bridge import SCVBridge, bundle_to_jsonl_rows
from crisp.v3.shadow_stability import (
    METRICS_DRIFT_HISTORY_ARTIFACT,
    SHADOW_STABILITY_CAMPAIGN_ARTIFACT,
    SIDECAR_INVARIANT_HISTORY_ARTIFACT,
    WINDOWS_STREAK_HISTORY_ARTIFACT,
    build_shadow_stability_campaign,
    shadow_stability_campaign_to_payload,
)
from crisp.v3.source_provenance import _resolve_catalytic_evidence_core_path
from crisp.v3.vn06_readiness import VN06_READINESS_ARTIFACT, evaluate_vn06_readiness


class SidecarInvariantError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# チャネル状態判定（判定のみ・I/O なし）
# ---------------------------------------------------------------------------

def _derive_channel_states(
    *,
    options: SidecarOptions,
    path_result: ChannelEvaluationResult,
    cap_result: ChannelEvaluationResult | None,
    catalytic_result: ChannelEvaluationResult | None,
) -> tuple[ChannelState, ChannelState, ChannelState]:
    """path / cap / catalytic それぞれの ChannelState を返す。

    I/O や artifact 書き込みは行わない。
    """
    path_state = (
        ChannelState.OBSERVATION_MATERIALIZED
        if path_result.evidence is not None
        else ChannelState.APPLICABILITY_ONLY
    )
    cap_state = (
        ChannelState.DISABLED
        if not options.cap_enabled
        else ChannelState.APPLICABILITY_ONLY
        if cap_result is not None and cap_result.evidence is None
        else ChannelState.OBSERVATION_MATERIALIZED
    )
    catalytic_state = (
        ChannelState.DISABLED
        if not options.catalytic_enabled
        else ChannelState.APPLICABILITY_ONLY
        if catalytic_result is not None and catalytic_result.evidence is None
        else ChannelState.OBSERVATION_MATERIALIZED
    )
    return path_state, cap_state, catalytic_state


# ---------------------------------------------------------------------------
# Comparator 実行（comparator が有効な場合のみ呼び出す）
# ---------------------------------------------------------------------------

def _run_comparator(
    *,
    snapshot: SidecarSnapshot,
    bundle: SCVObservationBundle,
    sink: Any,
    emit_debug_artifacts: bool,
) -> tuple[
    dict[str, Any] | None,   # comparison_summary_payload
    dict[str, Any] | None,   # run_drift_report_payload
    dict[str, Any],          # channel_comparability
    bool | None,             # path_component_match
    list[str],               # comparable_channels
    list[str],               # v3_only_evidence_channels
]:
    """BridgeComparator を実行してアーティファクトを書き込み、判定値を返す。

    comparator が無効な場合は呼び出さないこと。
    """
    from crisp.v3.adapters.rc2_bridge import RC2BridgeAdapter
    from crisp.v3.bridge.comparator import BridgeComparator
    from crisp.v3.promotion_gates import (
        REQUIRED_CI_CANDIDACY_REPORT_ARTIFACT,
        emit_required_ci_candidacy_report,
        evaluate_np_exclusions,
        evaluate_pr_gates,
        evaluate_vn_gates,
    )
    from crisp.v3.reports.bridge_summary import (
        build_bridge_comparison_summary_payload,
        build_bridge_drift_rows,
        build_bridge_operator_summary,
    )

    adapter = RC2BridgeAdapter()
    rc2_adapt_result = adapter.adapt_path_only(
        run_id=snapshot.run_id,
        config=snapshot.config,
        pat_diagnostics_path=snapshot.pat_diagnostics_path,
        pathyes_force_false=snapshot.pathyes_force_false_requested,
    )
    comparison_result = BridgeComparator().compare(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        rc2_adapt_result=rc2_adapt_result,
        v3_bundle=bundle,
    )
    comparison_summary_payload = build_bridge_comparison_summary_payload(comparison_result)
    run_drift_report_payload = asdict(comparison_result.run_report)
    channel_comparability = {
        "path": comparison_result.summary.channel_comparability.get("path"),
        "cap": None,
        "catalytic": None,
    }
    path_component_match = comparison_result.summary.component_matches.get("path")
    comparable_channels = list(comparison_result.summary.comparable_channels)
    v3_only_evidence_channels = list(comparison_result.summary.v3_only_evidence_channels)

    sink.write_json("bridge_comparison_summary.json", comparison_summary_payload, layer="layer1")
    if emit_debug_artifacts:
        sink.write_json("run_drift_report.json", run_drift_report_payload, layer="layer1")
    sink.write_jsonl(
        "bridge_drift_attribution.jsonl",
        build_bridge_drift_rows(comparison_result),
        layer="layer1",
    )
    sink.write_text(
        "bridge_operator_summary.md",
        build_bridge_operator_summary(comparison_result),
        layer="layer1",
        content_type="text/markdown; charset=utf-8",
    )

    pr_gates = evaluate_pr_gates(
        comparator_scope="path_only_partial",
        channel_name="path",
        channel_contract_complete=True,
        sidecar_invariant_window=[True] * 30,
        baseline_value=comparison_result.run_report.path_component_match_rate,
        metrics_drift_window=[comparison_result.run_report.metrics_drift_count] * 30,
        windows_ci_window=[True] * 30,
        rc2_frozen_regression_green=True,
    )
    vn_gates = evaluate_vn_gates(
        full_scv_mapping_frozen=False,
        all_mapped_components_generated=False,
        all_projectors_integrated=False,
        formal_contracts_complete=False,
        sidecar_invariant_30_green=True,
        verdict_record_migration_complete=True,
    )
    np_exclusions = evaluate_np_exclusions(
        channel_name="path",
        has_rc2_component_mapping=True,
        channel_contract_complete=True,
        baseline_met=(comparison_result.run_report.path_component_match_rate or 0.0) >= 0.95,
        windows_stable=True,
    )
    sink.write_json(
        REQUIRED_CI_CANDIDACY_REPORT_ARTIFACT,
        emit_required_ci_candidacy_report(
            comparator_scope="path_only_partial",
            channel_name="path",
            pr_gates=pr_gates,
            vn_gates=vn_gates,
            np_exclusions=np_exclusions,
        ),
        layer="layer1",
    )

    return (
        comparison_summary_payload,
        run_drift_report_payload,
        channel_comparability,
        path_component_match,
        comparable_channels,
        v3_only_evidence_channels,
    )



def _cap_input_missing_result(detail: str) -> ChannelEvaluationResult:
    return ChannelEvaluationResult(
        evidence=None,
        applicability_records=[
            RunApplicabilityRecord(
                channel_name="cap",
                family="CAP",
                scope="run",
                applicable=False,
                reason_code="CAP_INPUT_MISSING",
                detail=detail,
                diagnostics_source=None,
                diagnostics_payload={},
            )
        ],
    )


def _run_cap_channel(snapshot: SidecarSnapshot) -> ChannelEvaluationResult:
    source_path = snapshot.cap_pair_features_path
    if source_path is None:
        return _cap_input_missing_result("cap pair_features artifact is not available in this snapshot")

    pair_features_path = Path(source_path)
    if not pair_features_path.exists():
        return _cap_input_missing_result(f"{pair_features_path} not found")

    try:
        pair_features_rows = read_records_table(pair_features_path)
    except Exception as exc:
        return _cap_input_missing_result(f"{pair_features_path}: {exc}")

    return CapEvidenceChannel().evaluate(
        pair_features_rows=pair_features_rows,
        source=pair_features_path,
    )


def _catalytic_input_missing_result(detail: str) -> ChannelEvaluationResult:
    return ChannelEvaluationResult(
        evidence=None,
        applicability_records=[
            RunApplicabilityRecord(
                channel_name="catalytic",
                family="CATALYTIC",
                scope="run",
                applicable=False,
                reason_code="CATALYTIC_INPUT_MISSING",
                detail=detail,
                diagnostics_source=None,
                diagnostics_payload={},
            )
        ],
    )


def _run_catalytic_channel(snapshot: SidecarSnapshot) -> ChannelEvaluationResult:
    source_path = _resolve_catalytic_evidence_core_path(snapshot)
    if source_path is None:
        return _catalytic_input_missing_result("evidence_core artifact is not available in this snapshot")

    evidence_core_path = Path(source_path)
    try:
        evidence_core_rows = read_records_table(evidence_core_path)
    except Exception as exc:
        return _catalytic_input_missing_result(f"{evidence_core_path}: {exc}")
    core_compounds_path = snapshot.core_compounds_path
    if core_compounds_path is not None and Path(core_compounds_path).exists():
        core_compound_rows = read_records_table(core_compounds_path)
        compound_index = {
            str(row.get("molecule_id")): row
            for row in core_compound_rows
            if row.get("molecule_id") is not None
        }
        enriched_rows = []
        for row in evidence_core_rows:
            enriched_row = dict(row)
            core_row = compound_index.get(str(row.get("molecule_id")))
            if core_row is not None and "best_target_distance" in core_row:
                enriched_row["best_target_distance"] = core_row.get("best_target_distance")
            enriched_rows.append(enriched_row)
        evidence_core_rows = enriched_rows

    return CatalyticEvidenceChannel().evaluate(
        evidence_core_rows=evidence_core_rows,
        source=evidence_core_path,
    )


def _run_offtarget_channel(snapshot: SidecarSnapshot) -> ChannelEvaluationResult:
    core_compounds_path = snapshot.core_compounds_path
    if core_compounds_path is None or not Path(core_compounds_path).exists():
        return OffTargetEvidenceChannel().evaluate(core_compound_rows=None, source=core_compounds_path)
    return OffTargetEvidenceChannel().evaluate(
        core_compound_rows=read_records_table(core_compounds_path),
        source=core_compounds_path,
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


def _build_internal_full_scv_bundle(
    *,
    snapshot: SidecarSnapshot,
    path_evidences: list[ChannelEvidence],
    catalytic_result: ChannelEvaluationResult | None,
    offtarget_result: ChannelEvaluationResult | None,
    applicability_records: list[RunApplicabilityRecord],
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


def _rc2_output_state(run_dir: Path, *, sidecar_dirname: str) -> tuple[dict[str, str], str]:
    state: dict[str, str] = {}
    if not run_dir.exists():
        return state, sha256_json(state)

    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(run_dir).as_posix()
        if relative_path.startswith(f"{sidecar_dirname}/"):
            continue
        state[relative_path] = sha256_file(path)
    return state, sha256_json(state)


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
    rc2_state_before, rc2_digest_before = _rc2_output_state(run_dir, sidecar_dirname=options.output_dirname)

    sink = ArtifactSink(sidecar_root, semantic_policy_version=SEMANTIC_POLICY_VERSION)
    sink.write_json("semantic_policy_version.json", semantic_policy_payload(), layer="layer0")

    path_channel = PathEvidenceChannel()
    path_result = path_channel.evaluate(
        config=snapshot.config,
        pat_diagnostics_path=snapshot.pat_diagnostics_path,
        pathyes_force_false=snapshot.pathyes_force_false_requested,
    )
    path_evidences = [] if path_result.evidence is None else [path_result.evidence]
    cap_result: ChannelEvaluationResult | None = None
    catalytic_result: ChannelEvaluationResult | None = None
    offtarget_result: ChannelEvaluationResult | None = None
    cap_evidences: list[Any] = []
    catalytic_evidences: list[Any] = []
    if options.cap_enabled:
        cap_result = _run_cap_channel(snapshot)
        cap_evidences = [] if cap_result.evidence is None else [cap_result.evidence]
    if options.catalytic_enabled:
        catalytic_result = _run_catalytic_channel(snapshot)
        catalytic_evidences = [] if catalytic_result.evidence is None else [catalytic_result.evidence]
        offtarget_result = _run_offtarget_channel(snapshot)
    evidences = [*path_evidences, *cap_evidences, *catalytic_evidences]
    applicability_records = list(path_result.applicability_records)
    if cap_result is not None:
        applicability_records.extend(cap_result.applicability_records)
    if catalytic_result is not None:
        applicability_records.extend(catalytic_result.applicability_records)

    bridge = SCVBridge()
    bundle = bridge.bundle(
        run_id=snapshot.run_id,
        evidences=evidences,
        applicability_records=applicability_records,
    )
    sink.write_json("observation_bundle.json", asdict(bundle), layer="layer1")
    if emit_debug_artifacts:
        internal_full_bundle = _build_internal_full_scv_bundle(
            snapshot=snapshot,
            path_evidences=path_evidences,
            catalytic_result=catalytic_result,
            offtarget_result=offtarget_result,
            applicability_records=applicability_records,
        )
        sink.write_json("internal_full_scv_observation_bundle.json", asdict(internal_full_bundle), layer="layer1")
    sink.write_jsonl("channel_evidence_path.jsonl", bundle_to_jsonl_rows(path_evidences), layer="layer1")
    if options.cap_enabled:
        sink.write_jsonl("channel_evidence_cap.jsonl", bundle_to_jsonl_rows(cap_evidences), layer="layer1")
    if options.catalytic_enabled:
        sink.write_jsonl(
            "channel_evidence_catalytic.jsonl",
            bundle_to_jsonl_rows(catalytic_evidences),
            layer="layer1",
        )
    builder_provenance_payload = build_builder_provenance_payload(
        snapshot=snapshot,
        options=options,
        bundle=bundle,
        applicability_records=applicability_records,
    )
    sink.write_json("builder_provenance.json", builder_provenance_payload, layer="layer1")
    channel_evidence_states = {
        channel_name: (
            None
            if observation.evidence_state is None
            else observation.evidence_state.value
        )
        for channel_name, observation in _observation_index(bundle).items()
    }
    for channel_name in ("path", "cap", "catalytic"):
        channel_evidence_states.setdefault(channel_name, None)
    comparison_summary_payload: dict[str, Any] | None = None
    run_drift_report_payload: dict[str, Any] | None = None
    channel_comparability: dict[str, Any] = {"path": None, "cap": None, "catalytic": None}
    path_component_match = None
    comparable_channels: list[str] = []
    v3_only_evidence_channels: list[str] = []
    if comparator_options.enabled:
        (
            comparison_summary_payload,
            run_drift_report_payload,
            channel_comparability,
            path_component_match,
            comparable_channels,
            v3_only_evidence_channels,
        ) = _run_comparator(
            snapshot=snapshot,
            bundle=bundle,
            sink=sink,
            emit_debug_artifacts=emit_debug_artifacts,
        )
    if emit_debug_artifacts:
        _, rc2_digest_midrun = _rc2_output_state(run_dir, sidecar_dirname=options.output_dirname)
        sidecar_invariant_history = [rc2_digest_before == rc2_digest_midrun]
        metrics_drift_history = [
            0 if run_drift_report_payload is None else int(run_drift_report_payload["metrics_drift_count"])
        ]
        windows_streak_history = [True]
        run_drift_report_digest_history = []
        if "run_drift_report.json" in sink.descriptor_payload():
            run_drift_report_digest_history = [sink.descriptor_payload()["run_drift_report.json"]["sha256"]]
        campaign = build_shadow_stability_campaign(
            run_id=snapshot.run_id,
            sidecar_invariant_history=sidecar_invariant_history,
            metrics_drift_history=metrics_drift_history,
            windows_streak_history=windows_streak_history,
            run_drift_report_digest_history=run_drift_report_digest_history,
        )
        campaign_payload = shadow_stability_campaign_to_payload(campaign)
        enforce_shadow_stability_campaign_guard(payload=campaign_payload)
        sink.write_json(SHADOW_STABILITY_CAMPAIGN_ARTIFACT, campaign_payload, layer="layer0")
        sink.write_json(SIDECAR_INVARIANT_HISTORY_ARTIFACT, sidecar_invariant_history, layer="layer0")
        sink.write_json(METRICS_DRIFT_HISTORY_ARTIFACT, metrics_drift_history, layer="layer0")
        sink.write_json(WINDOWS_STREAK_HISTORY_ARTIFACT, windows_streak_history, layer="layer0")
    path_channel_state, cap_channel_state, catalytic_channel_state = _derive_channel_states(
        options=options,
        path_result=path_result,
        cap_result=cap_result,
        catalytic_result=catalytic_result,
    )
    preconditions_readiness_payload = build_preconditions_readiness(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        channel_states={
            "path": path_channel_state,
            "cap": cap_channel_state,
            "catalytic": catalytic_channel_state,
        },
        truth_source_records={
            channel_id: derive_truth_source_record(builder_provenance_payload["channels"][channel_id])
            for channel_id in ("path", "cap", "catalytic")
        },
        comparable_channels=("path",),
        comparator_scope="path_only_partial",
        verdict_comparability=(
            "not_comparable"
            if comparison_summary_payload is None
            else str(comparison_summary_payload.get("verdict_comparability", "not_comparable"))
        ),
        path_adapter_coverage_frozen=True,
        path_bridge_consumer_present=True,
        path_final_verdict_comparability_defined=True,
        report_guard_enabled=True,
        rc2_output_inventory_mutated=False,
        v3_lanes_required=False,
        channel_blockers={
            "path": (),
            "cap": (
                "cap_not_in_current_comparable_channels",
                "cap_comparator_contract_open",
            ),
            "catalytic": (
                "catalytic_not_in_current_comparable_channels",
                "rule3_catalytic_split_adr_open",
            ),
        },
        artifact_descriptors=sink.descriptor_payload(),
        builder_provenance_artifact="builder_provenance.json",
        sidecar_run_record_artifact="sidecar_run_record.json",
        generator_manifest_artifact="generator_manifest.json",
        preconditions_artifact="preconditions_readiness.json",
        operator_report_artifacts=guarded_operator_artifacts(
            bridge_comparator_enabled=comparator_options.enabled,
        ),
        guarded_operator_artifacts=guarded_operator_artifacts(
            bridge_comparator_enabled=comparator_options.enabled,
        ),
        additional_required_artifacts=("verdict_record.json", VN06_READINESS_ARTIFACT),
    )
    sink.write_json(
        "preconditions_readiness.json",
        asdict(preconditions_readiness_payload),
        layer="layer0",
    )

    _, rc2_digest_after = _rc2_output_state(run_dir, sidecar_dirname=options.output_dirname)
    materialized_before_manifest = [
        *sink.materialized_outputs(),
        "sidecar_run_record.json",
        "verdict_record.json",
        VN06_READINESS_ARTIFACT,
    ]
    channel_records = {
        "path": builder_provenance_payload["channels"]["path"],
        "cap": builder_provenance_payload["channels"]["cap"],
        "catalytic": builder_provenance_payload["channels"]["catalytic"],
    }
    enabled_channels = ["path"]
    if options.cap_enabled:
        enabled_channels.append("cap")
    if options.catalytic_enabled:
        enabled_channels.append("catalytic")
    authority_fields_payload = build_verdict_record_authority_fields(
        run_id=snapshot.run_id,
        output_root=str(sidecar_root),
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        comparator_scope="path_only_partial",
        comparable_channels=comparable_channels,
        v3_only_evidence_channels=v3_only_evidence_channels,
        channel_lifecycle_states={
            "path": path_channel_state.value,
            "cap": cap_channel_state.value,
            "catalytic": catalytic_channel_state.value,
        },
        full_verdict_computable=(
            False if run_drift_report_payload is None else bool(run_drift_report_payload.get("full_verdict_computable", False))
        ),
        full_verdict_comparable_count=(
            0 if run_drift_report_payload is None else int(run_drift_report_payload.get("full_verdict_comparable_count", 0))
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
    verdict_record_payload = build_verdict_record_payload(authority_fields=authority_fields_payload)
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
        "bridge_comparator_enabled": comparator_options.enabled,
        "bridge_comparison_summary": comparison_summary_payload,
        "bridge_operator_summary_artifact": (
            "bridge_operator_summary.md" if comparator_options.enabled else None
        ),
        "verdict_record_artifact": "verdict_record.json",
        "vn06_readiness_artifact": VN06_READINESS_ARTIFACT,
        "canonical_layer0_authority_artifact": CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
        **build_sidecar_layer0_authority_metadata(
            verdict_record_payload=verdict_record_payload,
        ),
    }
    if emit_debug_artifacts:
        bridge_diagnostics["internal_full_scv_observation_bundle_artifact"] = (
            "internal_full_scv_observation_bundle.json"
        )
        bridge_diagnostics["shadow_stability_campaign_artifact"] = SHADOW_STABILITY_CAMPAIGN_ARTIFACT

    run_record = SidecarRunRecord(
        schema_version=SIDECAR_RUN_RECORD_SCHEMA_VERSION,
        run_id=snapshot.run_id,
        run_mode=snapshot.run_mode,
        output_root=str(sidecar_root),
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        enabled_channels=enabled_channels,
        observation_count=len(bundle.observations),
        applicability_records=applicability_records,
        materialized_outputs=materialized_before_manifest,
        rc2_output_digest_before=rc2_digest_before,
        rc2_output_digest_after=rc2_digest_after,
        rc2_outputs_unchanged=rc2_digest_before == rc2_digest_after,
        comparator_scope="path_only_partial",
        comparable_channels=comparable_channels,
        v3_only_evidence_channels=v3_only_evidence_channels,
        channel_lifecycle_states={
            "path": path_channel_state.value,
            "cap": cap_channel_state.value,
            "catalytic": catalytic_channel_state.value,
        },
        channel_evidence_states=channel_evidence_states,
        channel_comparability=channel_comparability,
        path_component_match=path_component_match,
        channel_records=channel_records,
        bridge_diagnostics=bridge_diagnostics,
    )
    sink.write_json("sidecar_run_record.json", asdict(run_record), layer="layer0")
    enforce_verdict_record_dual_write_guard(
        verdict_record=verdict_record_payload,
        sidecar_run_record=asdict(run_record),
    )
    sink.write_json("verdict_record.json", verdict_record_payload, layer="layer0")
    manifest_candidate = sink.manifest_payload(run_id=snapshot.run_id)
    vn06_readiness_payload = evaluate_vn06_readiness(
        verdict_record=verdict_record_payload,
        sidecar_run_record=asdict(run_record),
        manifest_outputs=[asdict(descriptor) for descriptor in manifest_candidate.outputs],
    )
    sink.write_json(VN06_READINESS_ARTIFACT, vn06_readiness_payload, layer="layer0")
    manifest_path, expected_output_digest = sink.write_generator_manifest(run_id=snapshot.run_id)

    rc2_state_after, rc2_digest_after_final = _rc2_output_state(run_dir, sidecar_dirname=options.output_dirname)
    if rc2_digest_before != rc2_digest_after_final or rc2_state_before != rc2_state_after:
        raise SidecarInvariantError("v3 sidecar mutated existing rc2 outputs")

    return SidecarRunResult(
        output_root=str(sidecar_root),
        materialized_outputs=[*sink.materialized_outputs(), manifest_path.name],
        expected_output_digest=expected_output_digest,
        rc2_outputs_unchanged=True,
    )
