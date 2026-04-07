from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


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


REQUIRED_TRUTH_SOURCE_FIELDS = (
    "source_label",
    "source_digest",
    "source_location_kind",
    "builder_identity",
    "projector_identity",
    "observation_artifact_pointer",
)


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
    inventory_authority: dict[str, Any]
    ci_status: dict[str, Any]

    def to_json_bytes(self) -> bytes:
        return json.dumps(asdict(self), indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _coerce_channel_state(value: ChannelState | str) -> ChannelState:
    if isinstance(value, ChannelState):
        return value
    return ChannelState(str(value))


def _find_truth_source_stage(
    truth_source_chain: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    stage_name: str,
) -> dict[str, Any]:
    for item in truth_source_chain:
        if str(item.get("stage")) == stage_name:
            return dict(item)
    return {}


def derive_truth_source_record(channel_record: Mapping[str, Any] | None) -> dict[str, Any]:
    if not channel_record:
        return {}
    if any(field_name in channel_record for field_name in REQUIRED_TRUTH_SOURCE_FIELDS):
        return {
            field_name: channel_record.get(field_name)
            for field_name in REQUIRED_TRUTH_SOURCE_FIELDS
        } | {
            "channel_evidence_artifact_pointer": channel_record.get("channel_evidence_artifact_pointer"),
        }
    truth_source_chain_raw = channel_record.get("truth_source_chain")
    if not isinstance(truth_source_chain_raw, (list, tuple)):
        return {}
    truth_source_chain = [
        dict(item)
        for item in truth_source_chain_raw
        if isinstance(item, Mapping)
    ]
    input_stage = _find_truth_source_stage(truth_source_chain, "input_snapshot")
    builder_stage = _find_truth_source_stage(truth_source_chain, "channel_builder")
    bridge_stage = _find_truth_source_stage(truth_source_chain, "bridge_route")
    return {
        "source_label": input_stage.get("source_label"),
        "source_digest": input_stage.get("source_digest"),
        "source_location_kind": input_stage.get("source_location_kind"),
        "builder_identity": builder_stage.get("builder"),
        "projector_identity": builder_stage.get("projector"),
        "observation_artifact_pointer": bridge_stage.get("observation_artifact"),
        "channel_evidence_artifact_pointer": (
            builder_stage.get("channel_evidence_artifact")
            or channel_record.get("channel_evidence_artifact")
        ),
    }


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
) -> PreconditionsReadiness:
    normalized_channel_states = {
        channel_id: _coerce_channel_state(channel_state)
        for channel_id, channel_state in channel_states.items()
    }
    audits = {
        channel_id: audit_truth_source_chain(
            channel_id,
            truth_source_records.get(channel_id),
            channel_state=normalized_channel_states.get(channel_id, ChannelState.DISABLED),
        )
        for channel_id in ("path", "cap", "catalytic")
    }
    normalized_blockers = {
        "path": tuple(channel_blockers.get("path", ())) if channel_blockers is not None else (),
        "cap": tuple(channel_blockers.get("cap", ())) if channel_blockers is not None else (),
        "catalytic": tuple(channel_blockers.get("catalytic", ())) if channel_blockers is not None else (),
    }

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
        status=GateStatus.PASS if report_guard_enabled else GateStatus.BLOCKED,
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
            and not any(normalized_blockers.values())
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
    full_migration_ready = all(
        gate["status"] == GateStatus.PASS.value
        for gate in gates.values()
    )

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
        inventory_authority={
            "sidecar_inventory_source": "v3_sidecar/generator_manifest.json",
            "rc2_inventory_source": "output_inventory.json",
            "rc2_inventory_mutated": rc2_output_inventory_mutated,
        },
        ci_status={
            "v3_lanes_required": v3_lanes_required,
            "rc2_frozen_suite_untouched": True,
        },
    )
