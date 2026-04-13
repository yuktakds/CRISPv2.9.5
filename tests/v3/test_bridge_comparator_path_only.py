from __future__ import annotations

from crisp.v3.adapters.rc2_bridge import RC2BridgeAdapter
from crisp.v3.bridge.comparator import PARTIAL_SCOPE_COMPARATOR_CONTRACT_VERSION, BridgeComparator
from crisp.v3.policy import SEMANTIC_POLICY_VERSION
from tests.v3.helpers import build_v3_shadow_bundle, make_config, write_pat_fixture


def test_bridge_comparator_freezes_current_public_partial_scope_without_drift(tmp_path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_blockage_supported.json")
    config = make_config()
    rc2_result = RC2BridgeAdapter().adapt_path_only(
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

    assert PARTIAL_SCOPE_COMPARATOR_CONTRACT_VERSION == "crisp.v3.bridge_comparator.partial_scope/v1"
    assert result.summary.comparison_scope.value == "path_and_catalytic_partial"
    assert result.summary.verdict_comparability.value == "partially_comparable"
    assert result.summary.comparable_channels == ("path", "catalytic")
    assert result.summary.unavailable_channels == ("catalytic",)
    assert result.summary.channel_coverage == {"path": "present_on_both_sides"}
    assert result.summary.channel_comparability == {"path": "component_verdict_comparable"}
    assert result.summary.component_matches == {"path": True}
    assert "PATH_COMPONENT_BRIDGE_CONSUMER_PRESENT" in result.summary.run_level_flags
    assert "PATH_COMPONENT_VERDICT_COMPARABILITY_DEFINED" in result.summary.run_level_flags
    assert result.run_report.component_verdict_comparable_count == 1
    assert result.run_report.component_match_count == 1
    assert result.run_report.path_component_match_rate == 1.0
    assert result.drifts == ()
