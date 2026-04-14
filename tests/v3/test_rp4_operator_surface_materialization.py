from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from crisp.v3.adapters.rc2 import RC2Adapter
from crisp.v3.comparator import BridgeComparator
from crisp.v3.contracts import ComparisonScope, VerdictComparability
from crisp.v3.contracts import BridgeComparatorOptions
from crisp.v3.policy import SEMANTIC_POLICY_VERSION, parse_sidecar_options
from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.report_guards import ReportGuardError, render_guarded_exploratory_report
from crisp.v3.reports import build_bridge_comparison_summary_payload, build_bridge_operator_summary
from crisp.v3.rp3_activation import ActivationUnit
from crisp.v3.runner import run_sidecar
from tests.v3.helpers import build_v3_shadow_bundle, make_config, write_pat_fixture
from tests.v3.test_wp6_shadow_activation_readiness import _build_snapshot


def _bridge_result(
    tmp_path: Path,
    *,
    include_cap: bool = False,
    include_catalytic: bool = False,
):
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
    config = make_config()
    rc2_result = RC2Adapter().adapt_path_only(
        run_id="run-1",
        config=config,
        pat_diagnostics_path=pat_path,
    )
    v3_bundle = build_v3_shadow_bundle(
        run_id="run-1",
        config=config,
        pat_diagnostics_path=pat_path,
        include_cap=include_cap,
        include_catalytic=include_catalytic,
    )
    return BridgeComparator().compare(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        rc2_adapt_result=rc2_result,
        v3_bundle=v3_bundle,
    )


def _full_verdict_result(tmp_path: Path):
    result = _bridge_result(tmp_path, include_catalytic=True)
    return replace(
        result,
        summary=replace(
            result.summary,
            comparison_scope=ComparisonScope.FULL_CHANNEL_BUNDLE,
            verdict_comparability=VerdictComparability.COMPARABLE,
        ),
        run_report=replace(
            result.run_report,
            comparator_scope=ComparisonScope.FULL_CHANNEL_BUNDLE,
            full_verdict_computable=True,
            full_verdict_comparable_count=1,
            verdict_match_count=1,
            verdict_mismatch_count=0,
            verdict_match_rate=1.0,
            verdict_mismatch_rate=0.0,
        ),
    )


def _all_vn_gate_state() -> dict[str, bool]:
    return {
        "vn_01": True,
        "vn_02": True,
        "vn_03": True,
        "vn_04": True,
        "vn_05": True,
        "vn_06": True,
    }


def test_operator_summary_renders_shadow_verdict_when_activation_gate_is_met(tmp_path: Path) -> None:
    summary = build_bridge_operator_summary(
        _full_verdict_result(tmp_path),
        activation_decisions={
            ActivationUnit.V3_SHADOW_VERDICT.value: True,
            ActivationUnit.NUMERIC_VERDICT_RATES.value: False,
        },
        vn_gate_state=_all_vn_gate_state(),
        denominator_contract_satisfied=False,
        v3_shadow_verdict="PASS",
    )

    assert "v3_shadow_verdict: `PASS`" in summary
    assert "shadow_verdict_rendering: `rendered`" in summary
    assert "verdict_match_rate: `N/A`" in summary


def test_operator_summary_renders_numeric_rates_only_after_shadow_and_denominator_gate(tmp_path: Path) -> None:
    summary = build_bridge_operator_summary(
        _full_verdict_result(tmp_path),
        activation_decisions={
            ActivationUnit.V3_SHADOW_VERDICT.value: True,
            ActivationUnit.NUMERIC_VERDICT_RATES.value: True,
        },
        vn_gate_state=_all_vn_gate_state(),
        denominator_contract_satisfied=True,
        v3_shadow_verdict="PASS",
    )

    assert "v3_shadow_verdict: `PASS`" in summary
    assert "verdict_match_rate: `1/1 (100.0%)`" in summary
    assert "verdict_mismatch_rate: `0/1 (0.0%)`" in summary
    assert "numeric_verdict_rates_suppression_reason: `none`" in summary


def test_operator_summary_blocks_numeric_rates_when_shadow_verdict_is_inactive(tmp_path: Path) -> None:
    summary = build_bridge_operator_summary(
        _full_verdict_result(tmp_path),
        activation_decisions={
            ActivationUnit.V3_SHADOW_VERDICT.value: False,
            ActivationUnit.NUMERIC_VERDICT_RATES.value: True,
        },
        vn_gate_state=_all_vn_gate_state(),
        denominator_contract_satisfied=True,
    )

    assert "v3_shadow_verdict:" not in summary
    assert "verdict_match_rate: `N/A`" in summary
    assert (
        "numeric_verdict_rates_suppression_reason: "
        "`shadow_verdict_inactive:activation_decision_not_accepted`"
    ) in summary


