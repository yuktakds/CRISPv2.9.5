from __future__ import annotations

import json
from collections import Counter
from numbers import Real
from pathlib import Path
from typing import Any

from crisp.v3.contracts import ChannelEvaluationResult, ChannelEvidence, EvidenceState, RunApplicabilityRecord
from crisp.v3.contracts.catalytic import CatalyticConstraintObservation, CatalyticConstraintState
from crisp.v3.projectors.catalytic import project_catalytic_payload

CATALYTIC_CHANNEL_NAME = "catalytic"
CATALYTIC_CHANNEL_FAMILY = "CATALYTIC"
_TRACE_ONLY_POLICY_VERSION = "v29.trace-only.noop"
_TRACE_ONLY_SEMANTIC_MODE = "trace-only-noop"
_CATALYTIC_INPUT_MISSING = "CATALYTIC_INPUT_MISSING"


def _normalize_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(payload, dict):
            return payload
    return {}


def _normalize_list(value: Any) -> list[Any] | None:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes, bytearray)):
        normalized = value.tolist()
        if isinstance(normalized, list):
            return normalized
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, list):
            return payload
    return None


def evaluate_catalytic_constraints(
    evidence_core_rows: list[dict[str, Any]],
) -> CatalyticConstraintObservation:
    record_count = len(evidence_core_rows)
    rows_with_proposal_trace = 0
    rows_with_candidate_order_hash = 0
    rows_with_stage_history = 0
    rows_with_trace_only_policy = 0
    rows_with_trace_only_semantic_mode = 0
    near_band_triggered_count = 0
    max_anchor_candidate_count = 0
    projected_best_target_distance: float | None = None
    policy_versions: set[str] = set()
    semantic_modes: set[str] = set()
    sample_molecule_ids: list[str] = []
    struct_conn_status_counts: Counter[str] = Counter()
    violation_markers: list[str] = []

    for index, row in enumerate(evidence_core_rows):
        trace_payload = _normalize_mapping(row.get("proposal_trace_json"))
        stage_history = _normalize_list(row.get("stage_history_json"))
        molecule_id = str(row.get("molecule_id", f"row-{index}"))
        sample_molecule_ids.append(molecule_id)

        if trace_payload:
            rows_with_proposal_trace += 1
        candidate_order_hash = row.get("candidate_order_hash") or trace_payload.get("candidate_order_hash")
        if candidate_order_hash:
            rows_with_candidate_order_hash += 1
        if stage_history is not None:
            rows_with_stage_history += 1

        policy_version = trace_payload.get("proposal_policy_version", row.get("proposal_policy_version"))
        if policy_version is not None:
            canonical_policy_version = str(policy_version)
            policy_versions.add(canonical_policy_version)
            if canonical_policy_version == _TRACE_ONLY_POLICY_VERSION:
                rows_with_trace_only_policy += 1
            else:
                violation_markers.append(f"policy:{molecule_id}")

        semantic_mode = trace_payload.get("semantic_mode")
        if semantic_mode is not None:
            canonical_semantic_mode = str(semantic_mode)
            semantic_modes.add(canonical_semantic_mode)
            if canonical_semantic_mode == _TRACE_ONLY_SEMANTIC_MODE:
                rows_with_trace_only_semantic_mode += 1
            else:
                violation_markers.append(f"semantic_mode:{molecule_id}")

        if trace_payload.get("near_band_triggered") is True:
            near_band_triggered_count += 1

        anchor_candidates = _normalize_list(trace_payload.get("anchor_candidate_atoms"))
        if anchor_candidates is not None:
            max_anchor_candidate_count = max(max_anchor_candidate_count, len(anchor_candidates))
        best_target_distance = row.get("best_target_distance")
        if isinstance(best_target_distance, Real) and not isinstance(best_target_distance, bool):
            best_target_distance = float(best_target_distance)
            projected_best_target_distance = (
                best_target_distance
                if projected_best_target_distance is None
                else min(projected_best_target_distance, best_target_distance)
            )

        struct_conn_status = trace_payload.get("struct_conn_status")
        if struct_conn_status is not None:
            struct_conn_status_counts[str(struct_conn_status)] += 1

    if violation_markers:
        state = CatalyticConstraintState.VIOLATED
        reason_code = "CATALYTIC_CONSTRAINT_VIOLATED"
    elif (
        rows_with_proposal_trace == record_count
        and rows_with_candidate_order_hash == record_count
        and rows_with_stage_history == record_count
        and rows_with_trace_only_policy == record_count
        and rows_with_trace_only_semantic_mode == record_count
    ):
        state = CatalyticConstraintState.SATISFIED
        reason_code = "CATALYTIC_TRACE_ONLY_CONSTRAINTS_OBSERVED"
    else:
        state = CatalyticConstraintState.PARTIAL
        reason_code = "CATALYTIC_TRACE_CONSTRAINTS_PARTIAL"

    return CatalyticConstraintObservation(
        state=state,
        reason_code=reason_code,
        record_count=record_count,
        rows_with_proposal_trace=rows_with_proposal_trace,
        rows_with_candidate_order_hash=rows_with_candidate_order_hash,
        rows_with_stage_history=rows_with_stage_history,
        rows_with_trace_only_policy=rows_with_trace_only_policy,
        rows_with_trace_only_semantic_mode=rows_with_trace_only_semantic_mode,
        near_band_triggered_count=near_band_triggered_count,
        max_anchor_candidate_count=max_anchor_candidate_count,
        observed_policy_versions=tuple(sorted(policy_versions)),
        observed_semantic_modes=tuple(sorted(semantic_modes)),
        sample_molecule_ids=tuple(sorted(sample_molecule_ids)),
        struct_conn_status_counts=dict(sorted(struct_conn_status_counts.items())),
        diagnostics={
            "expected_trace_only_policy_version": _TRACE_ONLY_POLICY_VERSION,
            "expected_trace_only_semantic_mode": _TRACE_ONLY_SEMANTIC_MODE,
            "violation_markers": tuple(sorted(violation_markers)),
            "projected_best_target_distance": projected_best_target_distance,
        },
    )


