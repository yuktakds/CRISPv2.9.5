from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from crisp.v3.keep_path_rc_audit import (
    KEEP_PATH_RC_HOSTILE_AUDIT_REPORT_ARTIFACT,
    KEEP_PATH_RC_HOSTILE_AUDIT_SUMMARY_ARTIFACT,
    evaluate_keep_path_rc_hostile_audit,
    write_keep_path_rc_hostile_audit_report,
    write_keep_path_rc_hostile_audit_summary,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _build_hostile_audit_bundle(
    repo_root: Path,
    *,
    metric_contract_note: str = (
        "path_component_match_rate is a Path-only metric. "
        "It is not a full verdict proxy and does not replace verdict_match_rate."
    ),
) -> tuple[Path, Path]:
    docs_root = repo_root / "docs"
    evidence_dir = docs_root / "release" / "evidence" / "keep_path_rc" / "2026-04-09"
    release_packet_dir = evidence_dir / "release_packet"
    workflow_dir = repo_root / ".github" / "workflows"
    docs_root.mkdir(parents=True, exist_ok=True)
    (docs_root / "release").mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    workflow_dir.mkdir(parents=True, exist_ok=True)

    (workflow_dir / "v29-required-matrix.yml").write_text(
        dedent(
            """
            name: v2.9.5 Required Matrix
            jobs:
              v3-sidecar-determinism:
                name: required / v3-sidecar-determinism
                steps:
                  - run: uv run pytest -q tests/v3/test_sidecar_invariants.py
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (workflow_dir / "v3-keep-path-rc-exploratory.yml").write_text(
        dedent(
            """
            name: v3 Keep-Path RC Exploratory
            jobs:
              keep-path-rc-contracts:
                name: exploratory / v3-keep-path-rc-contracts
                runs-on: windows-latest
                steps:
                  - run: uv run pytest -q tests/v3/test_keep_path_rc_exploratory_ci_workflow.py
              keep-path-rc-bundle:
                name: exploratory / v3-keep-path-rc-bundle
                runs-on: windows-latest
                steps:
                  - run: |
                      $metadata = [ordered]@{}
                      $metadata.required_promotion_authorized = $false
                      $metadata.public_scope_widening_authorized = $false
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (docs_root / "README.md").write_text(
        "# Docs Index\n\n"
        "Current public-scope decision:\n\n"
        "- `wp6_public_inclusion_decision_memo.md`\n\n"
        "Current keep-path RC definition:\n\n"
        "- `v3_keep_path_rc_acceptance_memo.md`\n\n"
        "Pending reopen-path work:\n\n"
        "- comparator_scope widening remains a separate human decision\n\n"
        "Supporting-note boundary:\n\n"
        "- pre-freeze / pre-M-2 fragments are non-authoritative\n",
        encoding="utf-8",
    )
    (docs_root / "v3_keep_path_rc_acceptance_memo.md").write_text(
        "# v3 Keep-Path RC Acceptance Memo\n\n"
        "- keep-path RC is accepted as the current public-scope release candidate\n"
        "- no widening is authorized\n"
        "- no operator activation is authorized\n"
        "- required promotion is not authorized\n"
        "- automation alone remains insufficient for widening or requiredization\n",
        encoding="utf-8",
    )
    (docs_root / "v3_keep_path_rc_roadmap.md").write_text(
        "# v3 Keep-Path RC Roadmap\n\n"
        "This is the current public-scope release candidate.\n\n"
        "- `comparator_scope = path_only_partial`\n"
        "- `comparable_channels = [\"path\"]`\n",
        encoding="utf-8",
    )
    (docs_root / "wp6_public_inclusion_decision_memo.md").write_text(
        "# WP-6 Public Inclusion Decision Memo\n\n"
        "## Inclusion Decision\n\n"
        "- comparator_scope: keep `path_only_partial`\n"
        "- comparable_channels: keep `[\"path\"]`\n"
        "- `v3_shadow_verdict`: inactive\n"
        "- `verdict_match_rate`: `N/A`\n\n"
        "This memo closes the current public inclusion decision as `keep`, not `widen`.\n\n"
        "## Boundary\n\n"
        "- pre-freeze fragments are superseded and non-authoritative\n",
        encoding="utf-8",
    )
    (docs_root / "release" / "README.md").write_text(
        "# Release Docs\n\n"
        "- `.github/workflows/v3-keep-path-rc-exploratory.yml`: it is not part of the required matrix\n",
        encoding="utf-8",
    )
    (evidence_dir / "README.md").write_text(
        "# Keep-Path RC Ops Evidence Index\n\n"
        "- `rc_gate_keep_path_report.json`\n"
        "- `campaign_index.json`\n"
        "- `keep_path_rc_history_report.json`\n",
        encoding="utf-8",
    )

    verdict_record = {
        "schema_version": "crisp.v3.verdict_record/v1",
        "run_id": "keep-path-rc",
        "output_root": "out/v3_sidecar",
        "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
        "comparator_scope": "path_only_partial",
        "comparable_channels": ["path"],
        "v3_only_evidence_channels": [],
        "channel_lifecycle_states": {
            "path": "observation_materialized",
            "cap": "disabled",
            "catalytic": "disabled",
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
    sidecar_run_record = {
        "run_id": "keep-path-rc",
        "output_root": "out/v3_sidecar",
        "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
        "comparator_scope": "path_only_partial",
        "comparable_channels": ["path"],
        "v3_only_evidence_channels": [],
        "channel_lifecycle_states": {
            "path": "observation_materialized",
            "cap": "disabled",
            "catalytic": "disabled",
        },
        "channel_comparability": {
            "path": "component_verdict_comparable",
            "cap": None,
            "catalytic": None,
        },
        "bridge_diagnostics": {
            "layer0_authority_artifact": "verdict_record.json",
            "layer0_authority_mode": "M2",
            "verdict_record_role": "canonical_layer0_authority",
            "sidecar_run_record_role": "backward_compatible_mirror",
            "layer0_authority_mirror": {
                "run_id": "keep-path-rc",
                "output_root": "out/v3_sidecar",
                "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
                "comparator_scope": "path_only_partial",
                "comparable_channels": ["path"],
                "v3_only_evidence_channels": [],
                "channel_lifecycle_states": {
                    "path": "observation_materialized",
                    "cap": "disabled",
                    "catalytic": "disabled",
                },
                "full_verdict_computable": False,
                "full_verdict_comparable_count": 0,
                "verdict_match_rate": None,
                "verdict_mismatch_rate": None,
                "path_component_match_rate": 1.0,
                "v3_shadow_verdict": None,
                "authority_transfer_complete": True,
            },
            "bridge_comparison_summary": {
                "component_matches": {"path": True},
                "run_drift_report": {
                    "full_verdict_computable": False,
                    "full_verdict_comparable_count": 0,
                    "verdict_match_rate": None,
                    "verdict_mismatch_rate": None,
                    "path_component_match_rate": 1.0,
                },
            },
        },
        "rc2_outputs_unchanged": True,
    }
    output_inventory = {
        "generated_outputs": [
            "run_manifest.json",
            "output_inventory.json",
        ]
    }
    generator_manifest = {
        "schema_version": "crisp.v3.generator_manifest/v1",
        "expected_output_digest": "sha256:test-digest",
        "output_root": "out/v3_sidecar",
        "outputs": [
            {
                "logical_name": "verdict_record.json",
                "relative_path": "verdict_record.json",
                "sha256": "sha256:test",
            }
        ],
    }

    _write_json(release_packet_dir / "verdict_record.json", verdict_record)
    _write_json(release_packet_dir / "sidecar_run_record.json", sidecar_run_record)
    _write_json(release_packet_dir / "output_inventory.json", output_inventory)
    _write_json(release_packet_dir / "generator_manifest.json", generator_manifest)
    (release_packet_dir / "bridge_operator_summary.md").write_text(
        "# [exploratory] Bridge Operator Summary\n\n"
        "- semantic_policy_version: `crisp.v3.semantic_policy/rev3-sidecar-first`\n"
        "- comparator_scope: `path_only_partial`\n"
        "- verdict_match_rate: `N/A`\n"
        "- path_component_match_rate: `1/1 (100.0%)`\n\n"
        "Cap / Catalytic sidecar materialization does not widen the current Path-only comparability claim.\n",
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
        {
            "required_window_size": 30,
            "observed_window_size": 30,
            "authority_phase_m2_streak": True,
            "dual_write_mismatch_zero_streak": True,
            "operator_surface_inactive_streak": True,
            "manifest_registration_complete_streak": True,
            "schema_complete_streak": True,
            "window_passed": True,
        },
    )
    _write_json(
        evidence_dir / "rc_gate_keep_path_report.json",
        {
            "gate_passed": True,
            "run_facts": {
                "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
                "comparator_scope": "path_only_partial",
                "comparable_channels": ["path"],
                "path_component_match_rate": 1.0,
                "coverage_drift_count": 0,
                "applicability_drift_count": 0,
                "metrics_drift_count": 0,
                "output_inventory_unchanged": True,
                "v3_shadow_verdict_inactive": True,
                "numeric_verdict_match_rate_absent": True,
                "operator_surface_exploratory": True,
                "operator_surface_verdict_match_rate_na": True,
            },
        },
    )
    _write_json(
        evidence_dir / "campaign_index.json",
        {
            "aggregate": {
                "campaign_passed": True,
                "comparator_scope_path_only_partial_all_runs": True,
                "comparable_channels_path_only_all_runs": True,
                "v3_shadow_verdict_inactive_all_runs": True,
                "numeric_verdict_match_rate_absent_all_runs": True,
                "coverage_drift_zero_all_runs": True,
                "applicability_drift_zero_all_runs": True,
                "metrics_drift_zero_all_runs": True,
                "operator_surface_exploratory_all_runs": True,
                "metric_contract_note": metric_contract_note,
            }
        },
    )
    _write_json(
        evidence_dir / "release_packet_smoke_report.json",
        {
            "smoke_passed": True,
            "hash_mismatches": [],
            "tracked_hashes": {
                "release_packet/generator_manifest.json": "sha256:test-digest",
            },
        },
    )
    _write_json(
        evidence_dir / "keep_path_rc_history_report.json",
        {
            "history_passed": True,
            "aggregate": {
                "observed_run_count": 3,
                "all_gate_passed": True,
                "all_campaign_passed": True,
                "all_smoke_passed": True,
                "required_matrix_untouched_all_runs": True,
                "required_promotion_authorized_any_run": False,
                "public_scope_widening_authorized_any_run": False,
                "exploratory_label_maintained_all_runs": True,
                "output_inventory_unchanged_all_runs": True,
                "windows_hosted_success_all_runs": True,
                "coverage_drift_zero_all_runs": True,
                "applicability_drift_zero_all_runs": True,
                "metrics_drift_zero_all_runs": True,
                "metric_contract_note": metric_contract_note,
            },
        },
    )
    return docs_root, evidence_dir


def test_keep_path_rc_hostile_audit_accepts_valid_bundle_and_writes_reports(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    docs_root, evidence_dir = _build_hostile_audit_bundle(repo_root)

    payload = evaluate_keep_path_rc_hostile_audit(
        docs_root=docs_root,
        evidence_dir=evidence_dir,
        repo_root=repo_root,
    )

    assert payload["audit_passed"] is True
    assert payload["audit_checks"] == {
        "authorization_boundary_ok": True,
        "keep_scope_unchanged": True,
        "operator_surface_inactive": True,
        "ci_promotion_not_implied": True,
        "path_metric_not_overclaimed": True,
    }

    report_path = write_keep_path_rc_hostile_audit_report(
        output_dir=evidence_dir,
        payload=payload,
    )
    summary_path = write_keep_path_rc_hostile_audit_summary(
        output_dir=evidence_dir,
        payload=payload,
    )
    assert report_path.name == KEEP_PATH_RC_HOSTILE_AUDIT_REPORT_ARTIFACT
    assert summary_path.name == KEEP_PATH_RC_HOSTILE_AUDIT_SUMMARY_ARTIFACT
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "path_component_match_rate remains a Path-only component metric" in summary_text


def test_keep_path_rc_hostile_audit_rejects_path_metric_overclaim(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    docs_root, evidence_dir = _build_hostile_audit_bundle(
        repo_root,
        metric_contract_note="path_component_match_rate is equivalent to final verdict quality",
    )

    payload = evaluate_keep_path_rc_hostile_audit(
        docs_root=docs_root,
        evidence_dir=evidence_dir,
        repo_root=repo_root,
    )

    assert payload["audit_passed"] is False
    assert payload["audit_checks"]["path_metric_not_overclaimed"] is False
    assert "KEEP_PATH_RC_AUDIT_PATH_METRIC_OVERCLAIMED" in payload["findings"]


def test_repo_keep_path_rc_hostile_audit_bundle_passes_on_fixed_evidence() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    payload = evaluate_keep_path_rc_hostile_audit(
        docs_root=repo_root / "docs",
        evidence_dir=repo_root / "docs" / "release" / "evidence" / "keep_path_rc" / "2026-04-09",
        repo_root=repo_root,
    )

    assert payload["audit_passed"] is True
