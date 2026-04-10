from __future__ import annotations

import json

import pytest

from crisp.repro.hashing import sha256_json
from crisp.v3.policy import parse_sidecar_options
from crisp.v3.report_guards import (
    ReportGuardError,
    enforce_shadow_stability_campaign_guard,
    enforce_verdict_record_dual_write_guard,
)
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from crisp.v3.shadow_stability import build_shadow_stability_campaign
from tests.v3.helpers import make_config, write_pat_fixture


def _build_snapshot(tmp_path, *, run_id: str = "run-1"):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
    core_compounds_path = tmp_path / "core_compounds.jsonl"
    core_compounds_path.write_text(
        "\n".join(
            [
                json.dumps({"molecule_id": "m1", "best_target_distance": 2.1, "best_offtarget_distance": 3.6}),
                json.dumps({"molecule_id": "m2", "best_target_distance": 2.4, "best_offtarget_distance": 3.9}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    evidence_core_path = run_dir / "evidence_core.jsonl"
    evidence_core_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "run_id": run_id,
                        "molecule_id": "m1",
                        "target_id": "tgt",
                        "candidate_order_hash": "sha256:a",
                        "proposal_policy_version": "v29.trace-only.noop",
                        "stage_history_json": [{"stage_id": 1}],
                        "proposal_trace_json": {
                            "proposal_policy_version": "v29.trace-only.noop",
                            "semantic_mode": "trace-only-noop",
                            "candidate_order_hash": "sha256:a",
                            "near_band_triggered": True,
                            "anchor_candidate_atoms": [0, 1],
                            "struct_conn_status": "present",
                        },
                        "evidence_path": "ignored-a.json",
                    }
                ),
                json.dumps(
                    {
                        "run_id": run_id,
                        "molecule_id": "m2",
                        "target_id": "tgt",
                        "candidate_order_hash": "sha256:b",
                        "proposal_policy_version": "v29.trace-only.noop",
                        "stage_history_json": [{"stage_id": 1}],
                        "proposal_trace_json": {
                            "proposal_policy_version": "v29.trace-only.noop",
                            "semantic_mode": "trace-only-noop",
                            "candidate_order_hash": "sha256:b",
                            "near_band_triggered": True,
                            "anchor_candidate_atoms": [0, 1, 2],
                            "struct_conn_status": "present",
                        },
                        "evidence_path": "ignored-b.json",
                        "best_target_distance": 2.1,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return build_sidecar_snapshot(
        run_id=run_id,
        run_mode="core+rule1",
        repo_root=str(tmp_path),
        out_dir=run_dir,
        config_path=tmp_path / "cfg.yaml",
        integrated_config_path=tmp_path / "integrated.yaml",
        resource_profile="smoke",
        comparison_type="cross-regime",
        pathyes_mode_requested="pat-backed",
        pathyes_force_false_requested=False,
        pat_diagnostics_path=pat_path,
        config=make_config(),
        rc2_generated_outputs=["run_manifest.json", "output_inventory.json"],
        core_compounds_path=core_compounds_path,
    )


def test_shadow_stability_campaign_requires_30_green_runs() -> None:
    campaign = build_shadow_stability_campaign(
        run_id="run-1",
        sidecar_invariant_history=[True] * 30,
        metrics_drift_history=[0] * 30,
        windows_streak_history=[True] * 30,
        run_drift_report_digest_history=["abc"] * 30,
    )

    enforce_shadow_stability_campaign_guard(payload={
        "required_window_size": campaign.required_window_size,
        "campaign_passed": campaign.campaign_passed,
        "sidecar_invariant_green": campaign.sidecar_invariant_green,
        "metrics_drift_zero": campaign.metrics_drift_zero,
        "windows_streak_green": campaign.windows_streak_green,
        "digest_stable": campaign.digest_stable,
    })
    assert campaign.campaign_passed is True


def test_verdict_record_guard_blocks_dual_write_mismatch() -> None:
    with pytest.raises(ReportGuardError, match="verdict_record dual-write mismatch: comparable_channels"):
        enforce_verdict_record_dual_write_guard(
            verdict_record={
                "run_id": "run-1",
                "output_root": "x",
                "semantic_policy_version": "v3",
                "comparator_scope": "path_only_partial",
                "comparable_channels": ["path", "cap"],
                "v3_only_evidence_channels": [],
                "channel_lifecycle_states": {"path": "observation_materialized"},
                "full_verdict_computable": False,
                "full_verdict_comparable_count": 0,
                "verdict_mismatch_rate": None,
                "path_component_match_rate": 1.0,
                "authority_transfer_complete": False,
                "v3_shadow_verdict": None,
                "verdict_match_rate": None,
            },
            sidecar_run_record={
                "run_id": "run-1",
                "output_root": "x",
                "semantic_policy_version": "v3",
                "comparator_scope": "path_only_partial",
                "comparable_channels": ["path"],
                "v3_only_evidence_channels": [],
                "channel_lifecycle_states": {"path": "observation_materialized"},
                "bridge_diagnostics": {
                    "bridge_comparison_summary": {
                        "run_drift_report": {
                            "full_verdict_computable": False,
                            "full_verdict_comparable_count": 0,
                            "verdict_match_rate": None,
                            "verdict_mismatch_rate": None,
                            "path_component_match_rate": 1.0,
                        }
                    }
                },
            },
        )


def test_verdict_record_guard_requires_m2_sidecar_role_markers_after_cutover() -> None:
    with pytest.raises(
        ReportGuardError,
        match="sidecar_run_record must reference verdict_record.json as canonical Layer 0 authority",
    ):
        enforce_verdict_record_dual_write_guard(
            verdict_record={
                "run_id": "run-1",
                "output_root": "x",
                "semantic_policy_version": "v3",
                "comparator_scope": "path_only_partial",
                "comparable_channels": ["path"],
                "v3_only_evidence_channels": [],
                "channel_lifecycle_states": {"path": "observation_materialized"},
                "full_verdict_computable": False,
                "full_verdict_comparable_count": 0,
                "verdict_mismatch_rate": None,
                "path_component_match_rate": 1.0,
                "authority_transfer_complete": True,
                "v3_shadow_verdict": None,
                "verdict_match_rate": None,
            },
            sidecar_run_record={
                "bridge_diagnostics": {
                    "layer0_authority_mirror": {
                        "run_id": "run-1",
                        "output_root": "x",
                        "semantic_policy_version": "v3",
                        "comparator_scope": "path_only_partial",
                        "comparable_channels": ["path"],
                        "v3_only_evidence_channels": [],
                        "channel_lifecycle_states": {"path": "observation_materialized"},
                        "full_verdict_computable": False,
                        "full_verdict_comparable_count": 0,
                        "verdict_match_rate": None,
                        "verdict_mismatch_rate": None,
                        "path_component_match_rate": 1.0,
                        "v3_shadow_verdict": None,
                        "authority_transfer_complete": True,
                    }
                }
            },
        )


def test_internal_full_scv_bundle_is_deterministic_and_internal_only(tmp_path) -> None:
    snapshot = _build_snapshot(tmp_path)

    result_one = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options(
            {
                "v3_sidecar": {
                    "enabled": True,
                    "artifact_policy": "full",
                    "channels": {"catalytic": {"enabled": True}},
                }
            }
        ),
    )
    bundle_one = json.loads(
        (tmp_path / "run" / "v3_sidecar" / "internal_full_scv_observation_bundle.json").read_text(encoding="utf-8")
    )

    run_dir_two = tmp_path / "run-two"
    run_dir_two.mkdir()
    (run_dir_two / "run_manifest.json").write_text(json.dumps({"run_id": "run-1"}), encoding="utf-8")
    (run_dir_two / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    (run_dir_two / "evidence_core.jsonl").write_text((tmp_path / "run" / "evidence_core.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    snapshot_two = build_sidecar_snapshot(
        run_id="run-1",
        run_mode=snapshot.run_mode,
        repo_root=snapshot.repo_root,
        out_dir=run_dir_two,
        config_path=snapshot.config_path,
        integrated_config_path=snapshot.integrated_config_path,
        resource_profile=snapshot.resource_profile,
        comparison_type=snapshot.comparison_type,
        pathyes_mode_requested=snapshot.pathyes_mode_requested,
        pathyes_force_false_requested=snapshot.pathyes_force_false_requested,
        pat_diagnostics_path=snapshot.pat_diagnostics_path,
        config=snapshot.config,
        rc2_generated_outputs=snapshot.rc2_generated_outputs,
        core_compounds_path=snapshot.core_compounds_path,
    )
    result_two = run_sidecar(
        snapshot=snapshot_two,
        options=parse_sidecar_options(
            {
                "v3_sidecar": {
                    "enabled": True,
                    "artifact_policy": "full",
                    "channels": {"catalytic": {"enabled": True}},
                }
            }
        ),
    )
    bundle_two = json.loads(
        (run_dir_two / "v3_sidecar" / "internal_full_scv_observation_bundle.json").read_text(encoding="utf-8")
    )

    assert result_one is not None
    assert result_two is not None
    assert sha256_json(bundle_one) == sha256_json(bundle_two)
    assert bundle_one["bridge_diagnostics"]["operator_surface_active"] is False
    assert {
        observation["channel_name"]
        for observation in bundle_one["observations"]
    } == {"path", "scv_anchoring", "scv_offtarget"}
