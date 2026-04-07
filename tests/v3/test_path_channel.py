from __future__ import annotations

from pathlib import Path

from crisp.v3.contracts import EvidenceState
from crisp.v3.path_channel import PathEvidenceChannel
from tests.v3.helpers import make_config, write_pat_payload


def test_path_channel_marks_supported_when_blockage_clears_threshold(tmp_path: Path) -> None:
    pat_path = write_pat_payload(
        tmp_path / "pat.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.8,
                "apo_accessible_goal_voxels": 4,
                "feasible_count": 7,
                "witness_pose_id": "pose-1",
                "obstruction_path_ids": ["path-a", "path-b"],
            },
        },
    )

    result = PathEvidenceChannel().evaluate(
        config=make_config(blockage_pass_threshold=0.5),
        pat_diagnostics_path=pat_path,
    )

    assert result.applicability_records == []
    assert result.evidence is not None
    assert result.evidence.state is EvidenceState.SUPPORTED
    assert result.evidence.payload["blockage_ratio"] == 0.8
    assert result.evidence.payload["apo_accessible_goal_voxels"] == 4
    assert result.evidence.payload["witness_pose_id"] == "pose-1"
    assert result.evidence.payload["obstruction_path_ids"] == ["path-a", "path-b"]


def test_path_channel_marks_refuted_below_threshold(tmp_path: Path) -> None:
    pat_path = write_pat_payload(
        tmp_path / "pat.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.2,
                "apo_accessible_goal_voxels": 2,
            },
        },
    )

    result = PathEvidenceChannel().evaluate(
        config=make_config(blockage_pass_threshold=0.5),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is not None
    assert result.evidence.state is EvidenceState.REFUTED
    assert result.evidence.payload["numeric_resolution_limited"] is False


def test_path_channel_marks_insufficient_for_numeric_resolution_limit(tmp_path: Path) -> None:
    pat_path = write_pat_payload(
        tmp_path / "pat.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.9,
                "apo_accessible_goal_voxels": 2,
                "numeric_resolution_limited": True,
                "persistence_confidence": 0.05,
            },
        },
    )

    result = PathEvidenceChannel().evaluate(
        config=make_config(blockage_pass_threshold=0.5),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is not None
    assert result.evidence.state is EvidenceState.INSUFFICIENT
    assert result.evidence.payload["persistence_confidence"] == 0.05
    assert result.evidence.bridge_metrics["persistence_confidence"] == 0.05

