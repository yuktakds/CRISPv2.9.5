from __future__ import annotations

from crisp.v3.full_scope_validation import (
    audit_full_scope_validation_payload,
    build_full_scope_validation_payload,
)


def test_full_scope_validation_records_missing_required_components_without_activating_full_scope() -> None:
    payload = build_full_scope_validation_payload(
        comparator_scope="path_and_catalytic_partial",
        comparable_channels=("path", "catalytic"),
        v3_only_evidence_channels=("cap",),
        comparison_summary_payload={
            "comparison_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "component_matches": {"path": True, "catalytic_rule3a": None},
        },
        run_drift_report_payload={
            "comparator_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "verdict_match_rate": None,
            "verdict_mismatch_rate": None,
            "path_component_match_rate": 1.0,
        },
        internal_full_scv_bundle={
            "observations": [
                {"channel_name": "path"},
            ]
        },
    )

    assert payload["missing_required_components"] == ["scv_anchoring", "scv_offtarget"]
    assert payload["required_component_coverage_complete"] is False
    assert payload["full_verdict_denominator_ready"] is False
    assert payload["scope_allows_full_verdict_aggregation"] is False
    assert payload["verdict_rate_inactive"] is True


def test_full_scope_validation_can_prepare_denominator_before_full_scope_is_authorized() -> None:
    payload = build_full_scope_validation_payload(
        comparator_scope="path_and_catalytic_partial",
        comparable_channels=("path", "catalytic"),
        v3_only_evidence_channels=(),
        comparison_summary_payload={
            "comparison_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "component_matches": {"path": True, "catalytic_rule3a": None},
        },
        run_drift_report_payload={
            "comparator_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "verdict_match_rate": None,
            "verdict_mismatch_rate": None,
            "path_component_match_rate": 1.0,
        },
        internal_full_scv_bundle={
            "observations": [
                {"channel_name": "path"},
                {"channel_name": "scv_anchoring"},
                {"channel_name": "scv_offtarget"},
            ]
        },
    )

    assert payload["present_required_components"] == [
        "scv_pat",
        "scv_anchoring",
        "scv_offtarget",
    ]
    assert payload["missing_required_components"] == []
    assert payload["full_verdict_denominator_ready"] is True
    assert payload["scope_allows_full_verdict_aggregation"] is False
    assert payload["path_component_rate_retained"] is True


def test_full_scope_validation_audit_rejects_denominator_tamper() -> None:
    payload = build_full_scope_validation_payload(
        comparator_scope="path_and_catalytic_partial",
        comparable_channels=("path", "catalytic"),
        v3_only_evidence_channels=(),
        comparison_summary_payload={
            "comparison_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "component_matches": {"path": True, "catalytic_rule3a": None},
        },
        run_drift_report_payload={
            "comparator_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "verdict_match_rate": None,
            "verdict_mismatch_rate": None,
            "path_component_match_rate": 1.0,
        },
        internal_full_scv_bundle={
            "observations": [
                {"channel_name": "path"},
                {"channel_name": "scv_anchoring"},
                {"channel_name": "scv_offtarget"},
            ]
        },
    )

    tampered = dict(payload)
    tampered["full_verdict_denominator_ready"] = False
    findings = audit_full_scope_validation_payload(
        payload=tampered,
        comparator_scope="path_and_catalytic_partial",
        comparable_channels=("path", "catalytic"),
        v3_only_evidence_channels=(),
        comparison_summary_payload={
            "comparison_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "component_matches": {"path": True, "catalytic_rule3a": None},
        },
        run_drift_report_payload={
            "comparator_scope": "path_and_catalytic_partial",
            "comparable_channels": ["path", "catalytic"],
            "verdict_match_rate": None,
            "verdict_mismatch_rate": None,
            "path_component_match_rate": 1.0,
        },
        internal_full_scv_bundle={
            "observations": [
                {"channel_name": "path"},
                {"channel_name": "scv_anchoring"},
                {"channel_name": "scv_offtarget"},
            ]
        },
    )

    assert "P3 full_verdict_denominator_ready mismatch" in findings
