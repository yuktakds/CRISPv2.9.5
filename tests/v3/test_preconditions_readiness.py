from __future__ import annotations

from crisp.v3.preconditions import (
    ChannelState,
    GATE_EVIDENCE_SCHEMA_VERSION,
    GateStatus,
    build_preconditions_readiness,
)


def test_preconditions_readiness_stays_path_only_and_not_full_ready() -> None:
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
    )

    assert readiness.comparator_scope == "path_only_partial"
    assert readiness.comparable_channels == ("path",)
    assert readiness.full_migration_ready is False
    assert readiness.channel_states["cap"] == ChannelState.OBSERVATION_MATERIALIZED.value
    assert readiness.channel_blockers["cap"] == ()
    assert readiness.gates["P1"]["status"] == GateStatus.PASS.value
    assert readiness.gates["P6"]["status"] == GateStatus.BLOCKED.value
    assert readiness.gate_evidence["P2"]["schema_version"] == GATE_EVIDENCE_SCHEMA_VERSION
    assert readiness.gate_evidence["P2"]["builder_provenance_ref"]["artifact_name"] == "builder_provenance.json"
    assert readiness.gate_evidence["P4"]["guarded_operator_report_refs"] == ()
    assert readiness.gate_evidence["P7"]["preconditions_ref"]["artifact_name"] == "preconditions_readiness.json"


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
    )

    assert readiness.gates["P2"]["status"] == GateStatus.BLOCKED.value
