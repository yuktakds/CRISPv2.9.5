from __future__ import annotations

import json
from pathlib import Path

from crisp.v29.cli import run_integrated_v29
from tests.v29.test_v3_sidecar_hook import _snapshot_rc2_files, _write_fixture_config
from tests.v29_smoke_helpers import make_stub_core_bridge, write_managed_theta_table, write_pat_diagnostics


def _run_bridge_shadow_mode(
    *,
    repo_root: Path,
    tmp_root: Path,
    config_path: Path,
    library_path: Path,
    stageplan_path: Path,
    pat_diagnostics_path: Path,
    theta_table_path: Path,
    out_dir: Path,
    monkeypatch,
    comparator_enabled: bool,
) -> dict[str, object]:
    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(library_path=library_path, target_id="tgt"),
    )
    integrated_path = tmp_root / f"{out_dir.parent.name}-{out_dir.name}.yaml"
    lines = [
        "pathyes_mode: pat-backed",
        f"pat_diagnostics_path: {pat_diagnostics_path}",
        f"theta_rule1_table: {theta_table_path}",
        "v3_sidecar:",
        "  enabled: true",
    ]
    if comparator_enabled:
        lines.extend(
            [
                "v3_bridge_comparator:",
                "  enabled: true",
            ]
        )
    integrated_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_integrated_v29(
        repo_root=repo_root,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        out_dir=out_dir,
        integrated_config_path=integrated_path,
        run_mode="core+rule1",
    )


def test_bridge_shadow_mode_emits_partial_comparison_artifacts_without_touching_rc2(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path, library_path, stageplan_path = _write_fixture_config(repo_root)
    pat_diagnostics_path = write_pat_diagnostics(
        repo_root / "pat.json",
        goal_precheck_passed=True,
        extra_diagnostics={
            "blockage_ratio": 0.8,
            "apo_accessible_goal_voxels": 4,
            "feasible_count": 5,
            "witness_pose_id": "pose-1",
            "obstruction_path_ids": ["path-1"],
        },
    )
    theta_table_path = write_managed_theta_table(repo_root / "theta.parquet", config_path=config_path)

    sidecar_only_dir = tmp_path / "sidecar-only" / "run"
    comparator_dir = tmp_path / "comparator" / "run"
    sidecar_only = _run_bridge_shadow_mode(
        repo_root=repo_root,
        tmp_root=tmp_path,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        pat_diagnostics_path=pat_diagnostics_path,
        theta_table_path=theta_table_path,
        out_dir=sidecar_only_dir,
        monkeypatch=monkeypatch,
        comparator_enabled=False,
    )
    comparator = _run_bridge_shadow_mode(
        repo_root=repo_root,
        tmp_root=tmp_path,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        pat_diagnostics_path=pat_diagnostics_path,
        theta_table_path=theta_table_path,
        out_dir=comparator_dir,
        monkeypatch=monkeypatch,
        comparator_enabled=True,
    )

    assert sidecar_only["run_mode_complete"] is True
    assert comparator["run_mode_complete"] is True
    assert _snapshot_rc2_files(sidecar_only_dir) == _snapshot_rc2_files(comparator_dir)
    assert (comparator_dir / "v3_sidecar" / "bridge_comparison_summary.json").exists()
    assert (comparator_dir / "v3_sidecar" / "bridge_drift_attribution.jsonl").exists()
    assert (comparator_dir / "v3_sidecar" / "bridge_operator_summary.md").exists()

    summary = json.loads((comparator_dir / "v3_sidecar" / "bridge_comparison_summary.json").read_text(encoding="utf-8"))
    inventory = json.loads((comparator_dir / "output_inventory.json").read_text(encoding="utf-8"))
    assert summary["comparison_scope"] == "path_only_partial"
    assert summary["verdict_comparability"] == "partially_comparable"
    assert all(not name.startswith("v3_sidecar/bridge_") for name in inventory["generated_outputs"])


def test_bridge_shadow_mode_outputs_are_deterministic_across_repeat_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path, library_path, stageplan_path = _write_fixture_config(repo_root)
    pat_diagnostics_path = write_pat_diagnostics(
        repo_root / "pat.json",
        goal_precheck_passed=True,
        extra_diagnostics={
            "blockage_ratio": 0.8,
            "apo_accessible_goal_voxels": 4,
            "feasible_count": 5,
            "witness_pose_id": "pose-1",
            "obstruction_path_ids": ["path-1"],
        },
    )
    theta_table_path = write_managed_theta_table(repo_root / "theta.parquet", config_path=config_path)

    first_dir = tmp_path / "first" / "run"
    second_dir = tmp_path / "second" / "run"
    _run_bridge_shadow_mode(
        repo_root=repo_root,
        tmp_root=tmp_path,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        pat_diagnostics_path=pat_diagnostics_path,
        theta_table_path=theta_table_path,
        out_dir=first_dir,
        monkeypatch=monkeypatch,
        comparator_enabled=True,
    )
    _run_bridge_shadow_mode(
        repo_root=repo_root,
        tmp_root=tmp_path,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        pat_diagnostics_path=pat_diagnostics_path,
        theta_table_path=theta_table_path,
        out_dir=second_dir,
        monkeypatch=monkeypatch,
        comparator_enabled=True,
    )

    for name in (
        "bridge_comparison_summary.json",
        "bridge_drift_attribution.jsonl",
        "bridge_operator_summary.md",
    ):
        assert (first_dir / "v3_sidecar" / name).read_bytes() == (second_dir / "v3_sidecar" / name).read_bytes()

