from __future__ import annotations

from crisp.v3.full_scope_validation import build_full_scope_validation_payload
from crisp.v3.preconditions import (
    ChannelState,
    GATE_EVIDENCE_SCHEMA_VERSION,
    GateStatus,
    build_preconditions_readiness,
)


def _full_scope_validation_payload() -> dict[str, object]:
    return build_full_scope_validation_payload(
        comparator_scope="path_and_catalytic_partial",
        comparable_channels=("path", "catalytic"),
        v3_only_evidence_channels=("cap",),
        comparison_summary_payload={
            "comparison_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "component_matches": {"path": True, "catalytic_rule3a": None},
        },
        run_drift_report_payload={
            "comparator_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "verdict_match_rate": None,
            "verdict_mismatch_rate": None,
            "path_component_match_rate": 1.0,
        },
        internal_full_scv_bundle={
            "observations": [
                {"channel_name": "path"},
            ]
        },
    )


def test_preconditions_readiness_stays_current_public_partial_and_not_full_ready() -> None:
    readiness = build_preconditions_readiness(
        semantic_policy_version="v3.test",
        channel_states={
            "path": ChannelState.OBSERVATION_MATERIALIZED,
            "cap": ChannelState.OBSERVATION_MATERIALIZED,
            "catalytic": ChannelState.OBSERVATION_MATERIALIZED,
        },
        truth_source_records={
            "path": {
                "source_label": "path_snapshot",
                "source_digest": "sha256:1",
                "source_location_kind": "artifact",
                "builder_identity": "PathEvidenceChannel@v1",
                "projector_identity": "PathChannelProjector@v1",
                "observation_artifact_pointer": "observation_bundle.json",
            },
            "cap": {
                "source_label": "pair_features_snapshot",
                "source_digest": "sha256:2",
                "source_location_kind": "artifact",
                "builder_identity": "CapEvidenceChannel@v1",
                "projector_identity": "CapChannelProjector@v1",
                "observation_artifact_pointer": "observation_bundle.json",
            },
            "catalytic": {
                "source_label": "evidence_core_snapshot",
                "source_digest": "sha256:3",
                "source_location_kind": "artifact",
                "builder_identity": "CatalyticEvidenceChannel@v1",
                "projector_identity": "CatalyticChannelProjector@v1",
                "observation_artifact_pointer": "observation_bundle.json",
            },
        },
        full_scope_validation=_full_scope_validation_payload(),
    )

    assert readiness.comparator_scope == "path_and_catalytic_partial"
    assert readiness.comparable_channels == ("path", "catalytic")
    assert readiness.full_migration_ready is False
    assert readiness.channel_states["cap"] == ChannelState.OBSERVATION_MATERIALIZED.value
    assert readiness.channel_blockers["cap"] == ()
    assert readiness.gates["P1"]["status"] == GateStatus.PASS.value
    assert readiness.gates["P3"]["status"] == GateStatus.PASS.value
    assert readiness.gates["P6"]["status"] == GateStatus.BLOCKED.value
    assert readiness.gate_evidence["P2"]["schema_version"] == GATE_EVIDENCE_SCHEMA_VERSION
    assert readiness.gate_evidence["P2"]["builder_provenance_ref"]["artifact_name"] == "builder_provenance.json"
    assert readiness.gate_evidence["P3"]["validation_payload_version"] == "crisp.v3.full_scope_validation/v1"
    assert readiness.gate_evidence["P3"]["full_verdict_denominator_ready"] is False
    assert readiness.gate_evidence["P4"]["guarded_operator_report_refs"] == ()
    assert readiness.gate_evidence["P4"]["rc2_primary_label_required"] is True
    assert readiness.gate_evidence["P4"]["v3_secondary_label_required"] is True
    assert readiness.gate_evidence["P5"]["exploratory_job_name_prefix"] == "exploratory / "
    assert readiness.gate_evidence["P7"]["preconditions_ref"]["artifact_name"] == "preconditions_readiness.json"
    assert readiness.inventory_authority["sidecar_inventory_source"] == "v3_sidecar/generator_manifest.json"
    assert readiness.inventory_authority["rc2_inventory_source"] == "output_inventory.json"
    assert readiness.ci_status["required_promotion_blocked"] is True


def test_truth_source_chain_missing_field_blocks_p2() -> None:
    readiness = build_preconditions_readiness(
        semantic_policy_version="v3.test",
        channel_states={
            "path": ChannelState.OBSERVATION_MATERIALIZED,
            "cap": ChannelState.APPLICABILITY_ONLY,
            "catalytic": ChannelState.DISABLED,
        },
        truth_source_records={
            "path": {
                "source_label": "path_snapshot",
                "source_digest": "sha256:1",
                "source_location_kind": "artifact",
                "builder_identity": "PathEvidenceChannel@v1",
                "projector_identity": "PathChannelProjector@v1",
            },
            "cap": {},
            "catalytic": {},
        },
        full_scope_validation=_full_scope_validation_payload(),
    )

    assert readiness.gates["P2"]["status"] == GateStatus.BLOCKED.value
