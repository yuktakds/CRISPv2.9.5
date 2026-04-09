from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

from crisp.v3.policy import expected_output_digest_payload
from crisp.v3.ci_guards import (
    ALLOWED_REQUIRED_V3_JOB_NAMES,
    EXPLORATORY_JOB_NAME_PREFIX,
    EXPLORATORY_WORKFLOW_NAME_MARKER,
    REQUIRED_PROMOTION_BLOCKED_REASON,
    REQUIRED_WORKFLOW_PATH,
    V3_JOB_BODY_MARKERS,
    build_ci_separation_payload,
)
from crisp.v3.readiness.consistency import (
    RC2_INVENTORY_SOURCE,
    REQUIRED_TRUTH_SOURCE_FIELDS,
    SIDECAR_INVENTORY_SOURCE,
    build_inventory_authority_payload,
    derive_truth_source_record,
    find_truth_source_stage,
    reconstruct_truth_source_claims,
)


class GateStatus(str, Enum):
    PASS = "pass"
    BLOCKED = "blocked"
    OPEN = "open"
    NA = "na"


class ChannelState(str, Enum):
    DISABLED = "disabled"
    APPLICABILITY_ONLY = "applicability_only"
    OBSERVATION_MATERIALIZED = "observation_materialized"
    NOT_COMPARABLE = "not_comparable"

GATE_EVIDENCE_SCHEMA_VERSION = "crisp.v3.readiness_gate_evidence/v1"
ARTIFACT_GENERATOR_IDS = {
    "semantic_policy_version.json": "v3.semantic_policy_version/v1",
    "observation_bundle.json": "v3.observation_bundle/v1",
    "channel_evidence_path.jsonl": "v3.channel_evidence.path/v1",
    "channel_evidence_cap.jsonl": "v3.channel_evidence.cap/v1",
    "channel_evidence_catalytic.jsonl": "v3.channel_evidence.catalytic/v1",
    "builder_provenance.json": "v3.builder_provenance/v1",
    "sidecar_run_record.json": "v3.sidecar_run_record/v1",
    "verdict_record.json": "v3.verdict_record/v1",
    "preconditions_readiness.json": "v3.preconditions_readiness/v1",
    "generator_manifest.json": "v3.generator_manifest/v1",
    "bridge_operator_summary.md": "v3.bridge_operator_summary/v1",
    "run_drift_report.json": "v3.run_drift_report/v1",
    "required_ci_candidacy_report.json": "v3.required_ci_candidacy/v1",
    "internal_full_scv_observation_bundle.json": "v3.internal_full_scv_observation_bundle/v1",
    "shadow_stability_campaign.json": "v3.shadow_stability_campaign/v1",
    "sidecar_invariant_history.json": "v3.sidecar_invariant_history/v1",
    "metrics_drift_history.json": "v3.metrics_drift_history/v1",
    "windows_streak_history.json": "v3.windows_streak_history/v1",
}
ALLOWED_INPUT_SOURCE_KINDS = {
    "path": ("pat_diagnostics_json",),
    "cap": ("pair_features_snapshot",),
    "catalytic": ("evidence_core_snapshot",),
}
ALLOWED_TRUTH_SOURCE_KINDS = {
    "path": ("pat_diagnostics_json",),
    "cap": ("read_only_pair_features_snapshot",),
    "catalytic": ("read_only_evidence_core_snapshot",),
}


@dataclass(frozen=True, slots=True)
class TruthSourceAudit:
    channel_id: str
    status: GateStatus
    missing_fields: tuple[str, ...]
    record: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GateRecord:
    gate_id: str
    status: GateStatus
    detail: str


@dataclass(frozen=True, slots=True)
class ArtifactSectionReference:
    artifact_name: str
    generator_id: str
    section_id: str


@dataclass(frozen=True, slots=True)
class P2ChannelClaim:
    channel_id: str
    audit_status: str
    builder_provenance_ref: ArtifactSectionReference
    run_record_ref: ArtifactSectionReference
    source_label: str | None
    source_digest: str | None
    source_location_kind: str | None
    input_source_kind: str | None
    allowed_input_source_kinds: tuple[str, ...]
    truth_source_kind: str | None
    allowed_truth_source_kinds: tuple[str, ...]
    builder_identity: str | None
    projector_identity: str | None
    observation_artifact_ref: ArtifactSectionReference | None
    channel_evidence_artifact_ref: ArtifactSectionReference | None
    required_run_record_builder_status: str


@dataclass(frozen=True, slots=True)
class P2GateEvidence:
    schema_version: str
    builder_provenance_ref: ArtifactSectionReference
    sidecar_run_record_ref: ArtifactSectionReference
    channel_claims: dict[str, dict[str, Any]]


@dataclass(frozen=True, slots=True)
class P4GateEvidence:
    schema_version: str
    operator_report_refs: tuple[ArtifactSectionReference, ...]
    guarded_operator_report_refs: tuple[ArtifactSectionReference, ...]
    semantic_policy_version_required: bool
    mixed_summary_prohibited: bool
    exploratory_label_required_for_v3: bool
    rc2_primary_label_required: bool
    v3_secondary_label_required: bool
    verdict_match_rate_requires_full_comparability: bool


@dataclass(frozen=True, slots=True)
class P5GateEvidence:
    schema_version: str
    workflow_paths: tuple[str, ...]
    exploratory_workflow_paths: tuple[str, ...]
    required_workflow_paths: tuple[str, ...]
    exploratory_workflow_name_marker: str
    exploratory_job_name_prefix: str
    allowed_required_v3_job_names: tuple[str, ...]
    required_promotion_blocked_reason: str
    required_workflow_path: str
    v3_job_body_markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class P7GateEvidence:
    schema_version: str
    preconditions_ref: ArtifactSectionReference
    sidecar_run_record_ref: ArtifactSectionReference
    generator_manifest_ref: ArtifactSectionReference
    manifest_expected_output_digest_ref: ArtifactSectionReference
    required_manifest_entry_refs: tuple[ArtifactSectionReference, ...]
    descriptor_claims: dict[str, dict[str, Any]]


