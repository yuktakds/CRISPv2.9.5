from __future__ import annotations

import pytest

from crisp.v3.report_guards import ReportGuardError, enforce_exploratory_report_guard


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

