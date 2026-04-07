from __future__ import annotations

from crisp.v3.contracts.cap import CapValidationDecision


def project_cap_payload(decision: CapValidationDecision) -> dict[str, object]:
    candidate_ids = tuple(candidate.candidate_id for candidate in decision.candidates)
    native_candidate_ids = tuple(
        candidate.candidate_id
        for candidate in decision.candidates
        if candidate.pairing_role == "native"
    )
    falsification_candidate_ids = tuple(
        candidate.candidate_id
        for candidate in decision.candidates
        if candidate.pairing_role == "matched_falsification"
    )
    return {
        "quantitative_metrics": {
            "native_candidate_count": decision.native_candidate_count,
            "falsification_candidate_count": decision.falsification_candidate_count,
            "native_mean_comb": decision.native_mean_comb,
            "falsification_mean_comb": decision.falsification_mean_comb,
            "native_mean_pas": decision.native_mean_pas,
            "falsification_mean_pas": decision.falsification_mean_pas,
            "validation_margin": decision.validation_margin,
            "threshold_margin": decision.threshold_margin,
        },
        "witness_summary": {
            "native_witness_candidate_id": decision.native_witness_candidate_id,
            "falsification_witness_candidate_id": decision.falsification_witness_candidate_id,
            "candidate_ids": candidate_ids,
            "native_candidate_ids": native_candidate_ids,
            "falsification_candidate_ids": falsification_candidate_ids,
        },
        "validation": {
            "state": decision.state.value,
            "reason_code": decision.reason_code,
            "diagnostics": dict(decision.diagnostics),
        },
    }
