from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


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
    "vn06_readiness.json": "v3.vn06_readiness/v1",
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
