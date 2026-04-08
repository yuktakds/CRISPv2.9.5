from __future__ import annotations

import pytest

from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.report_guards import ReportGuardError, render_guarded_exploratory_report


def test_render_guarded_report_requires_inventory_authority_metadata() -> None:
    with pytest.raises(ReportGuardError, match="inventory_authority metadata is required"):
        render_guarded_exploratory_report(
            artifact_name="bridge_operator_summary.md",
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
            },
            sections=[
                {"semantic_source": "rc2", "label": "rc2 primary"},
                {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
            ],
            lines=["# invalid"],
        )


def test_render_guarded_report_rejects_mixed_summary_even_with_inventory_metadata() -> None:
    with pytest.raises(ReportGuardError, match="mixed semantic source is forbidden"):
        render_guarded_exploratory_report(
            artifact_name="bridge_operator_summary.md",
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
                "inventory_authority": build_inventory_authority_payload(
                    rc2_output_inventory_mutated=False,
                ),
            },
            sections=[
                {"semantic_source": "mixed", "label": "[exploratory] mixed summary"},
            ],
            lines=["# invalid"],
        )


def test_render_guarded_report_accepts_guarded_rc2_primary_and_v3_secondary() -> None:
    payload = render_guarded_exploratory_report(
        artifact_name="bridge_operator_summary.md",
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
        lines=["# [exploratory] ok"],
    )

    assert payload.endswith("\n")
