from __future__ import annotations

from crisp.v3.bridge.comparator import (
    build_run_report,
    compute_full_verdict_comparable_subset,
    guard_current_scope_no_full_aggregation,
    required_scv_components_frozen,
    resolve_denominators,
)
from crisp.v3.contracts import ComparisonScope, CompoundDriftReport, DriftRecord
from crisp.v3.migration_scope import get_mapping_status, resolve_pr03_metric


def test_required_scv_components_frozen_uses_shared_truth_source() -> None:
    assert get_mapping_status("scv_pat") == "FROZEN"
    assert get_mapping_status("scv_anchoring") == "FROZEN"
    assert get_mapping_status("scv_offtarget") == "FROZEN"
    assert required_scv_components_frozen() is True


def test_full_verdict_subset_is_not_computable_in_path_only_scope() -> None:
    subset = compute_full_verdict_comparable_subset(
        comparator_scope="path_only_partial",
        compound_reports=(
            CompoundDriftReport(
                channel_name="path",
                component_comparability={"path": "component_verdict_comparable"},
                component_matches={"path": True},
            ),
        ),
        v3_only_evidence_channels=("cap",),
    )

    assert subset["computable"] is False
    assert subset["subset_indices"] == ()


def test_resolve_denominators_keeps_path_component_rate_separate() -> None:
    denominators = resolve_denominators(
        total_compounds=7,
        component_verdict_comparable_count=2,
        full_verdict_comparable_count=0,
    )

    assert denominators["coverage_drift_rate"] == 7
    assert denominators["applicability_drift_rate"] == 7
    assert denominators["verdict_match_rate"] == 0
    assert denominators["verdict_mismatch_rate"] == 0
    assert denominators["path_component_match_rate"] == 2


def test_scope_guard_blocks_full_aggregation_in_path_only_scope() -> None:
    try:
        guard_current_scope_no_full_aggregation(
            comparator_scope="path_only_partial",
            full_verdict_computable=True,
            full_verdict_comparable_count=1,
            verdict_match_rate=1.0,
            verdict_mismatch_rate=0.0,
        )
    except ValueError as exc:
        assert "path_only_partial scope must not activate full-scope aggregation" in str(exc)
    else:
        raise AssertionError("expected path_only_partial guard to block full aggregation")


def test_scope_guard_blocks_full_aggregation_in_path_and_catalytic_partial_scope() -> None:
    try:
        guard_current_scope_no_full_aggregation(
            comparator_scope="path_and_catalytic_partial",
            full_verdict_computable=True,
            full_verdict_comparable_count=1,
            verdict_match_rate=1.0,
            verdict_mismatch_rate=0.0,
        )
    except ValueError as exc:
        assert "path_and_catalytic_partial scope must not activate full-scope aggregation" in str(exc)
    else:
        raise AssertionError("expected path_and_catalytic_partial guard to block full aggregation")


def test_build_run_report_uses_requested_partial_scope() -> None:
    report = build_run_report(
        comparator_scope=ComparisonScope.PATH_AND_CATALYTIC_PARTIAL.value,
        comparable_channels=("path",),
        compound_reports=(
            CompoundDriftReport(
                channel_name="path",
                component_comparability={"path": "component_verdict_comparable"},
                component_matches={"path": True},
            ),
        ),
        drifts=(),
        v3_only_evidence_channels=(),
    )

    assert report.comparator_scope is ComparisonScope.PATH_AND_CATALYTIC_PARTIAL
    assert report.full_verdict_computable is False
    assert report.full_verdict_comparable_count == 0


def test_pr03_metric_resolution_is_scope_aware() -> None:
    assert resolve_pr03_metric("path_only_partial") == "path_component_match_rate"
    assert resolve_pr03_metric("path_and_catalytic_partial") == "path_component_match_rate"
    assert resolve_pr03_metric("full_channel_bundle") == "verdict_match_rate"
