from __future__ import annotations


def compute_verdict_match_rate(
    comparable_count: int,
    match_count: int,
    has_shadow_verdict: bool,
) -> float | None:
    if comparable_count == 0 or not has_shadow_verdict:
        return None
    return match_count / comparable_count


def test_verdict_match_rate_is_na_when_shadow_verdict_absent() -> None:
    rate = compute_verdict_match_rate(
        comparable_count=12,
        match_count=0,
        has_shadow_verdict=False,
    )
    assert rate is None
