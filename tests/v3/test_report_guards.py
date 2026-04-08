from __future__ import annotations

import pytest

from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.report_guards import (
    ReportGuardError,
    enforce_exploratory_report_guard,
    guarded_operator_artifacts,
    render_guarded_exploratory_report,
)


def test_guard_requires_semantic_policy_version() -> None:
    with pytest.raises(ReportGuardError):
        enforce_exploratory_report_guard(
            metadata={"verdict_comparability": "not_comparable"},
            sections=[],
        )


def test_guard_requires_exploratory_label_for_v3_sections() -> None:
    with pytest.raises(ReportGuardError):
        enforce_exploratory_report_guard(
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
            },
            sections=[
                {"semantic_source": "rc2", "label": "rc2 primary"},
                {"semantic_source": "v3", "label": "v3 secondary"},
            ],
        )


def test_guard_rejects_non_na_match_rate_when_not_comparable() -> None:
    with pytest.raises(ReportGuardError):
        enforce_exploratory_report_guard(
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "0%",
            },
            sections=[
                {"semantic_source": "rc2", "label": "rc2 primary"},
                {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
            ],
        )


def test_guard_rejects_mixed_semantic_sections() -> None:
    with pytest.raises(ReportGuardError):
        enforce_exploratory_report_guard(
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
            },
            sections=[
                {"semantic_source": "mixed", "label": "[exploratory] mixed summary"},
            ],
        )


def test_guarded_operator_artifacts_follow_comparator_state() -> None:
    assert guarded_operator_artifacts(bridge_comparator_enabled=False) == ()
    assert guarded_operator_artifacts(bridge_comparator_enabled=True) == ("bridge_operator_summary.md",)


def test_render_guarded_exploratory_report_rejects_unknown_operator_artifact() -> None:
    with pytest.raises(ReportGuardError):
        render_guarded_exploratory_report(
            artifact_name="other_operator_summary.md",
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
                "inventory_authority": build_inventory_authority_payload(
                    rc2_output_inventory_mutated=False,
                ),
            },
            sections=[
                {"semantic_source": "rc2", "label": "rc2 primary"},
                {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
            ],
            lines=["# invalid"],
        )
