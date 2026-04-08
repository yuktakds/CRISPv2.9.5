from __future__ import annotations

from collections import Counter
from dataclasses import asdict

from crisp.v3.contracts import (
    ChannelEvidence,
    EvidenceState,
    RunApplicabilityRecord,
    SCVObservation,
    SCVObservationBundle,
    SCVVerdict,
)
from crisp.v3.policy import OBSERVATION_BUNDLE_SCHEMA_VERSION, SCV_BRIDGE_POLICY, SEMANTIC_POLICY_VERSION


class SCVBridge:
    """EvidenceState を SCV verdict に写すだけの routing shell。"""

    _STATE_TO_VERDICT = {
        EvidenceState.SUPPORTED: SCVVerdict.PASS,
        EvidenceState.REFUTED: SCVVerdict.FAIL,
        EvidenceState.INSUFFICIENT: SCVVerdict.UNCLEAR,
    }

    def route(self, evidence: ChannelEvidence) -> SCVObservation:
        verdict = self._STATE_TO_VERDICT[evidence.state]
        bridge_metrics = {
            "routing_policy": SCV_BRIDGE_POLICY,
            **dict(evidence.bridge_metrics),
        }
        return SCVObservation(
            channel_name=evidence.channel_name,
            family=evidence.family,
            verdict=verdict,
            evidence_state=evidence.state,
            payload=dict(evidence.payload),
            source=evidence.source,
            bridge_metrics=bridge_metrics,
        )

    def bundle(
        self,
        *,
        run_id: str,
        evidences: list[ChannelEvidence],
        applicability_records: list[RunApplicabilityRecord],
    ) -> SCVObservationBundle:
        observations = [self.route(evidence) for evidence in evidences]
        verdict_counts = Counter(observation.verdict for observation in observations)
        return SCVObservationBundle(
            schema_version=OBSERVATION_BUNDLE_SCHEMA_VERSION,
            run_id=run_id,
            semantic_policy_version=SEMANTIC_POLICY_VERSION,
            observations=observations,
            applicability_records=list(applicability_records),
            bridge_diagnostics={
                "routing_policy": SCV_BRIDGE_POLICY,
                "observation_count": len(observations),
                "applicability_record_count": len(applicability_records),
                "verdict_counts": {key.value: value for key, value in sorted(verdict_counts.items())},
            },
        )


def bundle_to_jsonl_rows(evidences: list[ChannelEvidence]) -> list[dict[str, object]]:
    return [asdict(evidence) for evidence in evidences]

