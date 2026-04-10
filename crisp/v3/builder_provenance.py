from __future__ import annotations

from typing import Any

from crisp.v3.contracts import (
    RunApplicabilityRecord,
    SCVObservationBundle,
    SidecarOptions,
    SidecarSnapshot,
)
from crisp.v3.policy import BUILDER_PROVENANCE_SCHEMA_VERSION, SEMANTIC_POLICY_VERSION
from crisp.v3.source_provenance import (
    _cap_truth_source_chain,
    _catalytic_truth_source_chain,
    _path_truth_source_chain,
)


def _applicability_rows(
    records: list[RunApplicabilityRecord],
    *,
    channel_name: str,
) -> list[dict[str, Any]]:
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


def build_builder_provenance_payload(
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
