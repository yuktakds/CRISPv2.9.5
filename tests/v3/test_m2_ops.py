from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.contracts import BridgeComparatorOptions
from crisp.v3.m2_ops import (
    execute_m2_rehearsal,
    execute_m2_rollback_drill,
    evaluate_post_cutover_monitoring_window,
)
from crisp.v3.policy import parse_sidecar_options
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from tests.v3.helpers import make_config, write_pat_fixture


def _materialize_run(tmp_path: Path, *, dirname: str, run_id: str = "run-1") -> Path:
    run_dir = tmp_path / dirname
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(run_dir / "pat.json", "pat_numeric_resolution_limited.json")
    snapshot = build_sidecar_snapshot(
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
    )
    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}),
        comparator_options=BridgeComparatorOptions(enabled=True),
    )
    assert result is not None
    return run_dir


def test_execute_m2_rollback_drill_detects_fault_and_preserves_hashes(tmp_path: Path) -> None:
    run_dir = _materialize_run(tmp_path, dirname="run")

    report = execute_m2_rollback_drill(run_dir)

    assert report["dual_write_mismatch_count"] == 0
    assert report["operator_surface_inactive"] is True
    assert report["injected_fault_detected"] is True
    assert report["output_inventory_unchanged"] is True
    assert report["hashes_unchanged"] is True
    assert report["rollback_projection"]["canonical_layer0_authority_artifact"] == "sidecar_run_record.json"
    assert report["drill_passed"] is True


def test_execute_m2_rehearsal_confirms_round_trip_integrity(tmp_path: Path) -> None:
    primary_run_dir = _materialize_run(tmp_path, dirname="run-a")
    rerun_run_dir = _materialize_run(tmp_path, dirname="run-b")

    report = execute_m2_rehearsal(primary_run_dir, rerun_run_dir)

    assert report["primary_validator_errors"] == []
    assert report["rerun_validator_errors"] == []
    assert report["round_trip_mismatches"] == []
    assert report["round_trip_integrity"] is True
    assert report["rehearsal_passed"] is True


def test_post_cutover_monitoring_window_requires_m2_alignment() -> None:
    readiness_payload = {
        "authority_phase": "M2",
        "dual_write_mismatch_count": 0,
        "current_run_operator_surface_inactive": True,
        "manifest_registration_complete": True,
        "schema_complete": True,
    }
    report = evaluate_post_cutover_monitoring_window(
        [dict(readiness_payload) for _ in range(30)]
    )

    assert report["authority_phase_m2_streak"] is True
    assert report["dual_write_mismatch_zero_streak"] is True
    assert report["operator_surface_inactive_streak"] is True
    assert report["window_passed"] is True


def test_post_cutover_monitoring_window_fails_on_operator_activation() -> None:
    history = [
        {
            "authority_phase": "M2",
            "dual_write_mismatch_count": 0,
            "current_run_operator_surface_inactive": True,
            "manifest_registration_complete": True,
            "schema_complete": True,
        }
        for _ in range(29)
    ]
    history.append(
        {
            "authority_phase": "M2",
            "dual_write_mismatch_count": 0,
            "current_run_operator_surface_inactive": False,
            "manifest_registration_complete": True,
            "schema_complete": True,
        }
    )

    report = evaluate_post_cutover_monitoring_window(history)

    assert report["operator_surface_inactive_streak"] is False
    assert report["window_passed"] is False
