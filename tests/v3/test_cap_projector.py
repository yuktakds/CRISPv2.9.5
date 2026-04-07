from __future__ import annotations

from crisp.v3.channels.cap import build_cap_partition_candidates, validate_cap_partition
from crisp.v3.projectors.cap import project_cap_payload


def test_cap_projector_preserves_quantitative_metrics_and_witness_summary() -> None:
    rows = [
        {"canonical_link_id": "a", "molecule_id": "n1", "cap_id": "c1", "pairing_role": "native", "comb": 0.82, "PAS": 0.75},
        {"canonical_link_id": "a", "molecule_id": "n2", "cap_id": "c2", "pairing_role": "native", "comb": 0.80, "PAS": 0.72},
        {"canonical_link_id": "a", "molecule_id": "n3", "cap_id": "c3", "pairing_role": "native", "comb": 0.78, "PAS": 0.70},
        {"canonical_link_id": "a", "molecule_id": "f1", "cap_id": "c4", "pairing_role": "matched_falsification", "comb": 0.22, "PAS": 0.18},
        {"canonical_link_id": "a", "molecule_id": "f2", "cap_id": "c5", "pairing_role": "matched_falsification", "comb": 0.20, "PAS": 0.15},
    ]
    decision = validate_cap_partition(build_cap_partition_candidates(rows))

    payload = project_cap_payload(decision)
    metrics = payload["quantitative_metrics"]

    assert metrics["native_candidate_count"] == 3
    assert metrics["falsification_candidate_count"] == 2
    assert round(float(metrics["native_mean_comb"]), 6) == 0.8
    assert round(float(metrics["falsification_mean_comb"]), 6) == 0.21
    assert round(float(metrics["native_mean_pas"]), 6) == 0.723333
    assert round(float(metrics["falsification_mean_pas"]), 6) == 0.165
    assert round(float(metrics["validation_margin"]), 6) == 0.574167
    assert round(float(metrics["threshold_margin"]), 6) == 0.524167
    assert payload["witness_summary"]["native_witness_candidate_id"] == "a::native::n1::c1"
    assert payload["witness_summary"]["falsification_witness_candidate_id"] == "a::matched_falsification::f1::c4"
    assert payload["validation"]["state"] == "VALIDATED"
    assert payload["validation"]["reason_code"] == "CAP_VALIDATION_CONFIRMED"
