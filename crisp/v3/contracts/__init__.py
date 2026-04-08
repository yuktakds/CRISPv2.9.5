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


class ComparisonScope(StrEnum):
    PATH_ONLY_PARTIAL = "path_only_partial"
    FULL_CHANNEL_BUNDLE = "full_channel_bundle"


class VerdictComparability(StrEnum):
    NOT_COMPARABLE = "not_comparable"
    PARTIALLY_COMPARABLE = "partially_comparable"
    COMPARABLE = "comparable"


class CompoundPathComparability(StrEnum):
    NOT_COMPARABLE = "not_comparable"
    EVIDENCE_COMPARABLE = "evidence_comparable"
    COMPONENT_VERDICT_COMPARABLE = "component_verdict_comparable"


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
    verdict: SCVVerdict | None
    evidence_state: EvidenceState | None
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
    comparator_scope: str | None = None
    comparable_channels: list[str] = field(default_factory=list)
    channel_evidence_states: dict[str, str | None] = field(default_factory=dict)
    channel_comparability: dict[str, str | None] = field(default_factory=dict)
    path_component_match: bool | None = None
    channel_records: dict[str, Any] = field(default_factory=dict)
    bridge_diagnostics: dict[str, Any] = field(default_factory=dict)
    expected_output_digest: str | None = None


@dataclass(frozen=True, slots=True)
class SidecarOptions:
    enabled: bool = False
    output_dirname: str = "v3_sidecar"
    cap_enabled: bool = False
    catalytic_enabled: bool = False


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
    cap_pair_features_path: str | None = None


@dataclass(frozen=True, slots=True)
class SidecarRunResult:
    output_root: str
    materialized_outputs: list[str]
    expected_output_digest: str
    rc2_outputs_unchanged: bool


@dataclass(frozen=True, slots=True)
class BridgeComparatorOptions:
    enabled: bool = False


@dataclass(frozen=True, slots=True)
class RC2AdaptResult:
    bundle: SCVObservationBundle
    coverage_channels: tuple[str, ...]
    unavailable_channels: tuple[str, ...]
    notes: tuple[str, ...]
    reference_kind: str


@dataclass(frozen=True, slots=True)
class DriftRecord:
    channel_name: str
    drift_kind: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompoundDriftReport:
    channel_name: str
    component_comparability: dict[str, str]
    component_matches: dict[str, bool | None]
    rc2_component_verdicts: dict[str, str | None] = field(default_factory=dict)
    v3_component_verdicts: dict[str, str | None] = field(default_factory=dict)
    rc2_component_states: dict[str, str | None] = field(default_factory=dict)
    v3_component_states: dict[str, str | None] = field(default_factory=dict)
    v3_shadow_verdict: str | None = None
    verdict_match: bool | None = None
    drifts: tuple[DriftRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RunDriftReport:
    comparator_scope: ComparisonScope
    comparable_channels: tuple[str, ...]
    comparable_subset_size: int
    component_verdict_comparable_count: int
    component_match_count: int
    verdict_match_count: int | None = None
    verdict_mismatch_count: int | None = None
    path_component_match_rate: float | None = None
    coverage_drift_count: int = 0
    applicability_drift_count: int = 0
    metrics_drift_count: int = 0
    witness_drift_count: int = 0


@dataclass(frozen=True, slots=True)
class BridgeComparisonSummary:
    semantic_policy_version: str
    comparison_scope: ComparisonScope
    verdict_comparability: VerdictComparability
    rc2_reference_kind: str
    v3_shadow_kind: str
    comparable_channels: tuple[str, ...]
    unavailable_channels: tuple[str, ...]
    run_level_flags: tuple[str, ...]
    channel_coverage: dict[str, str] = field(default_factory=dict)
    channel_comparability: dict[str, str] = field(default_factory=dict)
    component_matches: dict[str, bool | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BridgeComparisonResult:
    summary: BridgeComparisonSummary
    run_report: RunDriftReport
    compound_reports: tuple[CompoundDriftReport, ...]
    drifts: tuple[DriftRecord, ...]
