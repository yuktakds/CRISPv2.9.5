from __future__ import annotations

import pytest

from crisp.v3.ci_guards import build_ci_separation_payload
from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.report_guards import (
    OPERATOR_SURFACE_SPECS,
    ReportGuardError,
    attach_guarded_exploratory_payload,
    enforce_channel_semantics,
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
                {"semantic_source": "v3", "label": "v3 summary"},
            ],
        )


def test_channel_semantics_reject_v3_only_overlap_and_non_frozen_channel() -> None:
    with pytest.raises(ReportGuardError, match="outside the current public comparable set"):
        enforce_channel_semantics(
            comparable_channels=("path", "cap"),
            v3_only_evidence_channels=(),
        )

    with pytest.raises(ReportGuardError, match="must not appear in comparable_channels"):
        enforce_channel_semantics(
            comparable_channels=("path",),
            v3_only_evidence_channels=("path",),
        )

    with pytest.raises(ReportGuardError, match="must not appear in component_matches"):
        enforce_channel_semantics(
            comparable_channels=("path",),
            v3_only_evidence_channels=("cap",),
            component_matches={"path": True, "cap": True},
            channel_lifecycle_states={"path": "observation_materialized", "cap": "observation_materialized"},
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


def test_guard_requires_rc2_primary_section_first() -> None:
    with pytest.raises(ReportGuardError, match="rc2 primary section must be first"):
        enforce_exploratory_report_guard(
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
            },
            sections=[
                {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
                {"semantic_source": "rc2", "label": "rc2 primary"},
            ],
        )


def test_guard_requires_v3_secondary_label() -> None:
    with pytest.raises(ReportGuardError, match="v3 section must carry secondary label"):
        enforce_exploratory_report_guard(
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
            },
            sections=[
                {"semantic_source": "rc2", "label": "rc2 primary"},
                {"semantic_source": "v3", "label": "[exploratory] v3 shadow"},
            ],
        )


def test_guard_requires_rc2_primary_label() -> None:
    with pytest.raises(ReportGuardError, match="rc2 section must carry primary label"):
        enforce_exploratory_report_guard(
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
            },
            sections=[
                {"semantic_source": "rc2", "label": "rc2 frozen reference"},
                {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
            ],
        )


def test_guarded_operator_artifacts_follow_comparator_state() -> None:
    assert guarded_operator_artifacts(bridge_comparator_enabled=False) == ()
    assert guarded_operator_artifacts(bridge_comparator_enabled=True) == ("bridge_operator_summary.md",)


def test_operator_surface_registry_is_explicit() -> None:
    assert tuple(OPERATOR_SURFACE_SPECS) == (
        "bridge_operator_summary.md",
        "eval_report.json",
        "qc_report.json",
        "collapse_figure_spec.json",
    )
    assert OPERATOR_SURFACE_SPECS["bridge_operator_summary.md"].title_label == "[exploratory] Bridge Operator Summary"
    assert OPERATOR_SURFACE_SPECS["eval_report.json"].render_format == "json"
    assert OPERATOR_SURFACE_SPECS["qc_report.json"].render_format == "json"
    assert OPERATOR_SURFACE_SPECS["collapse_figure_spec.json"].render_format == "json"


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


def test_ci_separation_payload_blocks_required_promotion_for_current_v3_scope() -> None:
    payload = build_ci_separation_payload(v3_lanes_required=False)

    assert payload["required_promotion_blocked"] is True
    assert payload["allowed_required_v3_job_names"] == ["required / v3-sidecar-determinism"]
    assert payload["required_workflow_path"] == ".github/workflows/v29-required-matrix.yml"
    assert ".github/workflows/v29-required-matrix.yml" in payload["workflow_paths"]
    assert payload["v3_job_body_markers"]


def test_render_guarded_report_requires_exploratory_title_and_visible_semantic_policy_version() -> None:
    with pytest.raises(ReportGuardError, match="missing exploratory title label"):
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
                {"semantic_source": "rc2", "label": "rc2 primary"},
                {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
            ],
            lines=["# wrong title", "- semantic_policy_version: `v3.test`"],
        )

    with pytest.raises(ReportGuardError, match="must render semantic_policy_version"):
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
                {"semantic_source": "rc2", "label": "rc2 primary"},
                {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
            ],
            lines=["# [exploratory] Bridge Operator Summary"],
        )


def test_render_guarded_report_requires_v3_only_label_when_v3_only_channels_exist() -> None:
    with pytest.raises(ReportGuardError, match="must render \\[v3-only\\] labels"):
        render_guarded_exploratory_report(
            artifact_name="bridge_operator_summary.md",
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "not_comparable",
                "verdict_match_rate": "N/A",
                "comparable_channels": ("path",),
                "v3_only_evidence_channels": ("cap",),
                "channel_lifecycle_states": {
                    "path": "observation_materialized",
                    "cap": "observation_materialized",
                },
                "component_matches": {"path": True},
                "inventory_authority": build_inventory_authority_payload(
                    rc2_output_inventory_mutated=False,
                ),
            },
            sections=[
                {"semantic_source": "rc2", "label": "rc2 primary"},
                {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
            ],
            lines=[
                "# [exploratory] Bridge Operator Summary",
                "- semantic_policy_version: `v3.test`",
            ],
        )


def test_attach_guarded_exploratory_payload_rejects_unknown_surface() -> None:
    with pytest.raises(ReportGuardError):
        attach_guarded_exploratory_payload(
            artifact_name="unknown_report.json",
            payload={"run_id": "r1"},
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
        )


def test_attach_guarded_exploratory_payload_adds_contract_only_when_sections_present() -> None:
    payload = attach_guarded_exploratory_payload(
        artifact_name="eval_report.json",
        payload={"run_id": "r1"},
        metadata={
            "semantic_policy_version": "v3.test",
            "verdict_comparability": "not_comparable",
            "verdict_match_rate": "N/A",
            "comparator_scope": "path_only_partial",
            "comparable_channels": ("path",),
            "inventory_authority": build_inventory_authority_payload(
                rc2_output_inventory_mutated=False,
            ),
        },
        sections=[
            {"semantic_source": "rc2", "label": "rc2 primary"},
            {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
        ],
    )

    assert payload["semantic_policy_version"] == "v3.test"
    assert payload["comparator_scope"] == "path_only_partial"
    assert payload["comparable_channels"] == ["path"]
    assert payload["operator_surface_contract"]["artifact_name"] == "eval_report.json"
    assert payload["exploratory_sections"][1]["label"] == "[exploratory] v3 secondary"
