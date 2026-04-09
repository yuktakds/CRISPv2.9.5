from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.keep_path_rc_campaign import (
    KEEP_PATH_RC_CAMPAIGN_INDEX_ARTIFACT,
    materialize_keep_path_rc_campaign,
    write_keep_path_rc_campaign_index,
)
from tests.v3.test_keep_path_rc_gate import (
    _bridge_summary,
    _build_docs_bundle,
    _output_inventory,
    _sidecar_run_record,
    _verdict_record,
    _write_json,
)


def _build_named_run_dir(
    tmp_path: Path,
    *,
    run_name: str,
    verdict_match_rate: float | None = None,
) -> Path:
    run_dir = tmp_path / run_name
    sidecar_dir = run_dir / "v3_sidecar"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "output_inventory.json", _output_inventory())
    _write_json(
        sidecar_dir / "sidecar_run_record.json",
        _sidecar_run_record() | {"rc2_outputs_unchanged": True},
    )
    verdict_record = _verdict_record()
    verdict_record["verdict_match_rate"] = verdict_match_rate
    _write_json(sidecar_dir / "verdict_record.json", verdict_record)
    _write_json(sidecar_dir / "bridge_comparison_summary.json", _bridge_summary())
    (sidecar_dir / "bridge_operator_summary.md").write_text(
        "# [exploratory] Bridge Operator Summary\n"
        "- semantic_policy_version: `crisp.v3.semantic_policy/rev3-sidecar-first`\n"
        "- verdict_match_rate: `N/A`\n",
        encoding="utf-8",
    )
    return run_dir


def test_keep_path_rc_campaign_materializes_per_run_reports_and_index(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    docs_root, evidence_dir = _build_docs_bundle(tmp_path)
    run_dirs = [
        _build_named_run_dir(runs_root, run_name="run-01"),
        _build_named_run_dir(runs_root, run_name="run-02"),
    ]

    payload = materialize_keep_path_rc_campaign(
        run_dirs=run_dirs,
        docs_root=docs_root,
        evidence_dir=evidence_dir,
        output_dir=evidence_dir,
    )
    index_path = write_keep_path_rc_campaign_index(
        output_dir=evidence_dir,
        payload=payload,
    )

    assert payload["aggregate"]["run_count"] == 2
    assert payload["aggregate"]["campaign_passed"] is True
    assert payload["aggregate"]["same_semantic_policy_version"] is True
    assert payload["aggregate"]["path_component_match_rate_values"] == [1.0]
    assert payload["aggregate"]["metrics_drift_zero_all_runs"] is True
    assert payload["runs"][0]["gate_conditions"]["comparable_channels_path_only"] is True
    assert (evidence_dir / "campaign_runs" / "run-01" / "rc_gate_keep_path_report.json").exists()
    assert index_path.name == KEEP_PATH_RC_CAMPAIGN_INDEX_ARTIFACT
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_payload["aggregate"]["campaign_passed"] is True


def test_keep_path_rc_campaign_fails_when_one_run_breaks_keep_scope(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    docs_root, evidence_dir = _build_docs_bundle(tmp_path)
    run_dirs = [
        _build_named_run_dir(runs_root, run_name="run-01"),
        _build_named_run_dir(runs_root, run_name="run-02", verdict_match_rate=1.0),
    ]

    payload = materialize_keep_path_rc_campaign(
        run_dirs=run_dirs,
        docs_root=docs_root,
        evidence_dir=evidence_dir,
        output_dir=evidence_dir,
    )

    assert payload["aggregate"]["gate_failed_count"] == 1
    assert payload["aggregate"]["campaign_passed"] is False
    assert payload["runs"][1]["gate_passed"] is False
