from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from crisp.repro.hashing import sha256_file, sha256_json
from crisp.v29.tableio import read_records_table
from crisp.v3.adapters.rc2_bridge import RC2BridgeAdapter
from crisp.v3.artifacts.sink import ArtifactSink
from crisp.v3.bridge.comparator import BridgeComparator
from crisp.v3.channels.cap import CapEvidenceChannel
from crisp.v3.channels.catalytic import CatalyticEvidenceChannel
from crisp.v3.contracts import (
    BridgeComparatorOptions,
    ChannelEvaluationResult,
    RunApplicabilityRecord,
    SCVObservationBundle,
    SidecarOptions,
    SidecarRunRecord,
    SidecarRunResult,
    SidecarSnapshot,
)
from crisp.v3.path_channel import PathEvidenceChannel
from crisp.v3.policy import (
    BUILDER_PROVENANCE_SCHEMA_VERSION,
    SEMANTIC_POLICY_VERSION,
    SIDECAR_RUN_RECORD_SCHEMA_VERSION,
    semantic_policy_payload,
)
from crisp.v3.preconditions import (
    ChannelState,
    build_preconditions_readiness,
    derive_truth_source_record,
)
from crisp.v3.readiness.consistency import (
    RC2_INVENTORY_SOURCE,
    SIDECAR_INVENTORY_SOURCE,
)
from crisp.v3.report_guards import guarded_operator_artifacts
from crisp.v3.reports.bridge_summary import (
    build_bridge_comparison_summary_payload,
    build_bridge_drift_rows,
    build_bridge_operator_summary,
)
from crisp.v3.scv_bridge import SCVBridge, bundle_to_jsonl_rows


class SidecarInvariantError(RuntimeError):
    pass


def _source_label(path_value: str | None, *, snapshot: SidecarSnapshot) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    out_dir = Path(snapshot.out_dir)
    repo_root = Path(snapshot.repo_root)
    for base in (out_dir, repo_root):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name


def _source_location_kind(path_value: str | None, *, snapshot: SidecarSnapshot) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    out_dir = Path(snapshot.out_dir)
    repo_root = Path(snapshot.repo_root)
    try:
        path.relative_to(out_dir)
        return "run_output_snapshot"
    except ValueError:
        pass
    try:
        path.relative_to(repo_root)
        return "repo_input_snapshot"
    except ValueError:
        pass
    return "external_input_snapshot"


def _source_descriptor(
    path_value: str | None,
    *,
    kind: str,
    snapshot: SidecarSnapshot,
    digest_override: str | None = None,
) -> dict[str, Any]:
    digest = None
    if digest_override is not None:
        digest = digest_override
    elif path_value is not None and Path(path_value).exists():
        digest = sha256_file(path_value)
    return {
        "kind": kind,
        "source_label": _source_label(path_value, snapshot=snapshot),
        "source_location_kind": _source_location_kind(path_value, snapshot=snapshot),
        "source_digest": digest,
    }


def _cap_pair_features_semantic_digest(path_value: str | None) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    rows = read_records_table(path)
    normalized_rows = []
    for row in rows:
        normalized_row = {
            str(key): value
            for key, value in dict(row).items()
            if key != "run_id"
        }
        normalized_rows.append(normalized_row)
    return sha256_json(normalized_rows)


def _catalytic_evidence_core_semantic_digest(path_value: str | None) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    if not path.exists():
        return None

    def _json_ready(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): _json_ready(subvalue) for key, subvalue in value.items()}
        if isinstance(value, list):
            return [_json_ready(item) for item in value]
        if isinstance(value, tuple):
            return [_json_ready(item) for item in value]
        if hasattr(value, "tolist") and not isinstance(value, (str, bytes, bytearray)):
            return _json_ready(value.tolist())
        return value

    rows = read_records_table(path)
    normalized_rows = []
    for row in rows:
        normalized_row = {
            str(key): _json_ready(value)
            for key, value in dict(row).items()
            if key not in {"run_id", "evidence_path"}
        }
        normalized_rows.append(normalized_row)
    normalized_rows.sort(
        key=lambda row: (
            str(row.get("molecule_id", "")),
            str(row.get("target_id", "")),
            str(row.get("candidate_order_hash", "")),
        )
    )
    return sha256_json(normalized_rows)


def _applicability_rows(records: list[RunApplicabilityRecord], *, channel_name: str) -> list[dict[str, Any]]:
    rows = [
        {
            "reason_code": record.reason_code,
            "detail": record.detail,
            "scope": record.scope,
            "applicable": record.applicable,
        }
        for record in records
        if record.channel_name == channel_name
    ]
    return sorted(rows, key=lambda row: (str(row["reason_code"]), str(row["detail"])))


def _observation_index(bundle: SCVObservationBundle) -> dict[str, Any]:
    return {observation.channel_name: observation for observation in bundle.observations}


