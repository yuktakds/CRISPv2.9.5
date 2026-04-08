from __future__ import annotations

from crisp.v3.adapters.rc2 import RC2Adapter
from crisp.v3.comparator import BridgeComparator
from crisp.v3.policy import SEMANTIC_POLICY_VERSION
from crisp.v3.reports import (
    build_bridge_comparison_summary_payload,
    build_bridge_drift_rows,
    build_bridge_operator_summary,
)
from tests.v3.helpers import build_v3_shadow_bundle, make_config, write_pat_fixture


def test_bridge_reports_surface_scope_comparability_and_semantic_policy(tmp_path: Path) -> None:
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
    )
    result = BridgeComparator().compare(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        rc2_adapt_result=rc2_result,
        v3_bundle=v3_bundle,
    )

    summary_payload = build_bridge_comparison_summary_payload(result)
    drift_rows = build_bridge_drift_rows(result)
    operator_summary = build_bridge_operator_summary(result)

    assert summary_payload["semantic_policy_version"] == SEMANTIC_POLICY_VERSION
    assert summary_payload["comparison_scope"] == "path_only_partial"
    assert summary_payload["verdict_comparability"] == "partially_comparable"
    assert summary_payload["channel_coverage"] == {"path": "present_on_both_sides"}
    assert summary_payload["channel_comparability"] == {"path": "component_verdict_comparable"}
    assert summary_payload["component_matches"] == {"path": True}
    assert summary_payload["run_drift_report"]["component_verdict_comparable_count"] == 1
    assert summary_payload["run_drift_report"]["component_match_count"] == 1
    assert summary_payload["run_drift_report"]["path_component_match_rate"] == 1.0
    assert drift_rows == []
    assert "semantic_policy_version" in operator_summary
    assert "[exploratory] Bridge Operator Summary" in operator_summary
    assert "verdict_match_rate: `N/A`" in operator_summary
    assert "path_component_match_rate: `1/1 (100.0%)`" in operator_summary
    assert "comparable_subset_size: `1`" in operator_summary
    assert "coverage_drift_count: `0`" in operator_summary
    assert "applicability_drift_count: `0`" in operator_summary
    assert "metrics_drift_count: `0`" in operator_summary
    assert "path_only_partial" in operator_summary
    assert "partially_comparable" in operator_summary
    assert "[exploratory] only" in operator_summary
    assert "v3_sidecar/generator_manifest.json" in operator_summary
    assert "generator_manifest.outputs" in operator_summary
    assert "output_inventory.json" in operator_summary
    assert "output_inventory.generated_outputs" in operator_summary
    assert "rc2 display role: `primary`" in operator_summary
    assert "v3 display role: `[exploratory] secondary`" in operator_summary
