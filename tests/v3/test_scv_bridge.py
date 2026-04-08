from __future__ import annotations

from crisp.v3.contracts import ChannelEvidence, EvidenceState, RunApplicabilityRecord, SCVVerdict
from crisp.v3.scv_bridge import SCVBridge


def test_scv_bridge_maps_evidence_states_without_reinterpreting_payload() -> None:
    bridge = SCVBridge()
    evidence = ChannelEvidence(
        channel_name="path",
        family="TUNNEL",
        state=EvidenceState.SUPPORTED,
        payload={"blockage_ratio": 0.81, "persistence_confidence": 0.12},
        source="pat.json",
        bridge_metrics={"persistence_confidence": 0.12},
    )

    observation = bridge.route(evidence)

    assert observation.verdict is SCVVerdict.PASS
    assert observation.evidence_state is EvidenceState.SUPPORTED
    assert observation.payload == {"blockage_ratio": 0.81, "persistence_confidence": 0.12}
    assert observation.bridge_metrics["persistence_confidence"] == 0.12


def test_scv_bridge_bundles_applicability_records_and_unclear_paths() -> None:
    bridge = SCVBridge()
    evidence = ChannelEvidence(
        channel_name="path",
        family="TUNNEL",
        state=EvidenceState.INSUFFICIENT,
        payload={"numeric_resolution_limited": True},
    )
    applicability = RunApplicabilityRecord(
        channel_name="path",
        family="TUNNEL",
        scope="run",
        applicable=False,
        reason_code="PAT_GOAL_INVALID",
    )

    bundle = bridge.bundle(
        run_id="run-1",
        evidences=[evidence],
        applicability_records=[applicability],
    )

    assert len(bundle.observations) == 1
    assert bundle.observations[0].verdict is SCVVerdict.UNCLEAR
    assert bundle.bridge_diagnostics["observation_count"] == 1
    assert bundle.bridge_diagnostics["applicability_record_count"] == 1
    assert bundle.bridge_diagnostics["verdict_counts"] == {"UNCLEAR": 1}

