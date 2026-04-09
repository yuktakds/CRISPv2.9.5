from __future__ import annotations

from crisp.v3.contracts.catalytic import CatalyticConstraintObservation


def project_catalytic_payload(observation: CatalyticConstraintObservation) -> dict[str, object]:
    return {
        "quantitative_metrics": {
            "record_count": observation.record_count,
            "rows_with_proposal_trace": observation.rows_with_proposal_trace,
            "rows_with_candidate_order_hash": observation.rows_with_candidate_order_hash,
            "rows_with_stage_history": observation.rows_with_stage_history,
            "rows_with_trace_only_policy": observation.rows_with_trace_only_policy,
            "rows_with_trace_only_semantic_mode": observation.rows_with_trace_only_semantic_mode,
            "near_band_triggered_count": observation.near_band_triggered_count,
            "max_anchor_candidate_count": observation.max_anchor_candidate_count,
            "best_target_distance": observation.diagnostics.get("projected_best_target_distance"),
        },
        "witness_summary": {
            "sample_molecule_ids": observation.sample_molecule_ids,
            "observed_policy_versions": observation.observed_policy_versions,
            "observed_semantic_modes": observation.observed_semantic_modes,
            "struct_conn_status_counts": dict(observation.struct_conn_status_counts),
        },
        "constraint_set": {
            "state": observation.state.value,
            "reason_code": observation.reason_code,
            "diagnostics": dict(observation.diagnostics),
        },
    }