def _path_truth_source_chain(snapshot: SidecarSnapshot) -> list[dict[str, Any]]:
    return [
        {
            "stage": "input_snapshot",
            **_source_descriptor(
                snapshot.pat_diagnostics_path,
                kind="pat_diagnostics_json",
                snapshot=snapshot,
            ),
        },
        {
            "stage": "channel_builder",
            "builder": "crisp.v3.path_channel.PathEvidenceChannel.evaluate",
            "projector": "crisp.v3.path_channel.project_path_payload",
            "channel_evidence_artifact": "channel_evidence_path.jsonl",
        },
        {
            "stage": "bridge_route",
            "bridge": "crisp.v3.scv_bridge.SCVBridge.route",
            "observation_artifact": "observation_bundle.json",
        },
    ]


def _cap_truth_source_chain(snapshot: SidecarSnapshot, *, enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return [
            {
                "stage": "channel_toggle",
                "kind": "cap_sidecar_opt_in",
                "status": "disabled",
            }
        ]
    return [
        {
            "stage": "input_snapshot",
            **_source_descriptor(
                snapshot.cap_pair_features_path,
                kind="pair_features_snapshot",
                snapshot=snapshot,
                digest_override=_cap_pair_features_semantic_digest(snapshot.cap_pair_features_path),
            ),
        },
        {
            "stage": "channel_builder",
            "builder": "crisp.v3.channels.cap.CapEvidenceChannel.evaluate",
            "projector": "crisp.v3.projectors.cap.project_cap_payload",
            "channel_evidence_artifact": "channel_evidence_cap.jsonl",
        },
        {
            "stage": "bridge_route",
            "bridge": "crisp.v3.scv_bridge.SCVBridge.route",
            "observation_artifact": "observation_bundle.json",
        },
    ]


def _resolve_catalytic_evidence_core_path(snapshot: SidecarSnapshot) -> str | None:
    run_dir = Path(snapshot.out_dir)
    for candidate in (run_dir / "evidence_core.parquet", run_dir / "evidence_core.jsonl"):
        if candidate.exists():
            return str(candidate)
    return None


def _catalytic_truth_source_chain(snapshot: SidecarSnapshot, *, enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return [
            {
                "stage": "channel_toggle",
                "kind": "catalytic_sidecar_opt_in",
                "status": "disabled",
            }
        ]
    source_path = _resolve_catalytic_evidence_core_path(snapshot)
    return [
        {
            "stage": "input_snapshot",
            **_source_descriptor(
                source_path,
                kind="evidence_core_snapshot",
                snapshot=snapshot,
                digest_override=_catalytic_evidence_core_semantic_digest(source_path),
            ),
        },
        {
            "stage": "channel_builder",
            "builder": "crisp.v3.channels.catalytic.CatalyticEvidenceChannel.evaluate",
            "projector": "crisp.v3.projectors.catalytic.project_catalytic_payload",
            "channel_evidence_artifact": "channel_evidence_catalytic.jsonl",
        },
        {
            "stage": "bridge_route",
            "bridge": "crisp.v3.scv_bridge.SCVBridge.route",
            "observation_artifact": "observation_bundle.json",
        },
    ]


def _channel_record(
    *,
    channel_name: str,
    enabled: bool,
    bundle: SCVObservationBundle,
    applicability_records: list[RunApplicabilityRecord],
    truth_source_chain: list[dict[str, Any]],
    channel_evidence_artifact: str | None,
) -> dict[str, Any]:
    observation = _observation_index(bundle).get(channel_name)
    applicability = _applicability_rows(applicability_records, channel_name=channel_name)
    payload = {} if observation is None else dict(observation.payload)
    validation_payload = payload.get("validation")
    constraint_payload = payload.get("constraint_set")
    channel_state = None
    if isinstance(validation_payload, dict):
        channel_state = validation_payload.get("state")
    if channel_state is None and isinstance(constraint_payload, dict):
        channel_state = constraint_payload.get("state")
    if channel_state is None and observation is not None and observation.evidence_state is not None:
        channel_state = observation.evidence_state.value
    truth_source_kind = None if observation is None else observation.bridge_metrics.get("truth_source_kind")
    if truth_source_kind is None and truth_source_chain:
        truth_source_kind = truth_source_chain[0].get("kind")
    return {
        "enabled": enabled,
        "builder_status": (
            "disabled"
            if not enabled
            else "observation_materialized"
            if observation is not None
            else "applicability_only"
        ),
        "observation_present": observation is not None,
        "channel_state": channel_state,
        "evidence_state": None if observation is None or observation.evidence_state is None else observation.evidence_state.value,
        "scv_verdict": None if observation is None or observation.verdict is None else observation.verdict.value,
        "applicability": applicability,
        "channel_evidence_artifact": channel_evidence_artifact,
        "truth_source_kind": truth_source_kind,
        "truth_source_chain": truth_source_chain,
    }


def _builder_provenance_payload(
    *,
    snapshot: SidecarSnapshot,
    options: SidecarOptions,
    bundle: SCVObservationBundle,
    applicability_records: list[RunApplicabilityRecord],
) -> dict[str, Any]:
    return {
        "schema_version": BUILDER_PROVENANCE_SCHEMA_VERSION,
        "run_id": snapshot.run_id,
        "semantic_policy_version": SEMANTIC_POLICY_VERSION,
        "channels": {
            "path": _channel_record(
                channel_name="path",
                enabled=True,
                bundle=bundle,
                applicability_records=applicability_records,
                truth_source_chain=_path_truth_source_chain(snapshot),
                channel_evidence_artifact="channel_evidence_path.jsonl",
            ),
            "cap": _channel_record(
                channel_name="cap",
                enabled=options.cap_enabled,
                bundle=bundle,
                applicability_records=applicability_records,
                truth_source_chain=_cap_truth_source_chain(snapshot, enabled=options.cap_enabled),
                channel_evidence_artifact=("channel_evidence_cap.jsonl" if options.cap_enabled else None),
            ),
            "catalytic": _channel_record(
                channel_name="catalytic",
                enabled=options.catalytic_enabled,
                bundle=bundle,
                applicability_records=applicability_records,
                truth_source_chain=_catalytic_truth_source_chain(snapshot, enabled=options.catalytic_enabled),
                channel_evidence_artifact=(
                    "channel_evidence_catalytic.jsonl" if options.catalytic_enabled else None
                ),
            ),
        },
    }


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

    return CatalyticEvidenceChannel().evaluate(
        evidence_core_rows=evidence_core_rows,
        source=evidence_core_path,
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
    cap_evidences: list[Any] = []
    catalytic_evidences: list[Any] = []
    if options.cap_enabled:
        cap_result = _run_cap_channel(snapshot)
        cap_evidences = [] if cap_result.evidence is None else [cap_result.evidence]
    if options.catalytic_enabled:
        catalytic_result = _run_catalytic_channel(snapshot)
        catalytic_evidences = [] if catalytic_result.evidence is None else [catalytic_result.evidence]
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
    sink.write_jsonl("channel_evidence_path.jsonl", bundle_to_jsonl_rows(path_evidences), layer="layer1")
    if options.cap_enabled:
        sink.write_jsonl("channel_evidence_cap.jsonl", bundle_to_jsonl_rows(cap_evidences), layer="layer1")
    if options.catalytic_enabled:
        sink.write_jsonl(
            "channel_evidence_catalytic.jsonl",
            bundle_to_jsonl_rows(catalytic_evidences),
            layer="layer1",
        )
    builder_provenance_payload = _builder_provenance_payload(
        snapshot=snapshot,
        options=options,
        bundle=bundle,
        applicability_records=applicability_records,
    )
    sink.write_json("builder_provenance.json", builder_provenance_payload, layer="layer1")
    comparison_summary_payload: dict[str, Any] | None = None
    if comparator_options.enabled:
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
        sink.write_json("bridge_comparison_summary.json", comparison_summary_payload, layer="layer1")
        sink.write_jsonl("bridge_drift_attribution.jsonl", build_bridge_drift_rows(comparison_result), layer="layer1")
        sink.write_text(
            "bridge_operator_summary.md",
            build_bridge_operator_summary(comparison_result),
            layer="layer1",
            content_type="text/markdown; charset=utf-8",
        )
    path_channel_state = (
        ChannelState.OBSERVATION_MATERIALIZED
        if path_result.evidence is not None
        else ChannelState.APPLICABILITY_ONLY
    )
    cap_channel_state = (
        ChannelState.DISABLED
        if not options.cap_enabled
        else ChannelState.APPLICABILITY_ONLY
        if cap_result is not None and cap_result.evidence is None
        else ChannelState.OBSERVATION_MATERIALIZED
    )
    catalytic_channel_state = (
        ChannelState.DISABLED
        if not options.catalytic_enabled
        else ChannelState.APPLICABILITY_ONLY
        if catalytic_result is not None and catalytic_result.evidence is None
        else ChannelState.OBSERVATION_MATERIALIZED
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
        path_bridge_consumer_present=False,
        path_final_verdict_comparability_defined=False,
        report_guard_enabled=True,
        rc2_output_inventory_mutated=False,
        v3_lanes_required=False,
        channel_blockers={
            "path": (
                "path_bridge_consumer_missing",
                "path_final_verdict_comparability_undefined",
            ),
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
        channel_records=channel_records,
        bridge_diagnostics={
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
        },
    )
    sink.write_json("sidecar_run_record.json", asdict(run_record), layer="layer0")
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