def _evidence_state(state: CatalyticConstraintState) -> EvidenceState:
    if state is CatalyticConstraintState.SATISFIED:
        return EvidenceState.SUPPORTED
    if state is CatalyticConstraintState.PARTIAL:
        return EvidenceState.INSUFFICIENT
    return EvidenceState.REFUTED


def _applicability_record(detail: str | None) -> RunApplicabilityRecord:
    return RunApplicabilityRecord(
        channel_name=CATALYTIC_CHANNEL_NAME,
        family=CATALYTIC_CHANNEL_FAMILY,
        scope="run",
        applicable=False,
        reason_code=_CATALYTIC_INPUT_MISSING,
        detail=detail,
        diagnostics_source=None,
        diagnostics_payload={},
    )


class CatalyticEvidenceChannel:
    def evaluate(
        self,
        *,
        evidence_core_rows: list[dict[str, Any]] | None,
        source: str | Path | None = None,
    ) -> ChannelEvaluationResult:
        if not evidence_core_rows:
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[_applicability_record("evidence_core rows are required for the catalytic sidecar stub")],
            )

        observation = evaluate_catalytic_constraints(evidence_core_rows)
        evidence = ChannelEvidence(
            channel_name=CATALYTIC_CHANNEL_NAME,
            family=CATALYTIC_CHANNEL_FAMILY,
            state=_evidence_state(observation.state),
            payload=project_catalytic_payload(observation),
            source=None if source is None else str(source),
            bridge_metrics={
                "constraint_state": observation.state.value,
                "record_count": observation.record_count,
                "missing_fields_not_inferred": True,
                "truth_source_kind": "read_only_evidence_core_snapshot",
            },
        )
        return ChannelEvaluationResult(
            evidence=evidence,
            applicability_records=[],
            diagnostics_payload={"record_count": observation.record_count},
        )
