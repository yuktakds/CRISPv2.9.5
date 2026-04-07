from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from crisp.config.models import TargetConfig


class SCVVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCLEAR = "UNCLEAR"


class EvidenceState(StrEnum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class RunApplicabilityRecord:
    channel_name: str
    family: str
    scope: str
    applicable: bool
    reason_code: str
    detail: str | None = None
    diagnostics_source: str | None = None
    diagnostics_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChannelEvidence:
    channel_name: str
    family: str
    state: EvidenceState
    payload: dict[str, Any]
    source: str | None = None
    bridge_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChannelEvaluationResult:
    evidence: ChannelEvidence | None
    applicability_records: list[RunApplicabilityRecord] = field(default_factory=list)
    diagnostics_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SCVObservation:
    channel_name: str
    family: str
    verdict: SCVVerdict
    evidence_state: EvidenceState
    payload: dict[str, Any]
    source: str | None = None
    bridge_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SCVObservationBundle:
    schema_version: str
    run_id: str
    semantic_policy_version: str
    observations: list[SCVObservation]
    applicability_records: list[RunApplicabilityRecord] = field(default_factory=list)
    bridge_diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ArtifactDescriptor:
    logical_name: str
    relative_path: str
    layer: str
    content_type: str
    sha256: str
    byte_count: int


@dataclass(frozen=True, slots=True)
class GeneratorManifest:
    schema_version: str
    run_id: str
    output_root: str
    semantic_policy_version: str
    expected_output_digest: str
    outputs: list[ArtifactDescriptor]


@dataclass(frozen=True, slots=True)
class SidecarRunRecord:
    schema_version: str
    run_id: str
    run_mode: str
    output_root: str
    semantic_policy_version: str
    enabled_channels: list[str]
    observation_count: int
    applicability_records: list[RunApplicabilityRecord]
    materialized_outputs: list[str]
    rc2_output_digest_before: str
    rc2_output_digest_after: str
    rc2_outputs_unchanged: bool
    bridge_diagnostics: dict[str, Any] = field(default_factory=dict)
    expected_output_digest: str | None = None


@dataclass(frozen=True, slots=True)
class SidecarOptions:
    enabled: bool = False
    output_dirname: str = "v3_sidecar"


@dataclass(frozen=True, slots=True)
class SidecarSnapshot:
    run_id: str
    run_mode: str
    repo_root: str
    out_dir: str
    config_path: str
    integrated_config_path: str | None
    resource_profile: str
    comparison_type: str | None
    pathyes_mode_requested: str | None
    pathyes_force_false_requested: bool
    pat_diagnostics_path: str | None
    config: TargetConfig
    rc2_generated_outputs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SidecarRunResult:
    output_root: str
    materialized_outputs: list[str]
    expected_output_digest: str
    rc2_outputs_unchanged: bool

