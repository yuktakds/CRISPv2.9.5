from __future__ import annotations

from crisp.v3.channels.catalytic import evaluate_catalytic_constraints
from crisp.v3.projectors.catalytic import project_catalytic_payload


def test_catalytic_projector_preserves_constraint_metrics_and_witness_summary() -> None:
    observation = evaluate_catalytic_constraints(
        [
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
    )

    payload = project_catalytic_payload(observation)
    metrics = payload["quantitative_metrics"]

    assert metrics["record_count"] == 2
    assert metrics["rows_with_proposal_trace"] == 2
    assert metrics["rows_with_candidate_order_hash"] == 2
    assert metrics["rows_with_stage_history"] == 2
    assert metrics["rows_with_trace_only_policy"] == 2
    assert metrics["rows_with_trace_only_semantic_mode"] == 2
    assert metrics["near_band_triggered_count"] == 1
    assert metrics["max_anchor_candidate_count"] == 3
    assert payload["witness_summary"]["sample_molecule_ids"] == ("m1", "m2")
    assert payload["witness_summary"]["observed_policy_versions"] == ("v29.trace-only.noop",)
    assert payload["witness_summary"]["observed_semantic_modes"] == ("trace-only-noop",)
    assert payload["witness_summary"]["struct_conn_status_counts"] == {"missing": 1, "present": 1}
    assert payload["constraint_set"]["state"] == "SATISFIED"
