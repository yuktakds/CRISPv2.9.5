from __future__ import annotations

from crisp.v3.adapters.rc2_bridge import (
    PATH_ONLY_COVERAGE_CONTRACT_VERSION,
    PATH_ONLY_COVERAGE_FIELDS,
    RC2BridgeAdapter,
)
from tests.v3.helpers import make_config, write_pat_payload


def test_rc2_bridge_freezes_path_only_coverage_contract(tmp_path) -> None:
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
    assert result.bundle.bridge_diagnostics["coverage_contract_version"] == PATH_ONLY_COVERAGE_CONTRACT_VERSION
    assert result.bundle.bridge_diagnostics["coverage_fields"] == {
        key: list(values) for key, values in PATH_ONLY_COVERAGE_FIELDS.items()
    }
    observation = result.bundle.observations[0]
    assert observation.payload["quantitative_metrics"] == {"blockage_ratio": 0.81}
    assert observation.payload["exploration_slice"] == {"apo_accessible_goal_voxels": 3}
    assert observation.payload["witness_bundle"] == {"path_family": "TUNNEL"}
    assert observation.bridge_metrics["missing_fields_not_inferred"] is True
