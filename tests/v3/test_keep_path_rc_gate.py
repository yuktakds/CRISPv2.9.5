from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.keep_path_rc_gate import (
    RC_GATE_KEEP_PATH_REPORT_ARTIFACT,
    evaluate_keep_path_rc_gate,
    write_keep_path_rc_gate_report,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _sidecar_run_record() -> dict[str, object]:
    return {
        "comparator_scope": "path_only_partial",
        "comparable_channels": ["path"],
        "v3_only_evidence_channels": ["cap", "catalytic"],
        "channel_lifecycle_states": {
            "path": "observation_materialized",
            "cap": "observation_materialized",
            "catalytic": "observation_materialized",
        },
        "channel_comparability": {
            "path": "component_verdict_comparable",
            "cap": None,
            "catalytic": None,
        },
        "bridge_diagnostics": {
            "layer0_authority_artifact": "verdict_record.json",
            "sidecar_run_record_role": "backward_compatible_mirror",
            "layer0_authority_mirror": {
                "run_id": "run-1",
                "output_root": "out/v3_sidecar",
                "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
                "comparator_scope": "path_only_partial",
                "comparable_channels": ["path"],
                "v3_only_evidence_channels": ["cap", "catalytic"],
                "channel_lifecycle_states": {
                    "path": "observation_materialized",
                    "cap": "observation_materialized",
                    "catalytic": "observation_materialized",
                },
                "full_verdict_computable": False,
                "full_verdict_comparable_count": 0,
                "verdict_match_rate": None,
                "verdict_mismatch_rate": None,
                "path_component_match_rate": 1.0,
                "v3_shadow_verdict": None,
                "authority_transfer_complete": True,
            },
        },
    }


def _verdict_record() -> dict[str, object]:
    return {
        "schema_version": "crisp.v3.verdict_record/v1",
        "run_id": "run-1",
        "output_root": "out/v3_sidecar",
        "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
        "comparator_scope": "path_only_partial",
        "comparable_channels": ["path"],
        "v3_only_evidence_channels": ["cap", "catalytic"],
        "channel_lifecycle_states": {
            "path": "observation_materialized",
            "cap": "observation_materialized",
            "catalytic": "observation_materialized",
        },
        "full_verdict_computable": False,
        "full_verdict_comparable_count": 0,
        "verdict_match_rate": None,
        "verdict_mismatch_rate": None,
        "path_component_match_rate": 1.0,
        "v3_shadow_verdict": None,
        "authority_transfer_complete": True,
        "sidecar_run_record_artifact": "sidecar_run_record.json",
        "generator_manifest_artifact": "generator_manifest.json",
    }


def _bridge_summary() -> dict[str, object]:
    return {
        "component_matches": {
            "path": True,
        }
    }


def _output_inventory() -> dict[str, object]:
    return {
        "generated_outputs": [
            "run_manifest.json",
            "output_inventory.json",
        ]
    }


def _monitoring_report() -> dict[str, object]:
    return {
        "required_window_size": 30,
        "observed_window_size": 30,
        "authority_phase_m2_streak": True,
        "dual_write_mismatch_zero_streak": True,
        "operator_surface_inactive_streak": True,
        "manifest_registration_complete_streak": True,
        "schema_complete_streak": True,
        "window_passed": True,
    }


def _build_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run-01"
    sidecar_dir = run_dir / "v3_sidecar"
    _write_json(run_dir / "output_inventory.json", _output_inventory())
    _write_json(sidecar_dir / "sidecar_run_record.json", _sidecar_run_record())
    _write_json(sidecar_dir / "verdict_record.json", _verdict_record())
    _write_json(sidecar_dir / "bridge_comparison_summary.json", _bridge_summary())
    (sidecar_dir / "bridge_operator_summary.md").write_text(
        "# [exploratory] Bridge Operator Summary\n"
        "- semantic_policy_version: `crisp.v3.semantic_policy/rev3-sidecar-first`\n"
        "- verdict_match_rate: `N/A`\n",
        encoding="utf-8",
    )
    return run_dir


def _build_docs_bundle(tmp_path: Path) -> tuple[Path, Path]:
    docs_root = tmp_path / "docs"
    evidence_dir = docs_root / "release" / "evidence" / "keep_path_rc" / "2026-04-09"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (docs_root / "README.md").write_text(
        "# Docs Index\n\n"
        "Current public-scope decision:\n\n"
        "- `wp6_public_inclusion_decision_memo.md`\n\n"
        "Current keep-path RC definition:\n\n"
        "- `v3_keep_path_rc_acceptance_memo.md`\n",
        encoding="utf-8",
    )
    (docs_root / "v3_keep_path_rc_acceptance_memo.md").write_text(
        "# v3 Keep-Path RC Acceptance Memo\n\n"
        "- keep-path RC is accepted as the current public-scope release candidate\n"
        "- no widening is authorized\n"
        "- no operator activation is authorized\n"
        "- `m2_rollback_drill_report.json`\n"
        "- `m2_rehearsal_report.json`\n"
        "- `m2_post_cutover_monitoring_report.json`\n",
        encoding="utf-8",
    )
    (docs_root / "v3_keep_path_rc_roadmap.md").write_text(
        "# v3 Keep-Path RC Roadmap\n\n"
        "This is the current public-scope release candidate.\n\n"
        "- `comparator_scope = path_only_partial`\n"
        "- `comparable_channels = [\"path\"]`\n",
        encoding="utf-8",
    )
    (evidence_dir / "README.md").write_text(
        "# Keep-Path RC Ops Evidence Index\n\n"
        "- `m2_rollback_drill_report.json`\n"
        "- `m2_rehearsal_report.json`\n"
        "- `m2_post_cutover_monitoring_report.json`\n"
        "- `run-01`\n"
        "- `run-30`\n",
        encoding="utf-8",
    )
    _write_json(
        evidence_dir / "m2_rollback_drill_report.json",
        {
            "drill_passed": True,
            "injected_fault_detected": True,
            "output_inventory_unchanged": True,
            "dual_write_mismatch_count": 0,
        },
    )
    _write_json(
        evidence_dir / "m2_rehearsal_report.json",
        {
            "rehearsal_passed": True,
            "round_trip_integrity": True,
            "primary_operator_surface_inactive": True,
            "rerun_operator_surface_inactive": True,
        },
    )
    _write_json(
        evidence_dir / "m2_post_cutover_monitoring_report.json",
        _monitoring_report(),
    )
    return docs_root, evidence_dir


def test_keep_path_rc_gate_accepts_valid_bundle_and_writes_report(tmp_path: Path) -> None:
    run_dir = _build_run_dir(tmp_path)
    docs_root, evidence_dir = _build_docs_bundle(tmp_path)

    payload = evaluate_keep_path_rc_gate(
        run_dir=run_dir,
        docs_root=docs_root,
        evidence_dir=evidence_dir,
    )

    assert payload["gate_passed"] is True
    assert payload["validator"]["passed"] is True
    assert payload["docs_bundle"]["passed"] is True
    assert payload["ops_bundle"]["passed"] is True

    report_path = write_keep_path_rc_gate_report(
        output_dir=evidence_dir,
        payload=payload,
    )
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_path.name == RC_GATE_KEEP_PATH_REPORT_ARTIFACT
    assert report_payload["gate_passed"] is True
    assert report_payload["gate_checks"] == {
        "validator_passed": True,
        "docs_bundle_passed": True,
        "ops_bundle_passed": True,
    }


def test_keep_path_rc_gate_rejects_missing_acceptance_memo_fragment(tmp_path: Path) -> None:
    run_dir = _build_run_dir(tmp_path)
    docs_root, evidence_dir = _build_docs_bundle(tmp_path)
    (docs_root / "v3_keep_path_rc_acceptance_memo.md").write_text(
        "# v3 Keep-Path RC Acceptance Memo\n\n"
        "- keep-path RC is accepted as the current public-scope release candidate\n"
        "- no operator activation is authorized\n",
        encoding="utf-8",
    )

    payload = evaluate_keep_path_rc_gate(
        run_dir=run_dir,
        docs_root=docs_root,
        evidence_dir=evidence_dir,
    )

    assert payload["gate_passed"] is False
    assert "RC_GATE_ACCEPTANCE_MEMO_MISSING:no widening is authorized" in payload["findings"]


def test_keep_path_rc_gate_rejects_non_green_monitoring_report(tmp_path: Path) -> None:
    run_dir = _build_run_dir(tmp_path)
    docs_root, evidence_dir = _build_docs_bundle(tmp_path)
    _write_json(
        evidence_dir / "m2_post_cutover_monitoring_report.json",
        {
            **_monitoring_report(),
            "window_passed": False,
        },
    )

    payload = evaluate_keep_path_rc_gate(
        run_dir=run_dir,
        docs_root=docs_root,
        evidence_dir=evidence_dir,
    )

    assert payload["gate_passed"] is False
    assert "RC_GATE_MONITORING_WINDOW_NOT_GREEN" in payload["findings"]
