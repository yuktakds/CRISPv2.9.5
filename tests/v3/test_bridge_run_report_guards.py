from __future__ import annotations

import pytest

from crisp.v3.bridge.run_report import guard_current_scope_no_full_aggregation, resolve_denominators
from crisp.v3.current_public_scope import CURRENT_PUBLIC_COMPARATOR_SCOPE


# ---------------------------------------------------------------------------
# resolve_denominators
# ---------------------------------------------------------------------------


def test_resolve_denominators_maps_all_five_metrics() -> None:
    result = resolve_denominators(
        total_compounds=100,
        component_verdict_comparable_count=80,
        full_verdict_comparable_count=60,
    )

    assert set(result.keys()) == {
        "coverage_drift_rate",
        "applicability_drift_rate",
        "verdict_match_rate",
        "verdict_mismatch_rate",
        "path_component_match_rate",
    }


def test_resolve_denominators_coverage_uses_total_compounds() -> None:
    result = resolve_denominators(
        total_compounds=42,
        component_verdict_comparable_count=0,
        full_verdict_comparable_count=0,
    )

    assert result["coverage_drift_rate"] == 42
    assert result["applicability_drift_rate"] == 42


def test_resolve_denominators_verdict_rates_use_full_comparable_count() -> None:
    result = resolve_denominators(
        total_compounds=100,
        component_verdict_comparable_count=80,
        full_verdict_comparable_count=30,
    )

    assert result["verdict_match_rate"] == 30
    assert result["verdict_mismatch_rate"] == 30


def test_resolve_denominators_path_component_uses_component_count() -> None:
    result = resolve_denominators(
        total_compounds=100,
        component_verdict_comparable_count=75,
        full_verdict_comparable_count=0,
    )

    assert result["path_component_match_rate"] == 75


def test_resolve_denominators_all_zero_is_valid() -> None:
    result = resolve_denominators(
        total_compounds=0,
        component_verdict_comparable_count=0,
        full_verdict_comparable_count=0,
    )

    assert all(v == 0 for v in result.values())


# ---------------------------------------------------------------------------
# guard_current_scope_no_full_aggregation — current partial scope
# ---------------------------------------------------------------------------


def test_guard_allows_partial_scope_with_all_metrics_null_or_zero() -> None:
    # should not raise
    guard_current_scope_no_full_aggregation(
        comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
        full_verdict_computable=False,
        full_verdict_comparable_count=0,
        verdict_match_rate=None,
        verdict_mismatch_rate=None,
    )


def test_guard_raises_when_full_verdict_computable_in_partial_scope() -> None:
    with pytest.raises(ValueError, match="must not activate full-scope aggregation"):
        guard_current_scope_no_full_aggregation(
            comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
            full_verdict_computable=True,
            full_verdict_comparable_count=0,
            verdict_match_rate=None,
            verdict_mismatch_rate=None,
        )


def test_guard_raises_when_full_comparable_count_nonzero_in_partial_scope() -> None:
    with pytest.raises(ValueError, match="must not activate full-scope aggregation"):
        guard_current_scope_no_full_aggregation(
            comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
            full_verdict_computable=False,
            full_verdict_comparable_count=5,
            verdict_match_rate=None,
            verdict_mismatch_rate=None,
        )


def test_guard_raises_when_verdict_match_rate_set_in_partial_scope() -> None:
    with pytest.raises(ValueError, match="must not activate full-scope aggregation"):
        guard_current_scope_no_full_aggregation(
            comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
            full_verdict_computable=False,
            full_verdict_comparable_count=0,
            verdict_match_rate=0.95,
            verdict_mismatch_rate=None,
        )


def test_guard_raises_when_verdict_mismatch_rate_set_in_partial_scope() -> None:
    with pytest.raises(ValueError, match="must not activate full-scope aggregation"):
        guard_current_scope_no_full_aggregation(
            comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
            full_verdict_computable=False,
            full_verdict_comparable_count=0,
            verdict_match_rate=None,
            verdict_mismatch_rate=0.05,
        )


def test_guard_allows_full_bundle_scope_with_active_aggregation() -> None:
    # full_bundle scope permits full aggregation — must not raise
    guard_current_scope_no_full_aggregation(
        comparator_scope="full_channel_bundle",
        full_verdict_computable=True,
        full_verdict_comparable_count=50,
        verdict_match_rate=0.9,
        verdict_mismatch_rate=0.1,
    )
