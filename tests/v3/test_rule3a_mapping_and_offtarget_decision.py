from __future__ import annotations

from crisp.v3.channels.offtarget import OffTargetEvidenceChannel
from crisp.v3.migration_scope import all_required_components_frozen, get_mapping_source, get_mapping_status
from crisp.v3.projectors.catalytic import project_catalytic_payload
from crisp.v3.projectors.scv_components import (
    project_catalytic_rule3a_to_anchoring_input,
    project_thin_offtarget_to_offtarget_input,
)
from crisp.v3.contracts.catalytic import CatalyticConstraintObservation, CatalyticConstraintState


def test_mapping_registry_closes_rule3a_and_offtarget_source_decision() -> None:
    assert get_mapping_status("scv_anchoring") == "FROZEN"
    assert get_mapping_source("scv_anchoring") == "catalytic_rule3a_projector"
    assert get_mapping_status("scv_offtarget") == "FROZEN"
    assert get_mapping_source("scv_offtarget") == "thin_offtarget_channel_wrapper"
    assert all_required_components_frozen() is True


def test_catalytic_rule3a_projector_is_deterministic_for_best_target_distance() -> None:
    payload = project_catalytic_payload(
        CatalyticConstraintObservation(
            state=CatalyticConstraintState.SATISFIED,
            reason_code="CATALYTIC_TRACE_ONLY_CONSTRAINTS_OBSERVED",
            record_count=2,
            rows_with_proposal_trace=2,
            rows_with_candidate_order_hash=2,
            rows_with_stage_history=2,
            rows_with_trace_only_policy=2,
            rows_with_trace_only_semantic_mode=2,
            near_band_triggered_count=1,
            max_anchor_candidate_count=3,
            observed_policy_versions=("v29.trace-only.noop",),
            observed_semantic_modes=("trace-only-noop",),
            sample_molecule_ids=("m1", "m2"),
            diagnostics={"projected_best_target_distance": 1.7},
        )
    )

    first = project_catalytic_rule3a_to_anchoring_input(payload)
    second = project_catalytic_rule3a_to_anchoring_input(payload)

    assert first.best_target_distance == 1.7
    assert second.best_target_distance == 1.7


def test_thin_offtarget_channel_wrapper_projects_best_offtarget_distance() -> None:
    result = OffTargetEvidenceChannel().evaluate(
        core_compound_rows=[
            {"molecule_id": "m1", "best_offtarget_distance": 5.1},
            {"molecule_id": "m2", "best_offtarget_distance": 4.7},
        ],
        source="core_compounds.parquet",
    )

    assert result.evidence is not None
    payload = result.evidence.payload
    projected = project_thin_offtarget_to_offtarget_input(payload)
    assert projected.best_offtarget_distance == 4.7
    assert result.evidence.bridge_metrics["wrapper_kind"] == "thin_offtarget_channel_wrapper"
