from __future__ import annotations

from pathlib import Path

from crisp.v3.adapters.rc2_bridge import RC2BridgeAdapter
from crisp.v3.comparator import BridgeComparator
from crisp.v3.policy import SEMANTIC_POLICY_VERSION
from crisp.v3.reports import build_bridge_comparison_summary_payload, build_bridge_operator_summary
from tests.v3.helpers import build_v3_shadow_bundle, make_config, write_pat_fixture, write_pat_payload


def test_rc2_bridge_preserves_missing_fields_without_guessing(tmp_path: Path) -> None:
    pat_path = write_pat_payload(
        tmp_path / "pat-missing.json",
        {
            "goal_precheck_passed": True,
            "supported_path_model": True,
            "pat_run_diagnostics_json": {
                "apo_accessible_goal_voxels": 3,
                "blockage_ratio": 0.81,
            },
        },
    )

    result = RC2BridgeAdapter().adapt_path_only(
        run_id="run-1",
        config=make_config(),
        pat_diagnostics_path=pat_path,
    )

    assert result.coverage_channels == ("path",)
    assert result.unavailable_channels == ()
    observation = result.bundle.observations[0]
    assert observation.payload["quantitative_metrics"] == {
        "max_blockage_ratio": 0.81,
        "numeric_resolution_limited": None,
        "persistence_confidence": None,
    }
    assert observation.payload["exploration_slice"] == {
        "apo_accessible_goal_voxels": 3,
        "goal_voxel_count": None,
        "feasible_count": None,
    }
    assert observation.payload["witness_bundle"] == {
        "witness_pose_id": None,
        "obstruction_path_ids": None,
        "path_family": "TUNNEL",
    }
    assert observation.payload["numeric_resolution_limited"] is None
    assert observation.bridge_metrics["missing_fields_not_inferred"] is True
    assert observation.bridge_metrics["blockage_pass_threshold"] == 0.5


def test_rc2_bridge_tracks_goal_precheck_failure_as_applicability_only(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat-goal-fail.json", "pat_goal_precheck_failure.json")

    result = RC2BridgeAdapter().adapt_path_only(
        run_id="run-1",
        config=make_config(),
        pat_diagnostics_path=pat_path,
    )

    assert result.coverage_channels == ()
    assert result.unavailable_channels == ("path",)
    assert result.bundle.observations == []
    assert [record.reason_code for record in result.bundle.applicability_records] == ["PAT_GOAL_INVALID"]


def test_rc2_bridge_reports_include_header_and_semantic_policy_display(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
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

    summary_payload = build_bridge_comparison_summary_payload(result)
    operator_summary = build_bridge_operator_summary(result)

    assert summary_payload["bridge_header"] == {
        "semantic_policy_version": SEMANTIC_POLICY_VERSION,
        "comparator_scope": "path_and_catalytic_partial",
        "verdict_comparability": "partially_comparable",
        "comparable_channels": ("path", "catalytic"),
        "rc2_policy_version": "v2.9.5-rc2",
    }
    assert "semantic_policy_version" in operator_summary
    assert SEMANTIC_POLICY_VERSION in operator_summary
    assert "comparator_scope" in operator_summary
    assert "path_and_catalytic_partial" in operator_summary
    assert "catalytic_rule3a_component_match: `N/A`" in operator_summary
    assert "rc2_policy_version" in operator_summary
