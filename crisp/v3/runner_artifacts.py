from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from crisp.repro.hashing import sha256_file, sha256_json
from crisp.v3.artifacts.sink import ArtifactSink
from crisp.v3.contracts import (
    SCVObservationBundle,
    SidecarOptions,
    SidecarRunRecord,
    SidecarRunResult,
    SidecarSnapshot,
)
from crisp.v3.policy import (
    CAP_CHANNEL_NAME,
    CATALYTIC_CHANNEL_NAME,
    PATH_CHANNEL_NAME,
    SEMANTIC_POLICY_VERSION,
    SIDECAR_RUN_RECORD_SCHEMA_VERSION,
    semantic_policy_payload,
)
from crisp.v3.report_guards import (
    enforce_shadow_stability_campaign_guard,
    enforce_verdict_record_dual_write_guard,
)
from crisp.v3.runner_authority import Layer0AuthorityAssembly
from crisp.v3.scv_bridge import bundle_to_jsonl_rows
from crisp.v3.shadow_stability import (
    METRICS_DRIFT_HISTORY_ARTIFACT,
    SHADOW_STABILITY_CAMPAIGN_ARTIFACT,
    SIDECAR_INVARIANT_HISTORY_ARTIFACT,
    WINDOWS_STREAK_HISTORY_ARTIFACT,
    build_shadow_stability_campaign,
    shadow_stability_campaign_to_payload,
)
from crisp.v3.vn06_readiness import VN06_READINESS_ARTIFACT, evaluate_vn06_readiness


class SidecarInvariantError(RuntimeError):
    pass


def rc2_output_state(run_dir: Path, *, sidecar_dirname: str) -> tuple[dict[str, str], str]:
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


def emit_semantic_policy_artifact(*, sink: ArtifactSink) -> None:
    sink.write_json("semantic_policy_version.json", semantic_policy_payload(), layer="layer0")


def emit_bundle_artifacts(
    *,
    sink: ArtifactSink,
    options: SidecarOptions,
    bundle: SCVObservationBundle,
    path_evidences: list[Any],
    cap_evidences: list[Any],
    catalytic_evidences: list[Any],
    builder_provenance_payload: dict[str, Any],
    internal_full_bundle: SCVObservationBundle | None,
) -> None:
    sink.write_json("observation_bundle.json", asdict(bundle), layer="layer1")
    if internal_full_bundle is not None:
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
    sink.write_json("builder_provenance.json", builder_provenance_payload, layer="layer1")


def emit_shadow_stability_artifacts(
    *,
    sink: ArtifactSink,
    run_id: str,
    rc2_digest_before: str,
    rc2_digest_midrun: str,
    run_drift_report_payload: dict[str, Any] | None,
) -> None:
    sidecar_invariant_history = [rc2_digest_before == rc2_digest_midrun]
    metrics_drift_history = [
        0 if run_drift_report_payload is None else int(run_drift_report_payload["metrics_drift_count"])
    ]
    windows_streak_history = [True]
    run_drift_report_digest_history = []
    if "run_drift_report.json" in sink.descriptor_payload():
        run_drift_report_digest_history = [sink.descriptor_payload()["run_drift_report.json"]["sha256"]]
    campaign = build_shadow_stability_campaign(
        run_id=run_id,
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


def finalize_sidecar_run(
    *,
    sink: ArtifactSink,
    snapshot: SidecarSnapshot,
    options: SidecarOptions,
    run_dir: Path,
    rc2_state_before: dict[str, str],
    rc2_digest_before: str,
    rc2_digest_after: str,
    bundle: SCVObservationBundle,
    applicability_records: list[Any],
    channel_evidence_states: dict[str, str | None],
    channel_comparability: dict[str, Any],
    path_component_match: bool | None,
    builder_provenance_payload: dict[str, Any],
    preconditions_readiness_payload: Any,
    authority: Layer0AuthorityAssembly,
) -> SidecarRunResult:
    sink.write_json(
        "preconditions_readiness.json",
        asdict(preconditions_readiness_payload),
        layer="layer0",
    )

    materialized_before_manifest = [
        *sink.materialized_outputs(),
        "sidecar_run_record.json",
        "verdict_record.json",
        VN06_READINESS_ARTIFACT,
    ]
    channel_records = {
        PATH_CHANNEL_NAME: builder_provenance_payload["channels"][PATH_CHANNEL_NAME],
        CAP_CHANNEL_NAME: builder_provenance_payload["channels"][CAP_CHANNEL_NAME],
        CATALYTIC_CHANNEL_NAME: builder_provenance_payload["channels"][CATALYTIC_CHANNEL_NAME],
    }
    run_record = SidecarRunRecord(
        schema_version=SIDECAR_RUN_RECORD_SCHEMA_VERSION,
        run_id=snapshot.run_id,
        run_mode=snapshot.run_mode,
        output_root=authority.authority_fields_payload["output_root"],
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        enabled_channels=authority.enabled_channels,
        observation_count=len(bundle.observations),
        applicability_records=applicability_records,
        materialized_outputs=materialized_before_manifest,
        rc2_output_digest_before=rc2_digest_before,
        rc2_output_digest_after=rc2_digest_after,
        rc2_outputs_unchanged=rc2_digest_before == rc2_digest_after,
        comparator_scope=authority.authority_fields_payload["comparator_scope"],
        comparable_channels=authority.authority_fields_payload["comparable_channels"],
        v3_only_evidence_channels=authority.authority_fields_payload["v3_only_evidence_channels"],
        channel_lifecycle_states=authority.authority_fields_payload["channel_lifecycle_states"],
        channel_evidence_states=channel_evidence_states,
        channel_comparability=channel_comparability,
        path_component_match=path_component_match,
        channel_records=channel_records,
        bridge_diagnostics=authority.bridge_diagnostics,
    )
    sink.write_json("sidecar_run_record.json", asdict(run_record), layer="layer0")
    enforce_verdict_record_dual_write_guard(
        verdict_record=authority.verdict_record_payload,
        sidecar_run_record=asdict(run_record),
    )
    sink.write_json("verdict_record.json", authority.verdict_record_payload, layer="layer0")
    manifest_candidate = sink.manifest_payload(run_id=snapshot.run_id)
    vn06_readiness_payload = evaluate_vn06_readiness(
        verdict_record=authority.verdict_record_payload,
        sidecar_run_record=asdict(run_record),
        manifest_outputs=[asdict(descriptor) for descriptor in manifest_candidate.outputs],
    )
    sink.write_json(VN06_READINESS_ARTIFACT, vn06_readiness_payload, layer="layer0")
    manifest_path, expected_output_digest = sink.write_generator_manifest(run_id=snapshot.run_id)

    rc2_state_after, rc2_digest_after_final = rc2_output_state(
        run_dir,
        sidecar_dirname=options.output_dirname,
    )
    if rc2_digest_before != rc2_digest_after_final or rc2_state_before != rc2_state_after:
        raise SidecarInvariantError("v3 sidecar mutated existing rc2 outputs")

    return SidecarRunResult(
        output_root=authority.authority_fields_payload["output_root"],
        materialized_outputs=[*sink.materialized_outputs(), manifest_path.name],
        expected_output_digest=expected_output_digest,
        rc2_outputs_unchanged=True,
    )
