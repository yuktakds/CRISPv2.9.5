from __future__ import annotations

from crisp.v3.channels.cap import build_cap_partition_candidates


def _pair_features_rows() -> list[dict[str, object]]:
    return [
        {
            "canonical_link_id": "link-b",
            "molecule_id": "mol-2",
            "cap_id": "cap-2",
            "pairing_role": "matched_falsification",
            "comb": 0.21,
            "PAS": 0.12,
        },
        {
            "canonical_link_id": "link-a",
            "molecule_id": "mol-1",
            "cap_id": "cap-1",
            "pairing_role": "native",
            "comb": 0.82,
            "PAS": 0.71,
        },
        {
            "canonical_link_id": "link-a",
            "molecule_id": "mol-3",
            "cap_id": "cap-3",
            "pairing_role": "matched_falsification",
            "comb": 0.31,
            "PAS": 0.18,
        },
        {
            "canonical_link_id": "link-a",
            "molecule_id": "mol-2",
            "cap_id": "cap-2",
            "pairing_role": "native",
            "comb": 0.79,
            "PAS": 0.69,
        },
        {
            "canonical_link_id": "link-z",
            "molecule_id": "ignored",
            "cap_id": "ignored",
            "pairing_role": "unknown",
            "comb": 0.5,
            "PAS": 0.5,
        },
    ]


def test_cap_partition_candidates_are_generated_deterministically() -> None:
    first = build_cap_partition_candidates(_pair_features_rows())
    second = build_cap_partition_candidates(list(reversed(_pair_features_rows())))

    assert tuple(candidate.candidate_id for candidate in first) == (
        "link-a::native::mol-1::cap-1",
        "link-a::native::mol-2::cap-2",
        "link-a::matched_falsification::mol-3::cap-3",
        "link-b::matched_falsification::mol-2::cap-2",
    )
    assert tuple(candidate.candidate_id for candidate in first) == tuple(candidate.candidate_id for candidate in second)
    assert all(candidate.pairing_role in {"native", "matched_falsification"} for candidate in first)
