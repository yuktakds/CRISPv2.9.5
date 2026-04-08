from __future__ import annotations

from pathlib import Path

from crisp.v3.adapters.rc2_bridge import RC2BridgeAdapter
from crisp.v3.path_channel import PathEvidenceChannel
from tests.v3.helpers import make_config, write_pat_fixture


def test_path_adapter_behavior_preserves_missing_numeric_resolution_as_none(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_blockage_supported.json")
    config = make_config()

    channel_result = PathEvidenceChannel().evaluate(
        config=config,
        pat_diagnostics_path=pat_path,
    )
    bridge_result = RC2BridgeAdapter().adapt_path_only(
        run_id="run-1",
        config=config,
        pat_diagnostics_path=pat_path,
    )

    assert channel_result.evidence is not None
    assert channel_result.evidence.payload["numeric_resolution_limited"] is None
    assert channel_result.evidence.payload["quantitative_metrics"]["numeric_resolution_limited"] is None
    assert bridge_result.bundle.observations[0].payload["numeric_resolution_limited"] is None
    assert bridge_result.bundle.observations[0].payload["quantitative_metrics"]["numeric_resolution_limited"] is None


def test_path_adapter_behavior_keeps_nested_canonical_payload_and_flat_aliases(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
    config = make_config()

    channel_result = PathEvidenceChannel().evaluate(
        config=config,
        pat_diagnostics_path=pat_path,
    )
    bridge_result = RC2BridgeAdapter().adapt_path_only(
        run_id="run-1",
        config=config,
        pat_diagnostics_path=pat_path,
    )

    assert channel_result.evidence is not None
    assert channel_result.evidence.payload["blockage_ratio"] == 0.92
    assert channel_result.evidence.payload["quantitative_metrics"]["max_blockage_ratio"] == 0.92
    assert channel_result.evidence.payload["exploration_slice"]["apo_accessible_goal_voxels"] == 4
    assert channel_result.evidence.payload["witness_bundle"]["witness_pose_id"] == "pose-numeric-limit"

    observation = bridge_result.bundle.observations[0]
    assert observation.payload["blockage_ratio"] == 0.92
    assert observation.payload["quantitative_metrics"]["max_blockage_ratio"] == 0.92
    assert observation.payload["exploration_slice"]["apo_accessible_goal_voxels"] == 4
    assert observation.payload["witness_bundle"]["witness_pose_id"] == "pose-numeric-limit"
