from __future__ import annotations

from crisp.v3.channels.catalytic import CatalyticEvidenceChannel, evaluate_catalytic_constraints
from crisp.v3.contracts import EvidenceState
from crisp.v3.contracts.catalytic import CatalyticConstraintState


def _trace_only_rows() -> list[dict[str, object]]:
    return [
        {
            "molecule_id": "m1",
            "candidate_order_hash": "sha256:a",
            "proposal_policy_version": "v29.trace-only.noop",
            "stage_history_json": [{"stage_id": 1}],
            "proposal_trace_json": {
                "proposal_policy_version": "v29.trace-only.noop",
                "semantic_mode": "trace-only-noop",
                "candidate_order_hash": "sha256:a",
                "near_band_triggered": True,
                "anchor_candidate_atoms": [0, 1, 2],
                "struct_conn_status": "present",
            },
        },
        {
            "molecule_id": "m2",
            "candidate_order_hash": "sha256:b",
            "proposal_policy_version": "v29.trace-only.noop",
            "stage_history_json": [],
            "proposal_trace_json": {
                "proposal_policy_version": "v29.trace-only.noop",
                "semantic_mode": "trace-only-noop",
                "candidate_order_hash": "sha256:b",
                "near_band_triggered": False,
                "anchor_candidate_atoms": [0, 1],
                "struct_conn_status": "missing",
            },
        },
    ]


def test_catalytic_constraints_mark_satisfied_for_trace_only_snapshot() -> None:
    observation = evaluate_catalytic_constraints(_trace_only_rows())

    assert observation.state is CatalyticConstraintState.SATISFIED
    assert observation.reason_code == "CATALYTIC_TRACE_ONLY_CONSTRAINTS_OBSERVED"
    assert observation.rows_with_proposal_trace == 2
    assert observation.rows_with_candidate_order_hash == 2
    assert observation.rows_with_stage_history == 2
    assert observation.rows_with_trace_only_policy == 2
    assert observation.rows_with_trace_only_semantic_mode == 2
    assert observation.near_band_triggered_count == 1
    assert observation.max_anchor_candidate_count == 3


def test_catalytic_channel_marks_partial_when_trace_fields_are_missing() -> None:
    rows = _trace_only_rows()
    rows[1] = {
        "molecule_id": "m2",
        "candidate_order_hash": "sha256:b",
        "proposal_policy_version": "v29.trace-only.noop",
    }

    result = CatalyticEvidenceChannel().evaluate(evidence_core_rows=rows)

    assert result.evidence is not None
    assert result.evidence.state is EvidenceState.INSUFFICIENT
    assert result.evidence.payload["constraint_set"]["state"] == "PARTIAL"
    assert result.evidence.payload["constraint_set"]["reason_code"] == "CATALYTIC_TRACE_CONSTRAINTS_PARTIAL"


def test_catalytic_channel_marks_violated_when_trace_only_policy_is_broken() -> None:
    rows = _trace_only_rows()
    rows[0]["proposal_trace_json"] = {
        "proposal_policy_version": "v29.proposal-connected",
        "semantic_mode": "proposal-connected",
        "candidate_order_hash": "sha256:a",
    }

    result = CatalyticEvidenceChannel().evaluate(evidence_core_rows=rows)

    assert result.evidence is not None
    assert result.evidence.state is EvidenceState.REFUTED
    assert result.evidence.payload["constraint_set"]["state"] == "VIOLATED"
    assert result.evidence.payload["constraint_set"]["reason_code"] == "CATALYTIC_CONSTRAINT_VIOLATED"
    diagnostics = result.evidence.payload["constraint_set"]["diagnostics"]
    assert diagnostics["violation_markers"] == ("policy:m1", "semantic_mode:m1")
