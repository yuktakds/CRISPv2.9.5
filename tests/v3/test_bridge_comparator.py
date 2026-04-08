from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from crisp.v3.adapters.rc2 import RC2Adapter
from crisp.v3.comparator import BridgeComparator
from crisp.v3.contracts import CompoundPathComparability
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
    assert result.summary.channel_coverage == {"path": "present_on_both_sides"}
    assert result.summary.channel_comparability == {"path": "component_verdict_comparable"}
    assert result.summary.component_matches == {"path": True}
    assert result.run_report.comparable_subset_size == 1
    assert result.run_report.component_verdict_comparable_count == 1
    assert result.run_report.component_match_count == 1
    assert result.run_report.path_component_match_rate == 1.0
    assert result.drifts == ()


def test_bridge_comparator_treats_witness_drift_as_non_blocking(tmp_path: Path) -> None:
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
    original_payload = v3_bundle.observations[0].payload
    mutated_payload = {
        **original_payload,
        "witness_pose_id": "pose-shifted",
        "witness_bundle": {
            **original_payload["witness_bundle"],
            "witness_pose_id": "pose-shifted",
        },
    }
    mutated_bundle = replace(
        v3_bundle,
        observations=[replace(v3_bundle.observations[0], payload=mutated_payload)],
    )

    result = BridgeComparator().compare(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        rc2_adapt_result=rc2_result,
        v3_bundle=mutated_bundle,
    )

    assert result.summary.channel_comparability == {
        "path": CompoundPathComparability.COMPONENT_VERDICT_COMPARABLE.value
    }
    assert result.summary.component_matches == {"path": True}
    assert result.run_report.component_verdict_comparable_count == 1
    assert result.run_report.component_match_count == 1
    assert [drift.drift_kind for drift in result.drifts] == ["witness_drift"]


def test_bridge_comparator_classifies_metrics_and_applicability_drift(tmp_path: Path) -> None:
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
    original_payload = v3_bundle.observations[0].payload
    mutated_observation = replace(
        v3_bundle.observations[0],
        payload={
            **original_payload,
            "max_blockage_ratio": 0.11,
            "blockage_ratio": 0.11,
            "witness_pose_id": "pose-shifted",
            "quantitative_metrics": {
                **original_payload["quantitative_metrics"],
                "max_blockage_ratio": 0.11,
            },
            "witness_bundle": {
                **original_payload["witness_bundle"],
                "witness_pose_id": "pose-shifted",
            },
            "applicability": {
                **original_payload["applicability"],
                "pathyes_rule1_applicability": "PATH_NOT_EVALUABLE",
            },
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
    assert result.summary.comparable_channels == ()
    assert result.summary.channel_comparability == {
        "path": CompoundPathComparability.NOT_COMPARABLE.value
    }
    assert result.summary.component_matches == {"path": None}
    assert result.run_report.comparable_subset_size == 0
    assert result.run_report.component_verdict_comparable_count == 0
    assert result.run_report.path_component_match_rate is None


def test_bridge_comparator_reports_metrics_drift_as_evidence_comparable(tmp_path: Path) -> None:
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
    original_payload = v3_bundle.observations[0].payload
    mutated_bundle = replace(
        v3_bundle,
        observations=[
            replace(
                v3_bundle.observations[0],
                payload={
                    **original_payload,
                    "max_blockage_ratio": 0.79,
                    "blockage_ratio": 0.79,
                    "quantitative_metrics": {
                        **original_payload["quantitative_metrics"],
                        "max_blockage_ratio": 0.79,
                    },
                },
            )
        ],
    )

    result = BridgeComparator().compare(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        rc2_adapt_result=rc2_result,
        v3_bundle=mutated_bundle,
    )

    assert result.summary.channel_comparability == {
        "path": CompoundPathComparability.EVIDENCE_COMPARABLE.value
    }
    assert result.summary.component_matches == {"path": True}
    assert result.run_report.component_verdict_comparable_count == 1
    assert result.run_report.component_match_count == 1
    assert result.run_report.path_component_match_rate == 1.0
    assert [drift.drift_kind for drift in result.drifts] == ["metrics_drift"]
