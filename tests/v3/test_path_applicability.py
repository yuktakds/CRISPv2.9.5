from __future__ import annotations

from pathlib import Path

from crisp.v3.path_channel import PathEvidenceChannel
from tests.v3.helpers import make_config, write_pat_payload


def test_path_channel_rejects_non_tunnel_family(tmp_path: Path) -> None:
    pat_path = write_pat_payload(
        tmp_path / "pat.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.7,
                "apo_accessible_goal_voxels": 3,
            },
        },
    )

    result = PathEvidenceChannel().evaluate(
        config=make_config(path_model="SURFACE_LIKE"),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is None
    assert [record.reason_code for record in result.applicability_records] == ["PAT_UNSUPPORTED_PATH_MODEL"]


def test_path_channel_rejects_missing_apo_baseline(tmp_path: Path) -> None:
    pat_path = write_pat_payload(
        tmp_path / "pat.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.7,
                "apo_accessible_goal_voxels": 0,
            },
        },
    )

    result = PathEvidenceChannel().evaluate(
        config=make_config(),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is None
    assert [record.reason_code for record in result.applicability_records] == ["PAT_APO_BASELINE_ABSENT"]


def test_path_channel_records_missing_pat_path(tmp_path: Path) -> None:
    result = PathEvidenceChannel().evaluate(
        config=make_config(),
        pat_diagnostics_path=tmp_path / "missing.json",
    )

    assert result.evidence is None
    assert [record.reason_code for record in result.applicability_records] == ["PAT_DIAGNOSTICS_FILE_NOT_FOUND"]

