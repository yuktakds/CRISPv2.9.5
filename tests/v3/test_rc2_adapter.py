from __future__ import annotations

from crisp.v3.adapters.rc2 import RC2Adapter
from tests.v3.helpers import make_config, write_pat_fixture


def test_rc2_adapter_adapts_path_fixture_without_claiming_final_verdict(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_blockage_supported.json")

    result = RC2Adapter().adapt_path_only(
        run_id="run-1",
        config=make_config(),
        pat_diagnostics_path=pat_path,
    )

    assert result.reference_kind == "rc2_path_diagnostics_input"
    assert result.coverage_channels == ("path",)
    assert result.unavailable_channels == ()
    assert result.notes == ()
    assert len(result.bundle.observations) == 1
    observation = result.bundle.observations[0]
    assert observation.channel_name == "path"
    assert observation.verdict is None
    assert observation.evidence_state is None
    assert observation.payload["quantitative_metrics"]["max_blockage_ratio"] == 0.78
    assert observation.payload["quantitative_metrics"]["numeric_resolution_limited"] is None
    assert observation.payload["exploration_slice"]["apo_accessible_goal_voxels"] == 6
    assert observation.payload["witness_bundle"]["witness_pose_id"] == "pose-supported"


def test_rc2_adapter_tracks_goal_precheck_failure_as_applicability_only(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat-goal-fail.json", "pat_goal_precheck_failure.json")

    result = RC2Adapter().adapt_path_only(
        run_id="run-1",
        config=make_config(),
        pat_diagnostics_path=pat_path,
    )

    assert result.coverage_channels == ()
    assert result.unavailable_channels == ("path",)
    assert result.bundle.observations == []
    assert [record.reason_code for record in result.bundle.applicability_records] == ["PAT_GOAL_INVALID"]
