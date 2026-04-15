from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.contracts import BridgeComparatorOptions
from crisp.v3.policy import parse_sidecar_options
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from tests.v3.helpers import make_config, write_pat_payload


def test_sidecar_runner_preserves_existing_rc2_outputs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(json.dumps({"generated_outputs": ["run_manifest.json"]}), encoding="utf-8")
    pat_path = write_pat_payload(
        tmp_path / "pat.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.8,
                "apo_accessible_goal_voxels": 4,
            },
        },
    )
    rc2_before = (run_dir / "run_manifest.json").read_text(encoding="utf-8")

    snapshot = build_sidecar_snapshot(
        run_id="run",
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
    )

    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}),
    )

    assert result is not None
    assert result.rc2_outputs_unchanged is True
    assert (run_dir / "v3_sidecar" / "semantic_policy_version.json").exists()
    assert (run_dir / "v3_sidecar" / "sidecar_run_record.json").exists()
    assert (run_dir / "v3_sidecar" / "preconditions_readiness.json").exists()
    assert (run_dir / "v3_sidecar" / "generator_manifest.json").exists()
    assert (run_dir / "v3_sidecar" / "observation_bundle.json").exists()
    assert (run_dir / "v3_sidecar" / "channel_evidence_path.jsonl").exists()
    assert (run_dir / "run_manifest.json").read_text(encoding="utf-8") == rc2_before


def test_sidecar_runner_preserves_rc2_outputs_with_path_bridge_comparator_enabled(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(json.dumps({"generated_outputs": ["run_manifest.json"]}), encoding="utf-8")
    pat_path = write_pat_payload(
        tmp_path / "pat.json",
        {
            "supported_path_model": True,
            "goal_precheck_passed": True,
            "pat_run_diagnostics_json": {
                "blockage_ratio": 0.8,
                "apo_accessible_goal_voxels": 4,
                "witness_pose_id": "pose-1",
                "obstruction_path_ids": ["path-1"],
            },
        },
    )
    rc2_before = (run_dir / "run_manifest.json").read_text(encoding="utf-8")

    snapshot = build_sidecar_snapshot(
        run_id="run",
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
    )

    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}),
        comparator_options=BridgeComparatorOptions(enabled=True),
    )

    assert result is not None
    assert result.rc2_outputs_unchanged is True
    assert (run_dir / "v3_sidecar" / "bridge_comparison_summary.json").exists()
    assert (run_dir / "v3_sidecar" / "bridge_drift_attribution.jsonl").exists()
    assert (run_dir / "v3_sidecar" / "bridge_operator_summary.md").exists()
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    operator_summary = (run_dir / "v3_sidecar" / "bridge_operator_summary.md").read_text(encoding="utf-8")
    assert "[exploratory] Bridge Operator Summary" in operator_summary
    assert "semantic_policy_version" in operator_summary
    assert "verdict_match_rate: `N/A`" in operator_summary
    assert "path_component_match_rate: `1/1 (100.0%)`" in operator_summary
    assert "comparable_subset_size: `1`" in operator_summary
    assert "rc2 display role: `primary`" in operator_summary
    assert "v3 display role: `[exploratory] secondary`" in operator_summary
    assert run_record["comparator_scope"] == "path_and_catalytic_partial"
    assert run_record["comparable_channels"] == ["path", "catalytic"]
    assert run_record["channel_evidence_states"]["path"] == "SUPPORTED"
    assert run_record["channel_comparability"]["path"] == "component_verdict_comparable"
    assert run_record["path_component_match"] is True
    assert run_record["bridge_diagnostics"]["canonical_layer0_authority_artifact"] == "verdict_record.json"
    assert run_record["bridge_diagnostics"]["sidecar_run_record_role"] == "backward_compatible_mirror"
    assert run_record["bridge_diagnostics"]["layer0_authority_mirror"]["v3_shadow_verdict"] is None
    assert run_record["bridge_diagnostics"]["layer0_authority_mirror"]["verdict_match_rate"] is None
    assert readiness["gates"]["P6"]["status"] == "pass"
    assert (run_dir / "run_manifest.json").read_text(encoding="utf-8") == rc2_before
