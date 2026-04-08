from __future__ import annotations

from pathlib import Path

from crisp.v3.contracts import EvidenceState
from crisp.v3.path_channel import PathEvidenceChannel
from tests.v3.helpers import make_config, write_pat_fixture


def test_goal_precheck_failure_fixture_stays_run_level_diagnostic(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat-goal-precheck-failure.json", "pat_goal_precheck_failure.json")

    result = PathEvidenceChannel().evaluate(
        config=make_config(),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is None
    assert [record.reason_code for record in result.applicability_records] == ["PAT_GOAL_INVALID"]


def test_numeric_resolution_limited_fixture_stays_insufficient(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(
        tmp_path / "pat-numeric-resolution-limited.json",
        "pat_numeric_resolution_limited.json",
    )

    result = PathEvidenceChannel().evaluate(
        config=make_config(),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is not None
    assert result.evidence.state is EvidenceState.INSUFFICIENT
    assert result.evidence.payload["numeric_resolution_limited"] is True
    assert result.evidence.payload["quantitative_metrics"]["numeric_resolution_limited"] is True


def test_blockage_supported_fixture_stays_supported(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(tmp_path / "pat-blockage-supported.json", "pat_blockage_supported.json")

    result = PathEvidenceChannel().evaluate(
        config=make_config(blockage_pass_threshold=0.5),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is not None
    assert result.evidence.state is EvidenceState.SUPPORTED
    assert result.evidence.payload["blockage_ratio"] == 0.78
    assert result.evidence.payload["quantitative_metrics"]["max_blockage_ratio"] == 0.78


def test_blockage_below_threshold_fixture_stays_refuted(tmp_path: Path) -> None:
    pat_path = write_pat_fixture(
        tmp_path / "pat-blockage-below-threshold.json",
        "pat_blockage_below_threshold.json",
    )

    result = PathEvidenceChannel().evaluate(
        config=make_config(blockage_pass_threshold=0.5),
        pat_diagnostics_path=pat_path,
    )

    assert result.evidence is not None
    assert result.evidence.state is EvidenceState.REFUTED
    assert result.evidence.payload["blockage_ratio"] == 0.21
    assert result.evidence.payload["quantitative_metrics"]["numeric_resolution_limited"] is None
