from __future__ import annotations

from dataclasses import replace

from crisp.v3.adapters.rc2 import RC2Adapter
from crisp.v3.comparator import BridgeComparator
from crisp.v3.contracts import RunApplicabilityRecord
from crisp.v3.policy import SEMANTIC_POLICY_VERSION
from tests.v3.helpers import build_v3_shadow_bundle, make_config, write_pat_fixture


def test_bridge_comparator_reports_partial_path_comparability_without_drift(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_blockage_supported.json")
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

    assert result.summary.comparison_scope.value == "path_only_partial"
    assert result.summary.verdict_comparability.value == "partially_comparable"
    assert result.summary.comparable_channels == ("path",)
    assert result.summary.unavailable_channels == ()
    assert result.summary.channel_coverage == {"path": "comparable"}
    assert result.drifts == ()


def test_bridge_comparator_classifies_metrics_witness_and_applicability_drift(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_blockage_supported.json")
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
    mutated_observation = replace(
        v3_bundle.observations[0],
        payload={
            **v3_bundle.observations[0].payload,
            "blockage_ratio": 0.11,
            "witness_pose_id": "pose-shifted",
            "pathyes_rule1_applicability": "PATH_NOT_EVALUABLE",
        },
    )
    mutated_bundle = replace(
        v3_bundle,
        observations=[mutated_observation],
        applicability_records=[
            RunApplicabilityRecord(
                channel_name="path",
                family="TUNNEL",
                scope="run",
                applicable=False,
                reason_code="PAT_GOAL_INVALID",
                detail="goal_precheck_passed=false",
            )
        ],
    )

    result = BridgeComparator().compare(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        rc2_adapt_result=rc2_result,
        v3_bundle=mutated_bundle,
    )

    drift_kinds = [drift.drift_kind for drift in result.drifts]
    assert "metrics_drift" in drift_kinds
    assert "witness_drift" in drift_kinds
    assert "applicability_drift" in drift_kinds
