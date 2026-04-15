from __future__ import annotations

from crisp.v3.promotion_gates import (
    PROMOTION_GATE_AUTHORITY_DOCUMENT,
    PROMOTION_GATE_AUTHORITY_MODE,
    PROMOTION_GATE_AUTHORITY_SECTION,
    emit_required_ci_candidacy_report,
    evaluate_np_exclusions,
    evaluate_pr_gates,
    evaluate_vn_gates,
)
from crisp.v3.report_guards import ReportGuardError, enforce_candidacy_report_guard


def test_pr_gates_require_strict_consecutive_windows() -> None:
    pr_gates = evaluate_pr_gates(
        comparator_scope="path_only_partial",
        channel_name="path",
        channel_contract_complete=True,
        sidecar_invariant_window=[True] * 29 + [False] + [True] * 10,
        baseline_value=1.0,
        metrics_drift_window=[0] * 30,
        windows_ci_window=[True] * 30,
        rc2_frozen_regression_green=True,
    )

    assert pr_gates["PR-02"]["passed"] is False
    assert pr_gates["PR-03"]["passed"] is True
    for gate_id in ("PR-01", "PR-02", "PR-03", "PR-04", "PR-05", "PR-06"):
        assert pr_gates[gate_id]["authority_reference"] == {
            "document": PROMOTION_GATE_AUTHORITY_DOCUMENT,
            "section": PROMOTION_GATE_AUTHORITY_SECTION,
            "gate_id": gate_id,
            "evaluation_mode": PROMOTION_GATE_AUTHORITY_MODE,
        }


def test_pr03_detail_remains_scope_aware_while_referencing_adr() -> None:
    path_scope = evaluate_pr_gates(
        comparator_scope="path_only_partial",
        channel_name="path",
        channel_contract_complete=True,
        sidecar_invariant_window=[True] * 30,
        baseline_value=1.0,
        metrics_drift_window=[0] * 30,
        windows_ci_window=[True] * 30,
        rc2_frozen_regression_green=True,
    )
    full_scope = evaluate_pr_gates(
        comparator_scope="full_channel_bundle",
        channel_name="path",
        channel_contract_complete=True,
        sidecar_invariant_window=[True] * 30,
        baseline_value=1.0,
        metrics_drift_window=[0] * 30,
        windows_ci_window=[True] * 30,
        rc2_frozen_regression_green=True,
    )

    assert path_scope["PR-03"]["detail"] == "path_component_match_rate baseline met"
    assert full_scope["PR-03"]["detail"] == "verdict_match_rate baseline met"
    assert path_scope["PR-03"]["authority_reference"]["gate_id"] == "PR-03"
    assert full_scope["PR-03"]["authority_reference"]["gate_id"] == "PR-03"


def test_np_exclusions_keep_cap_out_of_required_ci_candidacy() -> None:
    exclusions = evaluate_np_exclusions(
        channel_name="cap",
        has_rc2_component_mapping=False,
        channel_contract_complete=True,
        baseline_met=True,
        windows_stable=True,
        sidecar_only=False,
    )

    assert exclusions["NO_RC2_COMPONENT_MAPPING"] is True
    assert exclusions["CAP_ALWAYS_EXCLUDED"] is True
    assert exclusions["NOT_FULLY_COMPARABLE"] is False


def test_vn_gates_are_independent_from_pr_gates() -> None:
    vn_gates = evaluate_vn_gates(
        full_scv_mapping_frozen=False,
        all_mapped_components_generated=False,
        all_projectors_integrated=False,
        formal_contracts_complete=False,
        sidecar_invariant_30_green=True,
        verdict_record_migration_complete=False,
    )

    assert vn_gates["VN-01"]["passed"] is False
    assert vn_gates["VN-05"]["passed"] is True


def test_candidacy_report_is_exploratory_only_and_human_gated() -> None:
    payload = emit_required_ci_candidacy_report(
        comparator_scope="path_only_partial",
        channel_name="path",
        pr_gates=evaluate_pr_gates(
            comparator_scope="path_only_partial",
            channel_name="path",
            channel_contract_complete=True,
            sidecar_invariant_window=[True] * 30,
            baseline_value=1.0,
            metrics_drift_window=[0] * 30,
            windows_ci_window=[True] * 30,
            rc2_frozen_regression_green=True,
        ),
        vn_gates=evaluate_vn_gates(
            full_scv_mapping_frozen=False,
            all_mapped_components_generated=False,
            all_projectors_integrated=False,
            formal_contracts_complete=False,
            sidecar_invariant_30_green=True,
            verdict_record_migration_complete=False,
        ),
        np_exclusions=evaluate_np_exclusions(
            channel_name="path",
            has_rc2_component_mapping=True,
            channel_contract_complete=True,
            baseline_met=True,
            windows_stable=True,
        ),
    )

    assert payload["required_matrix_mutation_allowed"] is False
    assert payload["human_explicit_decision_required"] is True
    assert payload["operator_surface"]["label"] == "[exploratory] required-CI candidacy"
    assert payload["pr_gates"]["PR-06"]["authority_reference"]["document"] == PROMOTION_GATE_AUTHORITY_DOCUMENT
    assert payload["pr_gates"]["PR-06"]["authority_reference"]["section"] == PROMOTION_GATE_AUTHORITY_SECTION
    enforce_candidacy_report_guard(payload=payload, sections=[{"semantic_source": "v3", "label": "[exploratory] required-CI candidacy"}])


def test_candidacy_report_guard_blocks_primary_surface_and_matrix_mutation() -> None:
    payload = {
        "required_matrix_mutation_allowed": True,
        "human_explicit_decision_required": True,
        "operator_surface": {"label": "[exploratory] required-CI candidacy"},
    }
    try:
        enforce_candidacy_report_guard(payload=payload)
    except ReportGuardError as exc:
        assert "required matrix mutation" in str(exc)
    else:
        raise AssertionError("expected candidacy report guard to reject mutation")
