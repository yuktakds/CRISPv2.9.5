from __future__ import annotations

from pathlib import Path

from crisp.v3.contracts import EvidenceState
from crisp.v3.path_channel import PathEvidenceChannel
from tests.v3.helpers import make_config, write_pat_payload


def test_goal_precheck_failure_becomes_run_level_applicability_record(tmp_path: Path) -> None:
    pat_path = write_pat_payload(
        tmp_path / "pat-goal-invalid.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": False,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.8,
                "apo_accessible_goal_voxels": 3,
            },
        },
    )

    result = PathEvidenceChannel().evaluate(
        config=make_config(),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is None
    assert [record.reason_code for record in result.applicability_records] == ["PAT_GOAL_INVALID"]


def test_persistence_confidence_is_recorded_but_not_used_as_a_gate(tmp_path: Path) -> None:
    high_conf_pat = write_pat_payload(
        tmp_path / "pat-high.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.7,
                "apo_accessible_goal_voxels": 3,
                "persistence_confidence": 0.95,
            },
        },
    )
    low_conf_pat = write_pat_payload(
        tmp_path / "pat-low.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.7,
                "apo_accessible_goal_voxels": 3,
                "persistence_confidence": 0.01,
            },
        },
    )

    channel = PathEvidenceChannel()
    high_conf = channel.evaluate(config=make_config(), pat_diagnostics_path=high_conf_pat)
    low_conf = channel.evaluate(config=make_config(), pat_diagnostics_path=low_conf_pat)

    assert high_conf.evidence is not None
    assert low_conf.evidence is not None
    assert high_conf.evidence.state is EvidenceState.SUPPORTED
    assert low_conf.evidence.state is EvidenceState.SUPPORTED
    assert high_conf.evidence.payload["persistence_confidence"] == 0.95
    assert low_conf.evidence.payload["persistence_confidence"] == 0.01

