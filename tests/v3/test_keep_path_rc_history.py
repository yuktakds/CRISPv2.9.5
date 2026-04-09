from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.keep_path_rc_history import (
    KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT,
    KEEP_PATH_RC_HISTORY_SUMMARY_ARTIFACT,
    harvest_keep_path_rc_history,
    write_keep_path_rc_history_report,
    write_keep_path_rc_history_summary,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _build_hosted_run(
    history_root: Path,
    *,
    run_name: str,
    gate_passed: bool = True,
    campaign_passed: bool = True,
    smoke_passed: bool = True,
    exploratory_label_maintained: bool = True,
) -> Path:
    run_dir = history_root / run_name
    _write_json(
        run_dir / "hosted_run_metadata.json",
        {
            "schema_version": "crisp.v3.keep_path_rc_hosted_run_metadata/v1",
            "workflow_name": "v3 Keep-Path RC Exploratory",
            "workflow_path": ".github/workflows/v3-keep-path-rc-exploratory.yml",
            "runner_os": "Windows",
            "runner_label": "windows-latest",
            "exploratory_lane": True,
            "required_matrix_touched": False,
            "public_scope_widening_authorized": False,
            "required_promotion_authorized": False,
        },
    )
    _write_json(
        run_dir / "gate" / "rc_gate_keep_path_report.json",
        {
            "gate_passed": gate_passed,
            "run_facts": {
                "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
                "path_component_match_rate": 1.0,
                "coverage_drift_count": 0,
                "applicability_drift_count": 0,
                "metrics_drift_count": 0,
                "operator_surface_exploratory": exploratory_label_maintained,
                "output_inventory_unchanged": True,
            },
        },
    )
    _write_json(
        run_dir / "campaign" / "campaign_index.json",
        {
            "aggregate": {
                "campaign_passed": campaign_passed,
                "metric_contract_note": (
                    "path_component_match_rate is a Path-only metric. "
                    "It is not a full verdict proxy and does not replace verdict_match_rate."
                ),
            }
        },
    )
    _write_json(
        run_dir / "release_packet" / "release_packet_smoke_report.json",
        {
            "smoke_passed": smoke_passed,
        },
    )
    return run_dir


def test_keep_path_rc_history_harvester_collects_non_authorizing_keep_scope_evidence(tmp_path: Path) -> None:
    history_root = tmp_path / "history"
    _build_hosted_run(history_root, run_name="hosted-run-01")
    _build_hosted_run(history_root, run_name="hosted-run-02")

    payload = harvest_keep_path_rc_history(
        history_root=history_root,
    )

    assert payload["history_passed"] is True
    assert payload["aggregate"]["observed_run_count"] == 2
    assert payload["aggregate"]["all_gate_passed"] is True
    assert payload["aggregate"]["all_campaign_passed"] is True
    assert payload["aggregate"]["all_smoke_passed"] is True
    assert payload["aggregate"]["windows_hosted_success_all_runs"] is True
    assert payload["aggregate"]["required_promotion_authorized_any_run"] is False
    assert "does not authorize required promotion or public scope widening" in payload["aggregate"]["non_authorizing_statement"]

    report_path = write_keep_path_rc_history_report(
        output_dir=history_root,
        payload=payload,
    )
    summary_path = write_keep_path_rc_history_summary(
        output_dir=history_root,
        payload=payload,
    )
    assert report_path.name == KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT
    assert summary_path.name == KEEP_PATH_RC_HISTORY_SUMMARY_ARTIFACT
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "This is non-authorizing readiness evidence only." in summary_text
    assert "path_component_match_rate remains a Path-only component metric" in summary_text


def test_keep_path_rc_history_harvester_fails_when_one_hosted_run_breaks_exploratory_contract(tmp_path: Path) -> None:
    history_root = tmp_path / "history"
    _build_hosted_run(history_root, run_name="hosted-run-01")
    _build_hosted_run(
        history_root,
        run_name="hosted-run-02",
        exploratory_label_maintained=False,
    )

    payload = harvest_keep_path_rc_history(
        history_root=history_root,
    )

    assert payload["history_passed"] is False
    assert payload["aggregate"]["exploratory_label_maintained_all_runs"] is False
