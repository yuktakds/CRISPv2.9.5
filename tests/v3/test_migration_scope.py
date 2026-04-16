from __future__ import annotations

import pytest

from crisp.v3.contracts import ComparisonScope
from crisp.v3.migration_scope import (
    all_required_components_frozen,
    get_comparator_scope,
    get_internal_full_scv_channel,
    get_mapping_source,
    get_mapping_status,
    is_partial_comparator_scope,
    required_scv_components,
    resolve_pr03_metric,
    scope_allows_full_verdict_aggregation,
)


# ---------------------------------------------------------------------------
# Component mapping status
# ---------------------------------------------------------------------------


def test_all_required_components_are_frozen() -> None:
    for component in required_scv_components():
        assert get_mapping_status(component) == "FROZEN", f"{component} must be FROZEN"


def test_all_required_components_frozen_returns_true() -> None:
    assert all_required_components_frozen() is True


def test_required_scv_components_are_exactly_three() -> None:
    components = required_scv_components()
    assert set(components) == {"scv_pat", "scv_anchoring", "scv_offtarget"}


def test_get_mapping_status_unknown_component_raises() -> None:
    with pytest.raises(KeyError):
        get_mapping_status("unknown_component")


def test_get_mapping_source_known_components() -> None:
    assert get_mapping_source("scv_pat") == "path_channel_projector"
    assert get_mapping_source("scv_anchoring") == "catalytic_rule3a_projector"
    assert get_mapping_source("scv_offtarget") == "thin_offtarget_channel_wrapper"


def test_get_internal_full_scv_channel_known_components() -> None:
    assert get_internal_full_scv_channel("scv_pat") == "path"
    assert get_internal_full_scv_channel("scv_anchoring") == "scv_anchoring"
    assert get_internal_full_scv_channel("scv_offtarget") == "scv_offtarget"


# ---------------------------------------------------------------------------
# Comparator scope normalization
# ---------------------------------------------------------------------------


def test_get_comparator_scope_accepts_enum() -> None:
    assert get_comparator_scope(ComparisonScope.PATH_AND_CATALYTIC_PARTIAL) == "path_and_catalytic_partial"
    assert get_comparator_scope(ComparisonScope.PATH_ONLY_PARTIAL) == "path_only_partial"
    assert get_comparator_scope(ComparisonScope.FULL_CHANNEL_BUNDLE) == "full_channel_bundle"


def test_get_comparator_scope_accepts_string() -> None:
    assert get_comparator_scope("path_and_catalytic_partial") == "path_and_catalytic_partial"
    assert get_comparator_scope("full_channel_bundle") == "full_channel_bundle"


# ---------------------------------------------------------------------------
# Partial scope classification
# ---------------------------------------------------------------------------


def test_partial_scopes_are_partial() -> None:
    assert is_partial_comparator_scope(ComparisonScope.PATH_AND_CATALYTIC_PARTIAL) is True
    assert is_partial_comparator_scope(ComparisonScope.PATH_ONLY_PARTIAL) is True
    assert is_partial_comparator_scope("path_and_catalytic_partial") is True
    assert is_partial_comparator_scope("path_only_partial") is True


def test_full_bundle_is_not_partial() -> None:
    assert is_partial_comparator_scope(ComparisonScope.FULL_CHANNEL_BUNDLE) is False
    assert is_partial_comparator_scope("full_channel_bundle") is False


# ---------------------------------------------------------------------------
# Full verdict aggregation guard
# ---------------------------------------------------------------------------


def test_full_bundle_allows_full_verdict_aggregation() -> None:
    assert scope_allows_full_verdict_aggregation(ComparisonScope.FULL_CHANNEL_BUNDLE) is True
    assert scope_allows_full_verdict_aggregation("full_channel_bundle") is True


def test_partial_scopes_do_not_allow_full_verdict_aggregation() -> None:
    assert scope_allows_full_verdict_aggregation(ComparisonScope.PATH_AND_CATALYTIC_PARTIAL) is False
    assert scope_allows_full_verdict_aggregation(ComparisonScope.PATH_ONLY_PARTIAL) is False
    assert scope_allows_full_verdict_aggregation("path_and_catalytic_partial") is False


# ---------------------------------------------------------------------------
# PR-03 metric selection — critical boundary guard
# The current comparator_scope is path_and_catalytic_partial.
# resolve_pr03_metric MUST return "path_component_match_rate" for any
# partial scope; it must NOT return "verdict_match_rate".
# ---------------------------------------------------------------------------


def test_pr03_metric_is_path_component_rate_for_current_scope() -> None:
    # This is the currently active comparator_scope. The metric must NOT be
    # verdict_match_rate while the scope remains partial.
    metric = resolve_pr03_metric(ComparisonScope.PATH_AND_CATALYTIC_PARTIAL)
    assert metric == "path_component_match_rate"
    assert metric != "verdict_match_rate"


def test_pr03_metric_is_path_component_rate_for_path_only_partial() -> None:
    metric = resolve_pr03_metric(ComparisonScope.PATH_ONLY_PARTIAL)
    assert metric == "path_component_match_rate"
    assert metric != "verdict_match_rate"


def test_pr03_metric_is_verdict_match_rate_only_for_full_bundle() -> None:
    metric = resolve_pr03_metric(ComparisonScope.FULL_CHANNEL_BUNDLE)
    assert metric == "verdict_match_rate"


def test_pr03_metric_accepts_string_scope() -> None:
    assert resolve_pr03_metric("path_and_catalytic_partial") == "path_component_match_rate"
    assert resolve_pr03_metric("full_channel_bundle") == "verdict_match_rate"