@dataclass(frozen=True, slots=True)
class PreconditionsReadiness:
    semantic_policy_version: str
    comparator_scope: str
    verdict_comparability: str
    comparable_channels: tuple[str, ...]
    full_migration_ready: bool
    channel_states: dict[str, str]
    channel_blockers: dict[str, tuple[str, ...]]
    truth_source_audits: dict[str, dict[str, Any]]
    gates: dict[str, dict[str, Any]]
    gate_evidence: dict[str, dict[str, Any]]
    inventory_authority: dict[str, Any]
    ci_status: dict[str, Any]

    def to_json_bytes(self) -> bytes:
        return json.dumps(asdict(self), indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _coerce_channel_state(value: ChannelState | str) -> ChannelState:
    if isinstance(value, ChannelState):
        return ChannelState.OBSERVATION_MATERIALIZED if value is ChannelState.NOT_COMPARABLE else value
    normalized = ChannelState(str(value))
    return ChannelState.OBSERVATION_MATERIALIZED if normalized is ChannelState.NOT_COMPARABLE else normalized


def _artifact_generator_id(artifact_name: str) -> str:
    return ARTIFACT_GENERATOR_IDS.get(artifact_name, "v3.unknown_artifact/v1")


def _artifact_ref(artifact_name: str, *, section_id: str) -> ArtifactSectionReference:
    return ArtifactSectionReference(
        artifact_name=artifact_name,
        generator_id=_artifact_generator_id(artifact_name),
        section_id=section_id,
    )


def _validate_artifact_ref(
    *,
    ref: Mapping[str, Any] | None,
    expected_artifact_name: str | None,
    expected_section_id: str | None,
    finding_prefix: str,
) -> list[str]:
    findings: list[str] = []
    if not isinstance(ref, Mapping):
        return [f"{finding_prefix} artifact reference is missing"]
    artifact_name = ref.get("artifact_name")
    generator_id = ref.get("generator_id")
    section_id = ref.get("section_id")
    if not artifact_name:
        findings.append(f"{finding_prefix} artifact_name is missing")
    if not generator_id:
        findings.append(f"{finding_prefix} generator_id is missing")
    if not section_id:
        findings.append(f"{finding_prefix} section_id is missing")
    if expected_artifact_name is not None and artifact_name != expected_artifact_name:
        findings.append(f"{finding_prefix} artifact_name mismatch")
    if artifact_name and generator_id and generator_id != _artifact_generator_id(str(artifact_name)):
        findings.append(f"{finding_prefix} generator_id mismatch")
    if expected_section_id is not None and section_id != expected_section_id:
        findings.append(f"{finding_prefix} section_id mismatch")
    return findings


def _derive_input_source_kind(channel_record: Mapping[str, Any] | None) -> str | None:
    if not channel_record:
        return None
    truth_source_chain_raw = channel_record.get("truth_source_chain")
    if isinstance(truth_source_chain_raw, (list, tuple)):
        input_stage = find_truth_source_stage(
            [dict(item) for item in truth_source_chain_raw if isinstance(item, Mapping)],
            "input_snapshot",
        )
        kind = input_stage.get("kind")
        return None if kind is None else str(kind)
    value = channel_record.get("input_source_kind")
    return None if value is None else str(value)


def _derive_truth_source_kind(channel_record: Mapping[str, Any] | None) -> str | None:
    if not channel_record:
        return None
    value = channel_record.get("truth_source_kind")
    return None if value is None else str(value)


def _required_run_record_builder_status(channel_state: ChannelState) -> str:
    if channel_state is ChannelState.DISABLED:
        return "disabled"
    if channel_state is ChannelState.APPLICABILITY_ONLY:
        return "applicability_only"
    return "observation_materialized"


def _descriptor_claim(descriptor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relative_path": descriptor.get("relative_path"),
        "layer": descriptor.get("layer"),
        "content_type": descriptor.get("content_type"),
        "sha256": descriptor.get("sha256"),
        "byte_count": descriptor.get("byte_count"),
    }


def _parse_operator_summary_fields(operator_summary: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "comparable_channels": None,
        "v3_only_evidence_channels": None,
        "v3_only_labels": {},
    }
    for raw_line in operator_summary.splitlines():
        line = raw_line.strip()
        if line.startswith("- comparable_channels: `") and line.endswith("`"):
            value = line[len("- comparable_channels: `") : -1]
            parsed["comparable_channels"] = [] if value == "none" else [item.strip() for item in value.split(",")]
        elif line.startswith("- v3_only_evidence_channels: `") and line.endswith("`"):
            value = line[len("- v3_only_evidence_channels: `") : -1]
            parsed["v3_only_evidence_channels"] = [] if value == "none" else [item.strip() for item in value.split(",")]
        elif line.startswith("- [v3-only] ") and ": `" in line and line.endswith("`"):
            body = line[len("- [v3-only] ") : -1]
            channel_name, lifecycle_state = body.split(": `", 1)
            parsed["v3_only_labels"][channel_name.strip()] = lifecycle_state.strip()
    return parsed


def audit_truth_source_chain(
    channel_id: str,
    record: Mapping[str, Any] | None,
    *,
    channel_state: ChannelState | str,
) -> TruthSourceAudit:
    state = _coerce_channel_state(channel_state)
    if state is ChannelState.DISABLED:
        return TruthSourceAudit(
            channel_id=channel_id,
            status=GateStatus.NA,
            missing_fields=(),
            record={},
        )

    truth_source_record = derive_truth_source_record(record)
    missing = tuple(
        field_name
        for field_name in REQUIRED_TRUTH_SOURCE_FIELDS
        if not truth_source_record.get(field_name)
    )
    return TruthSourceAudit(
        channel_id=channel_id,
        status=GateStatus.PASS if not missing else GateStatus.BLOCKED,
        missing_fields=missing,
        record=truth_source_record,
    )


def build_preconditions_readiness(
    *,
    semantic_policy_version: str,
    channel_states: Mapping[str, ChannelState | str],
    truth_source_records: Mapping[str, Mapping[str, Any] | None],
    comparable_channels: tuple[str, ...] = ("path",),
    comparator_scope: str = "path_only_partial",
    verdict_comparability: str = "not_comparable",
    path_adapter_coverage_frozen: bool = True,
    path_bridge_consumer_present: bool = False,
    path_final_verdict_comparability_defined: bool = False,
    report_guard_enabled: bool = True,
    rc2_output_inventory_mutated: bool = False,
    v3_lanes_required: bool = False,
    channel_blockers: Mapping[str, tuple[str, ...] | list[str]] | None = None,
    artifact_descriptors: Mapping[str, Mapping[str, Any]] | None = None,
    builder_provenance_artifact: str = "builder_provenance.json",
    sidecar_run_record_artifact: str = "sidecar_run_record.json",
    generator_manifest_artifact: str = "generator_manifest.json",
    preconditions_artifact: str = "preconditions_readiness.json",
    operator_report_artifacts: tuple[str, ...] = (),
    guarded_operator_artifacts: tuple[str, ...] = (),
    descriptor_digest_artifacts: tuple[str, ...] = (
        "semantic_policy_version.json",
        "builder_provenance.json",
    ),
    additional_required_artifacts: tuple[str, ...] = (),
) -> PreconditionsReadiness:
    raw_truth_source_records = {
        channel_id: truth_source_records.get(channel_id)
        for channel_id in ("path", "cap", "catalytic")
    }
    normalized_channel_states = {
        channel_id: _coerce_channel_state(channel_state)
        for channel_id, channel_state in channel_states.items()
    }
    audits = {
        channel_id: audit_truth_source_chain(
            channel_id,
            raw_truth_source_records.get(channel_id),
            channel_state=normalized_channel_states.get(channel_id, ChannelState.DISABLED),
        )
        for channel_id in ("path", "cap", "catalytic")
    }
    normalized_blockers = {
        "path": tuple(channel_blockers.get("path", ())) if channel_blockers is not None else (),
        "cap": tuple(channel_blockers.get("cap", ())) if channel_blockers is not None else (),
        "catalytic": tuple(channel_blockers.get("catalytic", ())) if channel_blockers is not None else (),
    }
    full_artifact_descriptors = {
        relative_path: _descriptor_claim(descriptor)
        for relative_path, descriptor in sorted((artifact_descriptors or {}).items())
    }
    descriptor_claims = {
        relative_path: descriptor
        for relative_path, descriptor in full_artifact_descriptors.items()
        if relative_path in descriptor_digest_artifacts
    }
    normalized_operator_report_artifacts = tuple(operator_report_artifacts)
    normalized_guarded_operator_artifacts = tuple(guarded_operator_artifacts)
    ci_status_payload = build_ci_separation_payload(v3_lanes_required=v3_lanes_required)

    p1 = GateRecord(
        gate_id="P1",
        status=(
            GateStatus.PASS
            if comparator_scope == "path_only_partial" and comparable_channels == ("path",)
            else GateStatus.BLOCKED
        ),
        detail="Comparator scope remains path-only partial; Cap / Catalytic are not implicitly promoted.",
    )
    p2 = GateRecord(
        gate_id="P2",
        status=(
            GateStatus.PASS
            if all(audit.status in {GateStatus.PASS, GateStatus.NA} for audit in audits.values())
            else GateStatus.BLOCKED
        ),
        detail="Truth-source chain completeness is audited from Layer 0 / Layer 1-facing records.",
    )
    p3 = GateRecord(
        gate_id="P3",
        status=(
            GateStatus.PASS
            if set(normalized_channel_states.keys()) >= {"path", "cap", "catalytic"}
            else GateStatus.BLOCKED
        ),
        detail="Channel readiness states remain explicit for path, cap, and catalytic.",
    )
    p4 = GateRecord(
        gate_id="P4",
        status=(
            GateStatus.PASS
            if report_guard_enabled
            and normalized_operator_report_artifacts == normalized_guarded_operator_artifacts
            else GateStatus.BLOCKED
        ),
        detail="Operator-facing mixed summary remains mechanically blocked.",
    )
    p5 = GateRecord(
        gate_id="P5",
        status=GateStatus.PASS if not v3_lanes_required else GateStatus.BLOCKED,
        detail="v3 sidecar lanes remain exploratory; required promotion is blocked.",
    )
    p6 = GateRecord(
        gate_id="P6",
        status=(
            GateStatus.PASS
            if path_adapter_coverage_frozen
            and path_bridge_consumer_present
            and path_final_verdict_comparability_defined
            and not normalized_blockers["path"]
            else GateStatus.BLOCKED
        ),
        detail=(
            "Path blocker status: "
            f"adapter_coverage_frozen={path_adapter_coverage_frozen}, "
            f"bridge_consumer_present={path_bridge_consumer_present}, "
            f"final_verdict_comparability_defined={path_final_verdict_comparability_defined}. "
            "Cap / Catalytic blocker closure remains open."
        ),
    )
    p7 = GateRecord(
        gate_id="P7",
        status=GateStatus.PASS if not rc2_output_inventory_mutated else GateStatus.BLOCKED,
        detail="Sidecar inventory authority remains generator_manifest; rc2 output_inventory stays untouched.",
    )

    gates = {record.gate_id: asdict(record) for record in (p1, p2, p3, p4, p5, p6, p7)}
    full_migration_ready = comparator_scope != "path_only_partial" and all(
        gate["status"] == GateStatus.PASS.value
        for gate in gates.values()
    )
    p2_channel_claims = {}
    for channel_id in ("path", "cap", "catalytic"):
        audit_record = audits[channel_id].record
        raw_record = raw_truth_source_records.get(channel_id)
        observation_artifact_pointer = audit_record.get("observation_artifact_pointer")
        channel_evidence_artifact_pointer = audit_record.get("channel_evidence_artifact_pointer")
        p2_channel_claims[channel_id] = asdict(
            P2ChannelClaim(
                channel_id=channel_id,
                audit_status=audits[channel_id].status.value,
                builder_provenance_ref=_artifact_ref(
                    builder_provenance_artifact,
                    section_id=f"channels.{channel_id}",
                ),
                run_record_ref=_artifact_ref(
                    sidecar_run_record_artifact,
                    section_id=f"channel_records.{channel_id}",
                ),
                source_label=audit_record.get("source_label"),
                source_digest=audit_record.get("source_digest"),
                source_location_kind=audit_record.get("source_location_kind"),
                input_source_kind=_derive_input_source_kind(raw_record),
                allowed_input_source_kinds=ALLOWED_INPUT_SOURCE_KINDS[channel_id],
                truth_source_kind=_derive_truth_source_kind(raw_record),
                allowed_truth_source_kinds=ALLOWED_TRUTH_SOURCE_KINDS[channel_id],
                builder_identity=audit_record.get("builder_identity"),
                projector_identity=audit_record.get("projector_identity"),
                observation_artifact_ref=(
                    None
                    if observation_artifact_pointer is None
                    else _artifact_ref(
                        str(observation_artifact_pointer),
                        section_id=f"observations.channel={channel_id}",
                    )
                ),
                channel_evidence_artifact_ref=(
                    None
                    if channel_evidence_artifact_pointer is None
                    else _artifact_ref(
                        str(channel_evidence_artifact_pointer),
                        section_id=f"channel_rows.channel={channel_id}",
                    )
                ),
                required_run_record_builder_status=_required_run_record_builder_status(
                    normalized_channel_states.get(channel_id, ChannelState.DISABLED)
                ),
            )
        )

    required_manifest_entries = tuple(
        sorted(
            {
                *full_artifact_descriptors.keys(),
                preconditions_artifact,
                sidecar_run_record_artifact,
                *additional_required_artifacts,
            }
        )
    )
    gate_evidence = {
        "P2": asdict(
            P2GateEvidence(
                schema_version=GATE_EVIDENCE_SCHEMA_VERSION,
                builder_provenance_ref=_artifact_ref(builder_provenance_artifact, section_id="channels"),
                sidecar_run_record_ref=_artifact_ref(sidecar_run_record_artifact, section_id="channel_records"),
                channel_claims=p2_channel_claims,
            )
        ),
        "P4": asdict(
            P4GateEvidence(
                schema_version=GATE_EVIDENCE_SCHEMA_VERSION,
                operator_report_refs=tuple(
                    _artifact_ref(artifact_name, section_id="rendered_document")
                    for artifact_name in normalized_operator_report_artifacts
                ),
                guarded_operator_report_refs=tuple(
                    _artifact_ref(artifact_name, section_id="guarded_render_path")
                    for artifact_name in normalized_guarded_operator_artifacts
                ),
                semantic_policy_version_required=True,
                mixed_summary_prohibited=True,
                exploratory_label_required_for_v3=True,
                rc2_primary_label_required=True,
                v3_secondary_label_required=True,
                verdict_match_rate_requires_full_comparability=True,
            )
        ),
        "P5": asdict(
            P5GateEvidence(
                schema_version=GATE_EVIDENCE_SCHEMA_VERSION,
                workflow_paths=tuple(ci_status_payload["workflow_paths"]),
                exploratory_workflow_paths=tuple(ci_status_payload["exploratory_workflow_paths"]),
                required_workflow_paths=tuple(ci_status_payload["required_workflow_paths"]),
                exploratory_workflow_name_marker=EXPLORATORY_WORKFLOW_NAME_MARKER,
                exploratory_job_name_prefix=EXPLORATORY_JOB_NAME_PREFIX,
                allowed_required_v3_job_names=ALLOWED_REQUIRED_V3_JOB_NAMES,
                required_promotion_blocked_reason=REQUIRED_PROMOTION_BLOCKED_REASON,
                required_workflow_path=REQUIRED_WORKFLOW_PATH,
                v3_job_body_markers=V3_JOB_BODY_MARKERS,
            )
        ),
        "P7": asdict(
            P7GateEvidence(
                schema_version=GATE_EVIDENCE_SCHEMA_VERSION,
                preconditions_ref=_artifact_ref(preconditions_artifact, section_id="root"),
                sidecar_run_record_ref=_artifact_ref(sidecar_run_record_artifact, section_id="materialized_outputs"),
                generator_manifest_ref=_artifact_ref(generator_manifest_artifact, section_id="outputs"),
                manifest_expected_output_digest_ref=_artifact_ref(
                    generator_manifest_artifact,
                    section_id="expected_output_digest",
                ),
                required_manifest_entry_refs=tuple(
                    _artifact_ref(artifact_name, section_id=f"outputs.relative_path={artifact_name}")
                    for artifact_name in required_manifest_entries
                ),
                descriptor_claims=descriptor_claims,
            )
        ),
    }

    return PreconditionsReadiness(
        semantic_policy_version=semantic_policy_version,
        comparator_scope=comparator_scope,
        verdict_comparability=verdict_comparability,
        comparable_channels=comparable_channels,
        full_migration_ready=full_migration_ready,
        channel_states={channel_id: state.value for channel_id, state in normalized_channel_states.items()},
        channel_blockers=normalized_blockers,
        truth_source_audits={channel_id: asdict(audit) for channel_id, audit in audits.items()},
        gates=gates,
        gate_evidence=gate_evidence,
        inventory_authority=build_inventory_authority_payload(
            rc2_output_inventory_mutated=rc2_output_inventory_mutated,
        ),
        ci_status=ci_status_payload,
    )


def audit_readiness_consistency(
    *,
    readiness: Mapping[str, Any],
    builder_provenance: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
    generator_manifest: Mapping[str, Any],
    operator_summary: str | None = None,
) -> tuple[str, ...]:
    findings: list[str] = []
    gate_evidence = readiness.get("gate_evidence", {})
    p2_evidence = gate_evidence.get("P2", {})
    p4_evidence = gate_evidence.get("P4", {})
    p5_evidence = gate_evidence.get("P5", {})
    p7_evidence = gate_evidence.get("P7", {})

    if p2_evidence.get("schema_version") != GATE_EVIDENCE_SCHEMA_VERSION:
        findings.append("P2 gate_evidence schema_version mismatch")
    if p4_evidence.get("schema_version") != GATE_EVIDENCE_SCHEMA_VERSION:
        findings.append("P4 gate_evidence schema_version mismatch")
    if p5_evidence.get("schema_version") != GATE_EVIDENCE_SCHEMA_VERSION:
        findings.append("P5 gate_evidence schema_version mismatch")
    if p7_evidence.get("schema_version") != GATE_EVIDENCE_SCHEMA_VERSION:
        findings.append("P7 gate_evidence schema_version mismatch")

    bridge_diagnostics = sidecar_run_record.get("bridge_diagnostics", {})
    p2_builder_ref = p2_evidence.get("builder_provenance_ref", {})
    p2_run_record_ref = p2_evidence.get("sidecar_run_record_ref", {})
    p7_preconditions_ref = p7_evidence.get("preconditions_ref", {})
    p7_manifest_ref = p7_evidence.get("generator_manifest_ref", {})
    findings.extend(
        _validate_artifact_ref(
            ref=p2_builder_ref,
            expected_artifact_name="builder_provenance.json",
            expected_section_id="channels",
            finding_prefix="P2 builder_provenance_ref",
        )
    )
    findings.extend(
        _validate_artifact_ref(
            ref=p2_run_record_ref,
            expected_artifact_name="sidecar_run_record.json",
            expected_section_id="channel_records",
            finding_prefix="P2 sidecar_run_record_ref",
        )
    )
    findings.extend(
        _validate_artifact_ref(
            ref=p7_preconditions_ref,
            expected_artifact_name="preconditions_readiness.json",
            expected_section_id="root",
            finding_prefix="P7 preconditions_ref",
        )
    )
    findings.extend(
        _validate_artifact_ref(
            ref=p7_manifest_ref,
            expected_artifact_name="generator_manifest.json",
            expected_section_id="outputs",
            finding_prefix="P7 generator_manifest_ref",
        )
    )
    if p2_builder_ref.get("artifact_name") != bridge_diagnostics.get("builder_provenance_artifact"):
        findings.append("P2 builder_provenance_artifact pointer mismatch")
    if p7_preconditions_ref.get("artifact_name") != bridge_diagnostics.get("preconditions_readiness_artifact"):
        findings.append("P7 preconditions_readiness_artifact pointer mismatch")
    if bridge_diagnostics.get("generator_manifest_artifact") != "generator_manifest.json":
        findings.append("P7 generator_manifest_artifact pointer mismatch")
    if p2_run_record_ref.get("artifact_name") != "sidecar_run_record.json":
        findings.append("P2 sidecar_run_record reference mismatch")
    if p7_manifest_ref.get("artifact_name") != "generator_manifest.json":
        findings.append("P7 generator_manifest reference mismatch")
    if p7_manifest_ref.get("artifact_name") != bridge_diagnostics.get("generator_manifest_artifact"):
        findings.append("P7 generator_manifest bridge_diagnostics pointer mismatch")
    expected_inventory_authority = build_inventory_authority_payload(rc2_output_inventory_mutated=False)
    for field_name, expected_value in expected_inventory_authority.items():
        if readiness.get("inventory_authority", {}).get(field_name) != expected_value:
            findings.append(f"P7 inventory_authority {field_name} mismatch")
    if bridge_diagnostics.get("sidecar_inventory_authority") != SIDECAR_INVENTORY_SOURCE:
        findings.append("P7 sidecar_inventory_authority mismatch")
    if bridge_diagnostics.get("rc2_inventory_authority") != RC2_INVENTORY_SOURCE:
        findings.append("P7 rc2_inventory_authority mismatch")

    channel_records = sidecar_run_record.get("channel_records", {})
    provenance_channels = builder_provenance.get("channels", {})
    truth_source_audits = readiness.get("truth_source_audits", {})
    reconstructed_claims = reconstruct_truth_source_claims(
        builder_provenance=builder_provenance,
        sidecar_run_record=sidecar_run_record,
        generator_manifest=generator_manifest,
    )
    for channel_id, claim in p2_evidence.get("channel_claims", {}).items():
        findings.extend(
            _validate_artifact_ref(
                ref=claim.get("builder_provenance_ref"),
                expected_artifact_name="builder_provenance.json",
                expected_section_id=f"channels.{channel_id}",
                finding_prefix=f"P2 {channel_id} builder_provenance_ref",
            )
        )
        findings.extend(
            _validate_artifact_ref(
                ref=claim.get("run_record_ref"),
                expected_artifact_name="sidecar_run_record.json",
                expected_section_id=f"channel_records.{channel_id}",
                finding_prefix=f"P2 {channel_id} run_record_ref",
            )
        )
        provenance_channel = provenance_channels.get(channel_id, {})
        derived_record = derive_truth_source_record(provenance_channel)
        reconstructed_claim = reconstructed_claims.get(channel_id, {})
        audit_status = truth_source_audits.get(channel_id, {}).get("status")
        if claim.get("audit_status") != audit_status:
            findings.append(f"P2 {channel_id} audit status mismatch")
        if audit_status == GateStatus.NA.value:
            continue
        for field_name in (
            "source_label",
            "source_digest",
            "source_location_kind",
            "builder_identity",
            "projector_identity",
        ):
            if claim.get(field_name) != derived_record.get(field_name):
                findings.append(f"P2 {channel_id} {field_name} does not reconstruct from builder_provenance")
            if claim.get(field_name) != reconstructed_claim.get(field_name):
                findings.append(f"P2 {channel_id} {field_name} does not reconstruct from layer0-1 artifacts")
        if claim.get("input_source_kind") != reconstructed_claim.get("input_source_kind"):
            findings.append(f"P2 {channel_id} input_source_kind does not reconstruct from layer0-1 artifacts")
        if (
            claim.get("required_run_record_builder_status") == "observation_materialized"
            and claim.get("truth_source_kind") != reconstructed_claim.get("truth_source_kind")
        ):
            findings.append(f"P2 {channel_id} truth_source_kind does not reconstruct from layer0-1 artifacts")
        run_record_channel = channel_records.get(channel_id, {})
        if run_record_channel.get("truth_source_chain") != provenance_channel.get("truth_source_chain"):
            findings.append(f"P2 {channel_id} truth_source_chain mismatch between run_record and builder_provenance")
        if not reconstructed_claim.get("truth_source_chain_matches", False):
            findings.append(f"P2 {channel_id} truth_source_chain is not reconstructable across builder_provenance and run_record")
        if not reconstructed_claim.get("required_fields_complete", False):
            findings.append(f"P2 {channel_id} required truth-source fields are not fully reconstructable")
        if not reconstructed_claim.get("builder_status_matches", False):
            findings.append(f"P2 {channel_id} builder_status mismatch between builder_provenance and run_record")
        if not reconstructed_claim.get("channel_state_matches", False):
            findings.append(f"P2 {channel_id} channel_state mismatch between builder_provenance and run_record")
        if not reconstructed_claim.get("observation_present_matches", False):
            findings.append(f"P2 {channel_id} observation_present mismatch between builder_provenance and run_record")
        duplicate_relative_paths = tuple(reconstructed_claim.get("manifest_duplicate_relative_paths", ()))
        if duplicate_relative_paths:
            findings.append(
                f"P7 generator_manifest contains duplicate relative_path entries: {', '.join(duplicate_relative_paths)}"
            )
        observation_artifact_ref = claim.get("observation_artifact_ref") or {}
        if derived_record.get("observation_artifact_pointer") is not None:
            findings.extend(
                _validate_artifact_ref(
                    ref=observation_artifact_ref,
                    expected_artifact_name=str(derived_record.get("observation_artifact_pointer")),
                    expected_section_id=f"observations.channel={channel_id}",
                    finding_prefix=f"P2 {channel_id} observation_artifact_ref",
                )
            )
        if observation_artifact_ref.get("artifact_name") != derived_record.get("observation_artifact_pointer"):
            findings.append(f"P2 {channel_id} observation_artifact pointer mismatch")
        observation_descriptor = reconstructed_claim.get("observation_artifact_descriptor")
        if derived_record.get("observation_artifact_pointer") is not None and not reconstructed_claim.get("observation_artifact_unique", False):
            findings.append(f"P2 {channel_id} observation_artifact pointer is not uniquely reconstructable from generator_manifest")
        if derived_record.get("observation_artifact_pointer") is not None and observation_descriptor is None:
            findings.append(f"P2 {channel_id} observation_artifact is missing from generator_manifest")
        channel_evidence_artifact_ref = claim.get("channel_evidence_artifact_ref") or {}
        if derived_record.get("channel_evidence_artifact_pointer") is not None:
            findings.extend(
                _validate_artifact_ref(
                    ref=channel_evidence_artifact_ref,
                    expected_artifact_name=str(derived_record.get("channel_evidence_artifact_pointer")),
                    expected_section_id=f"channel_rows.channel={channel_id}",
                    finding_prefix=f"P2 {channel_id} channel_evidence_artifact_ref",
                )
            )
        if channel_evidence_artifact_ref.get("artifact_name") != derived_record.get("channel_evidence_artifact_pointer"):
            findings.append(f"P2 {channel_id} channel_evidence claim does not reconstruct from builder_provenance")
        channel_evidence_descriptor = reconstructed_claim.get("channel_evidence_artifact_descriptor")
        if derived_record.get("channel_evidence_artifact_pointer") is not None and not reconstructed_claim.get("channel_evidence_artifact_unique", False):
            findings.append(f"P2 {channel_id} channel_evidence_artifact pointer is not uniquely reconstructable from generator_manifest")
        if derived_record.get("channel_evidence_artifact_pointer") is not None and channel_evidence_descriptor is None:
            findings.append(f"P2 {channel_id} channel_evidence_artifact is missing from generator_manifest")
        if channel_evidence_artifact_ref.get("artifact_name") != run_record_channel.get("channel_evidence_artifact"):
            findings.append(f"P2 {channel_id} channel_evidence artifact pointer mismatch")
        if claim.get("input_source_kind") not in set(claim.get("allowed_input_source_kinds", ())):
            findings.append(f"P2 {channel_id} input source kind is not in the allowed source classes")
        if (
            claim.get("required_run_record_builder_status") == "observation_materialized"
            and run_record_channel.get("truth_source_kind") not in set(claim.get("allowed_truth_source_kinds", ()))
        ):
            findings.append(f"P2 {channel_id} truth_source_kind is not in the allowed source classes")
        if claim.get("required_run_record_builder_status") != run_record_channel.get("builder_status"):
            findings.append(f"P2 {channel_id} run_record builder_status mismatch")
        expected_observation_present = claim.get("required_run_record_builder_status") == "observation_materialized"
        if bool(run_record_channel.get("observation_present")) != expected_observation_present:
            findings.append(f"P2 {channel_id} run_record observation_present mismatch")
        channel_state = run_record_channel.get("channel_state")
        if expected_observation_present and channel_state in (None, ""):
            findings.append(f"P2 {channel_id} run_record channel_state missing for materialized observation")
        if not expected_observation_present and channel_state not in (None, ""):
            findings.append(f"P2 {channel_id} run_record channel_state must be empty when observation is not materialized")
        if not reconstructed_claim.get("reconstruction_complete", False):
            findings.append(f"P2 {channel_id} truth-source reconstruction is incomplete")

    guarded_operator_artifacts = tuple(
        ref.get("artifact_name")
        for ref in p4_evidence.get("guarded_operator_report_refs", ())
        if isinstance(ref, Mapping)
    )
    operator_report_artifacts = tuple(
        ref.get("artifact_name")
        for ref in p4_evidence.get("operator_report_refs", ())
        if isinstance(ref, Mapping)
    )
    if operator_report_artifacts != guarded_operator_artifacts:
        findings.append("P4 guarded operator artifact coverage mismatch")
    for ref in p4_evidence.get("operator_report_refs", ()):
        if isinstance(ref, Mapping):
            findings.extend(
                _validate_artifact_ref(
                    ref=ref,
                    expected_artifact_name=str(ref.get("artifact_name")),
                    expected_section_id="rendered_document",
                    finding_prefix="P4 operator_report_ref",
                )
            )
    for ref in p4_evidence.get("guarded_operator_report_refs", ()):
        if isinstance(ref, Mapping):
            findings.extend(
                _validate_artifact_ref(
                    ref=ref,
                    expected_artifact_name=str(ref.get("artifact_name")),
                    expected_section_id="guarded_render_path",
                    finding_prefix="P4 guarded_operator_report_ref",
                )
            )
    if not p4_evidence.get("rc2_primary_label_required", False):
        findings.append("P4 rc2_primary_label_required must remain true")
    if not p4_evidence.get("v3_secondary_label_required", False):
        findings.append("P4 v3_secondary_label_required must remain true")

    expected_ci_status = build_ci_separation_payload(v3_lanes_required=False)
    for field_name, expected_value in expected_ci_status.items():
        if readiness.get("ci_status", {}).get(field_name) != expected_value:
            findings.append(f"P5 ci_status {field_name} mismatch")
    if tuple(p5_evidence.get("workflow_paths", ())) != tuple(expected_ci_status["workflow_paths"]):
        findings.append("P5 workflow_paths mismatch")
    if p5_evidence.get("exploratory_job_name_prefix") != EXPLORATORY_JOB_NAME_PREFIX:
        findings.append("P5 exploratory_job_name_prefix mismatch")
    if p5_evidence.get("exploratory_workflow_name_marker") != EXPLORATORY_WORKFLOW_NAME_MARKER:
        findings.append("P5 exploratory_workflow_name_marker mismatch")
    if tuple(p5_evidence.get("exploratory_workflow_paths", ())) != tuple(expected_ci_status["exploratory_workflow_paths"]):
        findings.append("P5 exploratory_workflow_paths mismatch")
    if tuple(p5_evidence.get("required_workflow_paths", ())) != tuple(expected_ci_status["required_workflow_paths"]):
        findings.append("P5 required_workflow_paths mismatch")
    if tuple(p5_evidence.get("allowed_required_v3_job_names", ())) != ALLOWED_REQUIRED_V3_JOB_NAMES:
        findings.append("P5 allowed_required_v3_job_names mismatch")
    if p5_evidence.get("required_promotion_blocked_reason") != REQUIRED_PROMOTION_BLOCKED_REASON:
        findings.append("P5 required_promotion_blocked_reason mismatch")
    if p5_evidence.get("required_workflow_path") != REQUIRED_WORKFLOW_PATH:
        findings.append("P5 required_workflow_path mismatch")
    if tuple(p5_evidence.get("v3_job_body_markers", ())) != V3_JOB_BODY_MARKERS:
        findings.append("P5 v3_job_body_markers mismatch")

    run_record_comparable_channels = tuple(str(item) for item in sidecar_run_record.get("comparable_channels", ()))
    readiness_comparable_channels = tuple(str(item) for item in readiness.get("comparable_channels", ()))
    bridge_comparator_enabled = bool(bridge_diagnostics.get("bridge_comparator_enabled"))
    if bridge_comparator_enabled and run_record_comparable_channels != readiness_comparable_channels:
        findings.append("P3 comparable_channels mismatch between readiness and run_record")
    if set(run_record_comparable_channels) - {"path"}:
        findings.append("P3 comparable_channels contains non-FROZEN channel")
    v3_only_evidence_channels = tuple(
        str(item) for item in sidecar_run_record.get("v3_only_evidence_channels", ())
    )
    if set(v3_only_evidence_channels) & set(run_record_comparable_channels):
        findings.append("P3 v3_only_evidence_channels overlaps comparable_channels")
    channel_lifecycle_states = {
        str(channel_id): str(state)
        for channel_id, state in sidecar_run_record.get("channel_lifecycle_states", {}).items()
    }
    for channel_id, state in channel_lifecycle_states.items():
        if state not in {
            ChannelState.DISABLED.value,
            ChannelState.APPLICABILITY_ONLY.value,
            ChannelState.OBSERVATION_MATERIALIZED.value,
        }:
            findings.append(f"P3 {channel_id} channel_lifecycle_state is not a primary lifecycle state")
    for channel_id in v3_only_evidence_channels:
        if channel_lifecycle_states.get(channel_id) != ChannelState.OBSERVATION_MATERIALIZED.value:
            findings.append(f"P3 {channel_id} v3_only_evidence channel must be observation_materialized")
    bridge_summary = bridge_diagnostics.get("bridge_comparison_summary")
    if isinstance(bridge_summary, Mapping):
        if tuple(str(item) for item in bridge_summary.get("comparable_channels", ())) != run_record_comparable_channels:
            findings.append("P3 bridge summary comparable_channels mismatch")
        if tuple(str(item) for item in bridge_summary.get("v3_only_evidence_channels", ())) != v3_only_evidence_channels:
            findings.append("P3 bridge summary v3_only_evidence_channels mismatch")
        if {
            str(channel_id)
            for channel_id in (bridge_summary.get("component_matches") or {}).keys()
        } & set(v3_only_evidence_channels):
            findings.append("P3 bridge summary component_matches must exclude v3-only channels")
    if operator_summary is not None:
        parsed_operator_summary = _parse_operator_summary_fields(operator_summary)
        if parsed_operator_summary.get("comparable_channels") != list(run_record_comparable_channels):
            findings.append("P4 operator_summary comparable_channels mismatch")
        if parsed_operator_summary.get("v3_only_evidence_channels") != list(v3_only_evidence_channels):
            findings.append("P4 operator_summary v3_only_evidence_channels mismatch")
        expected_v3_only_labels = {
            channel_id: channel_lifecycle_states.get(channel_id)
            for channel_id in v3_only_evidence_channels
        }
        if parsed_operator_summary.get("v3_only_labels") != expected_v3_only_labels:
            findings.append("P4 operator_summary v3-only lifecycle labels mismatch")
        if v3_only_evidence_channels and "[v3-only]" not in operator_summary:
            findings.append("P4 operator_summary must visibly label v3-only evidence")

    manifest_outputs = {
        str(item.get("relative_path")): item
        for item in generator_manifest.get("outputs", [])
        if isinstance(item, Mapping)
    }
    materialized_outputs = {
        str(item)
        for item in sidecar_run_record.get("materialized_outputs", [])
    }
    manifest_expected_output_digest_ref = p7_evidence.get("manifest_expected_output_digest_ref", {})
    findings.extend(
        _validate_artifact_ref(
            ref=manifest_expected_output_digest_ref,
            expected_artifact_name="generator_manifest.json",
            expected_section_id="expected_output_digest",
            finding_prefix="P7 manifest_expected_output_digest_ref",
        )
    )
    if manifest_expected_output_digest_ref.get("artifact_name") != "generator_manifest.json":
        findings.append("P7 expected_output_digest reference does not point at generator_manifest")
    if manifest_expected_output_digest_ref.get("section_id") != "expected_output_digest":
        findings.append("P7 expected_output_digest section reference mismatch")
    if not generator_manifest.get("expected_output_digest"):
        findings.append("P7 generator_manifest expected_output_digest is missing")
    elif generator_manifest.get("expected_output_digest") != expected_output_digest_payload(generator_manifest.get("outputs", [])):
        findings.append("P7 generator_manifest expected_output_digest does not match manifest outputs")
    for artifact_name in guarded_operator_artifacts:
        if artifact_name not in materialized_outputs:
            findings.append(f"P4 guarded operator artifact missing from run_record: {artifact_name}")
        if artifact_name not in manifest_outputs:
            findings.append(f"P4 guarded operator artifact missing from generator_manifest: {artifact_name}")

    required_manifest_entries = set()
    for ref in p7_evidence.get("required_manifest_entry_refs", ()):
        if isinstance(ref, Mapping):
            findings.extend(
                _validate_artifact_ref(
                    ref=ref,
                    expected_artifact_name=str(ref.get("artifact_name")),
                    expected_section_id=f"outputs.relative_path={ref.get('artifact_name')}",
                    finding_prefix="P7 required_manifest_entry_ref",
                )
            )
            required_manifest_entries.add(str(ref.get("artifact_name")))
    if materialized_outputs != required_manifest_entries:
        findings.append("P7 run_record materialized_outputs do not match readiness required_manifest_entries")
    for artifact_name in required_manifest_entries:
        if artifact_name not in manifest_outputs:
            findings.append(f"P7 generator_manifest missing required entry: {artifact_name}")
    for artifact_name, descriptor_claim in p7_evidence.get("descriptor_claims", {}).items():
        manifest_descriptor = manifest_outputs.get(str(artifact_name))
        if manifest_descriptor is None:
            findings.append(f"P7 generator_manifest missing descriptor for {artifact_name}")
            continue
        for field_name in ("relative_path", "layer", "content_type", "sha256", "byte_count"):
            if descriptor_claim.get(field_name) != manifest_descriptor.get(field_name):
                findings.append(f"P7 descriptor mismatch for {artifact_name}.{field_name}")

    return tuple(findings)
