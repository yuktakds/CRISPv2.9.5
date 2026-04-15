from __future__ import annotations

import pytest

from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.report_guards import ReportGuardError, enforce_exploratory_report_guard
from crisp.v3.rp3_activation import ActivationUnit
from crisp.v3.public_scope_validator import validate_keep_path_rc_bundle
from tests.v3.test_public_scope_validator import (
    _bridge_summary,
    _output_inventory,
    _sidecar_run_record,
    _verdict_record,
)


def _base_metadata() -> dict[str, object]:
    return {
        "semantic_policy_version": "v3.test",
        "verdict_comparability": "fully_comparable",
        "verdict_match_rate": "N/A",
        "verdict_mismatch_rate": "N/A",
        "full_verdict_computable": False,
        "inventory_authority": build_inventory_authority_payload(
            rc2_output_inventory_mutated=False,
        ),
        "comparable_channels": ("path", "catalytic"),
        "v3_only_evidence_channels": (),
        "channel_lifecycle_states": {
            "path": "observation_materialized",
            "catalytic": "observation_materialized",
        },
        "component_matches": {"path": True, "catalytic_rule3a": None},
    }


def _base_sections() -> list[dict[str, str]]:
    return [
        {"semantic_source": "rc2", "label": "rc2 primary"},
        {"semantic_source": "v3", "label": "[exploratory] v3 secondary"},
    ]


def _all_vn_gate_state() -> dict[str, bool]:
    return {
        "vn_01": True,
        "vn_02": True,
        "vn_03": True,
        "vn_04": True,
        "vn_05": True,
        "vn_06": True,
    }


def test_report_guard_does_not_render_shadow_verdict_from_decision_acceptance_alone() -> None:
    metadata = _base_metadata()
    metadata["activation_decisions"] = {
        ActivationUnit.V3_SHADOW_VERDICT.value: True,
    }
    metadata["v3_shadow_verdict"] = "PASS"

    with pytest.raises(ReportGuardError, match="v3_shadow_verdict must remain inactive"):
        enforce_exploratory_report_guard(
            metadata=metadata,
            sections=_base_sections(),
        )


def test_report_guard_suppresses_shadow_verdict_when_vn_gate_is_unmet() -> None:
    metadata = _base_metadata()
    metadata["activation_decisions"] = {
        ActivationUnit.V3_SHADOW_VERDICT.value: True,
    }
    metadata["vn_gate_state"] = {
        **_all_vn_gate_state(),
        "vn_04": False,
    }
    metadata["full_verdict_computable"] = True
    metadata["v3_shadow_verdict"] = "PASS"

    with pytest.raises(ReportGuardError, match="v3_shadow_verdict must remain inactive"):
        enforce_exploratory_report_guard(
            metadata=metadata,
            sections=_base_sections(),
        )


def test_report_guard_blocks_numeric_rates_when_shadow_is_inactive() -> None:
    metadata = _base_metadata()
    metadata["activation_decisions"] = {
        ActivationUnit.NUMERIC_VERDICT_RATES.value: True,
    }
    metadata["vn_gate_state"] = _all_vn_gate_state()
    metadata["full_verdict_computable"] = True
    metadata["denominator_contract_satisfied"] = True
    metadata["verdict_match_rate"] = "1/1 (100.0%)"

    with pytest.raises(
        ReportGuardError,
        match="numeric verdict rates present while runtime activation conditions are unmet",
    ):
        enforce_exploratory_report_guard(
            metadata=metadata,
            sections=_base_sections(),
        )


@pytest.mark.parametrize(
    ("metadata_patch", "sections", "match"),
    [
        (
            {
                "comparable_channels": ("path", "catalytic", "cap"),
                "channel_lifecycle_states": {
                    "path": "observation_materialized",
                    "catalytic": "observation_materialized",
                    "cap": "observation_materialized",
                },
            },
            _base_sections(),
            "cap must not appear in comparable_channels",
        ),
        (
            {
                "component_matches": {
                    "path": True,
                    "catalytic_rule3a": None,
                    "catalytic_rule3b": True,
                },
            },
            _base_sections(),
            "catalytic_rule3b must not appear in component_matches",
        ),
        (
            {},
            [{"semantic_source": "mixed", "label": "[exploratory] mixed summary"}],
            "mixed semantic source is forbidden",
        ),
    ],
)
def test_report_guard_blocks_forbidden_surfaces(
    metadata_patch: dict[str, object],
    sections: list[dict[str, str]],
    match: str,
) -> None:
    metadata = _base_metadata()
    metadata.update(metadata_patch)

    with pytest.raises(ReportGuardError, match=match):
        enforce_exploratory_report_guard(
            metadata=metadata,
            sections=sections,
        )


def test_public_scope_validator_blocks_shadow_verdict_with_decision_acceptance_alone() -> None:
    sidecar_run_record = _sidecar_run_record()
    sidecar_run_record["bridge_diagnostics"]["activation_decisions"] = {
        ActivationUnit.V3_SHADOW_VERDICT.value: True,
    }
    verdict_record = _verdict_record()
    verdict_record["v3_shadow_verdict"] = "PASS"

    errors, _, diagnostics = validate_keep_path_rc_bundle(
        sidecar_run_record=sidecar_run_record,
        verdict_record=verdict_record,
        output_inventory=_output_inventory(),
        bridge_summary=_bridge_summary(),
    )

    assert "KEEP_PATH_RC_V3_SHADOW_VERDICT_ACTIVE:verdict_record" in errors
    assert diagnostics["validation_passed"] is False


def test_public_scope_validator_blocks_rule3b_and_mixed_summary_surfaces() -> None:
    errors, _, diagnostics = validate_keep_path_rc_bundle(
        sidecar_run_record=_sidecar_run_record(),
        verdict_record=_verdict_record(),
        output_inventory=_output_inventory(),
        bridge_summary={
            "component_matches": {
                "path": True,
                "catalytic_rule3b": True,
            }
        },
        operator_summary=(
            "# [exploratory] Bridge Operator Summary\n"
            "- semantic_policy_version: `crisp.v3.semantic_policy/rev3-sidecar-first`\n"
            "- mixed summary: `requested`\n"
        ),
    )

    assert "KEEP_PATH_RC_COMPONENT_MATCH_LEAK:catalytic_rule3b" in errors
    assert "KEEP_PATH_RC_OPERATOR_MIXED_SUMMARY_FORBIDDEN" in errors
    assert diagnostics["validation_passed"] is False
