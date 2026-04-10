from __future__ import annotations

from crisp.v3.pathyes import PathYesState, pathyes_contract_fields
from crisp.v3.path_channel import project_path_payload


def test_path_projector_uses_raw_pat_quantities_not_contract_projection() -> None:
    pathyes_state = PathYesState(
        supported_path_model=True,
        goal_precheck_passed=True,
        pat_run_diagnostics_json={"probe_count": 4},
        rule1_applicability="PATH_EVALUABLE",
        mode="pat-backed",
        source="pat_diagnostics_json",
        diagnostics_status="loaded",
        diagnostics_source_path="pat.json",
    )
    contract_projection = pathyes_contract_fields(pathyes_state)
    assert "blockage_ratio" not in contract_projection

    projected = project_path_payload(
        raw_payload={
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.66,
                "apo_accessible_goal_voxels": 8,
                "feasible_count": 11,
                "witness_pose_id": "pose-9",
                "obstruction_path_ids": [1, 2, 3],
                "persistence_confidence": 0.4,
            },
        },
        diagnostics_source="pat.json",
        blockage_threshold=0.5,
        pathyes_state=pathyes_state,
    )

    assert projected["blockage_ratio"] == 0.66
    assert projected["quantitative_metrics"] == {
        "max_blockage_ratio": 0.66,
        "numeric_resolution_limited": None,
        "persistence_confidence": 0.4,
    }
    assert projected["exploration_slice"] == {
        "apo_accessible_goal_voxels": 8,
        "goal_voxel_count": None,
        "feasible_count": 11,
    }
    assert projected["witness_bundle"] == {
        "witness_pose_id": "pose-9",
        "obstruction_path_ids": ["1", "2", "3"],
        "path_family": "TUNNEL",
    }
    assert projected["apo_accessible_goal_voxels"] == 8
    assert projected["feasible_count"] == 11
    assert projected["witness_pose_id"] == "pose-9"
    assert projected["obstruction_path_ids"] == ["1", "2", "3"]
    assert projected["persistence_confidence"] == 0.4
    assert projected["pathyes_mode_resolved"] == "pat-backed"