def test_current_partial_surface_keeps_rule3b_v3_only_and_cap_out_of_comparable_surface(tmp_path: Path) -> None:
    result = _bridge_result(tmp_path, include_cap=True, include_catalytic=True)
    summary_payload = build_bridge_comparison_summary_payload(result)
    operator_summary = build_bridge_operator_summary(result)

    assert summary_payload["comparable_channels"] == ["path", "catalytic"]
    assert "cap" not in summary_payload["comparable_channels"]
    assert "catalytic_rule3b" not in summary_payload["component_matches"]
    assert "Rule3B remains [v3-only]." in operator_summary
    assert "[v3-only] cap: `observation_materialized`" in operator_summary


def test_mixed_summary_request_hard_blocks_operator_rendering() -> None:
    with pytest.raises(ReportGuardError, match="mixed semantic source is forbidden"):
        render_guarded_exploratory_report(
            artifact_name="bridge_operator_summary.md",
            metadata={
                "semantic_policy_version": "v3.test",
                "verdict_comparability": "partially_comparable",
                "verdict_match_rate": "N/A",
                "inventory_authority": build_inventory_authority_payload(
                    rc2_output_inventory_mutated=False,
                ),
                "comparable_channels": ("path", "catalytic"),
                "v3_only_evidence_channels": (),
                "channel_lifecycle_states": {
                    "path": "observation_materialized",
                    "catalytic": "applicability_only",
                },
                "component_matches": {"path": True, "catalytic_rule3a": None},
            },
            sections=[{"semantic_source": "mixed", "label": "[exploratory] mixed summary"}],
            lines=[
                "# [exploratory] Bridge Operator Summary",
                "- semantic_policy_version: `v3.test`",
            ],
        )


def test_sidecar_records_suppression_reasons_and_promotion_state_without_changing_boundary(tmp_path: Path) -> None:
    snapshot = _build_snapshot(tmp_path)

    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options(
            {
                "v3_sidecar": {
                    "enabled": True,
                    "artifact_policy": "full",
                    "channels": {"catalytic": {"enabled": True}},
                }
            }
        ),
        comparator_options=BridgeComparatorOptions(enabled=True),
    )

    assert result is not None
    sidecar_root = tmp_path / "run" / "v3_sidecar"
    operator_summary = (sidecar_root / "bridge_operator_summary.md").read_text(encoding="utf-8")
    operator_state = json.loads((sidecar_root / "operator_surface_state.json").read_text(encoding="utf-8"))
    run_record = json.loads((sidecar_root / "sidecar_run_record.json").read_text(encoding="utf-8"))
    required_candidacy = json.loads(
        (sidecar_root / "required_ci_candidacy_report.json").read_text(encoding="utf-8")
    )

    assert operator_summary.startswith("# [exploratory] Bridge Operator Summary")
    assert "rc2 display role: `primary`" in operator_summary
    assert "v3 display role: `[exploratory] secondary`" in operator_summary
    assert "Path and catalytic component indicators remain component-level only; they are not verdict proxies." in operator_summary
    assert "verdict_match_rate: `N/A`" in operator_summary
    assert "v3_shadow_verdict:" not in operator_summary

    assert operator_state["activation_decisions"] == {
        "v3_shadow_verdict": False,
        "numeric_verdict_rates": False,
    }
    assert operator_state["full_verdict_computable"] is False
    assert "vn_gate_state" in operator_state
    assert {
        item["surface"]: item["reason"]
        for item in operator_state["suppressed_surfaces"]
    } == {
        "v3_shadow_verdict": "activation_decision_not_accepted",
        "numeric_verdict_rates": "numeric_activation_decision_not_accepted",
    }
    assert run_record["bridge_diagnostics"]["operator_surface_state"] == operator_state
    assert run_record["bridge_diagnostics"]["operator_surface_state_artifact"] == "operator_surface_state.json"

    assert tuple(required_candidacy["pr_gates"]) == (
        "PR-01",
        "PR-02",
        "PR-03",
        "PR-04",
        "PR-05",
        "PR-06",
    )
    for gate_id, gate in required_candidacy["pr_gates"].items():
        assert gate["authority_reference"]["gate_id"] == gate_id
        assert gate["authority_reference"]["document"] == "adr_v3_10_full_migration_contract.md"
        assert gate["authority_reference"]["section"] == "CI promotion gate"
