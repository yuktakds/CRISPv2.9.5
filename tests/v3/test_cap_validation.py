from __future__ import annotations

from crisp.v3.channels.cap import build_cap_partition_candidates, validate_cap_partition
from crisp.v3.contracts.cap import CapValidationState


def _validated_rows() -> list[dict[str, object]]:
    return [
        {"canonical_link_id": "a", "molecule_id": "n1", "cap_id": "c1", "pairing_role": "native", "comb": 0.82, "PAS": 0.75},
        {"canonical_link_id": "a", "molecule_id": "n2", "cap_id": "c2", "pairing_role": "native", "comb": 0.80, "PAS": 0.72},
        {"canonical_link_id": "a", "molecule_id": "n3", "cap_id": "c3", "pairing_role": "native", "comb": 0.78, "PAS": 0.70},
        {"canonical_link_id": "a", "molecule_id": "f1", "cap_id": "c4", "pairing_role": "matched_falsification", "comb": 0.22, "PAS": 0.18},
        {"canonical_link_id": "a", "molecule_id": "f2", "cap_id": "c5", "pairing_role": "matched_falsification", "comb": 0.20, "PAS": 0.15},
    ]


def test_cap_validation_marks_validated_when_margin_is_clear() -> None:
    decision = validate_cap_partition(build_cap_partition_candidates(_validated_rows()))

    assert decision.state is CapValidationState.VALIDATED
    assert decision.reason_code == "CAP_VALIDATION_CONFIRMED"
    assert decision.validation_margin is not None
    assert decision.validation_margin > 0.05


def test_cap_validation_marks_provisional_near_threshold_flip() -> None:
    rows = [
        {"canonical_link_id": "a", "molecule_id": "n1", "cap_id": "c1", "pairing_role": "native", "comb": 0.56, "PAS": 0.55},
        {"canonical_link_id": "a", "molecule_id": "n2", "cap_id": "c2", "pairing_role": "native", "comb": 0.55, "PAS": 0.55},
        {"canonical_link_id": "a", "molecule_id": "n3", "cap_id": "c3", "pairing_role": "native", "comb": 0.54, "PAS": 0.55},
        {"canonical_link_id": "a", "molecule_id": "f1", "cap_id": "c4", "pairing_role": "matched_falsification", "comb": 0.50, "PAS": 0.50},
        {"canonical_link_id": "a", "molecule_id": "f2", "cap_id": "c5", "pairing_role": "matched_falsification", "comb": 0.50, "PAS": 0.50},
    ]

    decision = validate_cap_partition(build_cap_partition_candidates(rows))

    assert decision.state is CapValidationState.PROVISIONAL
    assert decision.reason_code == "CAP_THRESHOLD_NEAR_FLIP"
    assert round(float(decision.validation_margin or 0.0), 6) == 0.05


def test_cap_validation_marks_rejected_when_falsification_outperforms_native() -> None:
    rows = [
        {"canonical_link_id": "a", "molecule_id": "n1", "cap_id": "c1", "pairing_role": "native", "comb": 0.25, "PAS": 0.20},
        {"canonical_link_id": "a", "molecule_id": "n2", "cap_id": "c2", "pairing_role": "native", "comb": 0.22, "PAS": 0.18},
        {"canonical_link_id": "a", "molecule_id": "n3", "cap_id": "c3", "pairing_role": "native", "comb": 0.21, "PAS": 0.17},
        {"canonical_link_id": "a", "molecule_id": "f1", "cap_id": "c4", "pairing_role": "matched_falsification", "comb": 0.48, "PAS": 0.40},
        {"canonical_link_id": "a", "molecule_id": "f2", "cap_id": "c5", "pairing_role": "matched_falsification", "comb": 0.46, "PAS": 0.39},
    ]

    decision = validate_cap_partition(build_cap_partition_candidates(rows))

    assert decision.state is CapValidationState.REJECTED
    assert decision.reason_code == "CAP_VALIDATION_REJECTED"
    assert decision.validation_margin is not None
    assert decision.validation_margin < 0.0
