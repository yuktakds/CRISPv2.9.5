from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from crisp.v29.cli import run_integrated_v29
from crisp.utils.jsonx import canonical_json_bytes
from tests.v29_smoke_helpers import make_stub_core_bridge, write_managed_theta_table, write_pat_diagnostics


def _write_fixture_config(repo_root: Path) -> tuple[Path, Path, Path]:
    (repo_root / "pyproject.toml").write_text('[project]\nname="crisp"\nversion="0.0.0"\n', encoding="utf-8")
    structure = repo_root / "s.cif"
    structure.write_text("data_dummy\n", encoding="utf-8")
    config_path = repo_root / "cfg.yaml"
    config_path.write_text(
        f"""target_name: tgt
config_role: benchmark
expected_use: Frozen regression baseline for parser, search, and reason-taxonomy changes.
allowed_comparisons: [same-config, cross-regime]
frozen_for_regression: true
pathway: covalent
pdb:
  path: {structure}
  model_id: 1
  altloc_policy: first
  include_hydrogens: false
residue_id_format: auth
target_cysteine: {{chain: A, residue_number: 1, insertion_code: '', atom_name: SG}}
anchor_atom_set:
  - {{chain: A, residue_number: 1, insertion_code: '', atom_name: SG}}
offtarget_cysteines:
  - {{chain: B, residue_number: 2, insertion_code: '', atom_name: SG}}
search_radius: 6.0
distance_threshold: 2.2
sampling: {{n_conformers: 1, n_rotations: 1, n_translations: 1, alpha: 0.5}}
anchoring: {{bond_threshold: 2.2, near_threshold: 3.5, epsilon: 0.1}}
offtarget: {{distance_threshold: 2.2, epsilon: 0.1}}
scv: {{confident_fail_threshold: 1, zero_feasible_abort: 4096}}
staging: {{retry_distance_lower: 2.2, retry_distance_upper: 3.5, far_target_threshold: 6.0, max_stage: 2}}
translation: {{local_fraction: 0.5, local_min_radius: 1.0, local_max_radius: 2.0, local_start_stage: 2}}
pat: {{path_model: TUNNEL, goal_mode: shell, grid_spacing: 0.5, probe_radius: 1.4, r_outer_margin: 2.0, blockage_pass_threshold: 0.5, top_k_poses: 4, goal_shell_clearance: 0.2, goal_shell_thickness: 1.0, surface_window_radius: 4.0}}
random_seed: 42
""",
        encoding="utf-8",
    )
    library_path = repo_root / "molecules.smi"
    library_path.write_text("CCO m1\n", encoding="utf-8")
    stageplan_path = repo_root / "stageplan.json"
    stageplan_path.write_text("{}", encoding="utf-8")
    return config_path, library_path, stageplan_path


def _snapshot_rc2_files(out_dir: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    raw_run_dir = str(out_dir)
    escaped_run_dir = raw_run_dir.replace("\\", "\\\\")
    posix_run_dir = out_dir.as_posix()
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file() or "v3_sidecar" in path.parts:
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            snapshot[path.relative_to(out_dir).as_posix()] = raw
            continue
        if path.suffix == ".json":
            payload = json.loads(text)
            normalized_payload = _normalize_json_value(
                payload,
                raw_run_dir=raw_run_dir,
                escaped_run_dir=escaped_run_dir,
                posix_run_dir=posix_run_dir,
            )
            snapshot[path.relative_to(out_dir).as_posix()] = canonical_json_bytes(normalized_payload)
            continue
        if path.suffix == ".jsonl":
            rows = [
                _normalize_json_value(
                    json.loads(line),
                    raw_run_dir=raw_run_dir,
                    escaped_run_dir=escaped_run_dir,
                    posix_run_dir=posix_run_dir,
                )
                for line in text.splitlines()
                if line.strip()
            ]
            snapshot[path.relative_to(out_dir).as_posix()] = b"".join(
                canonical_json_bytes(row) + b"\n" for row in rows
            )
            continue
        normalized = (
            text.replace(escaped_run_dir, "<RUN_DIR>")
            .replace(raw_run_dir, "<RUN_DIR>")
            .replace(posix_run_dir, "<RUN_DIR>")
        )
        snapshot[path.relative_to(out_dir).as_posix()] = normalized.encode("utf-8")
    return snapshot


def _normalize_json_value(
    value: object,
    *,
    raw_run_dir: str,
    escaped_run_dir: str,
    posix_run_dir: str,
) -> object:
    if isinstance(value, str):
        normalized = (
            value.replace(escaped_run_dir, "<RUN_DIR>")
            .replace(raw_run_dir, "<RUN_DIR>")
            .replace(posix_run_dir, "<RUN_DIR>")
        )
        try:
            datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            return normalized
        return "<ISO8601>"
    if isinstance(value, list):
        return [
            _normalize_json_value(
                item,
                raw_run_dir=raw_run_dir,
                escaped_run_dir=escaped_run_dir,
                posix_run_dir=posix_run_dir,
            )
            for item in value
        ]
    if isinstance(value, dict):
        return {
            key: _normalize_json_value(
                item,
                raw_run_dir=raw_run_dir,
                escaped_run_dir=escaped_run_dir,
                posix_run_dir=posix_run_dir,
            )
            for key, item in value.items()
        }
    return value


def test_v3_sidecar_hook_is_default_off_and_non_interfering(tmp_path: Path, monkeypatch) -> None:
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
    theta_table_path = write_managed_theta_table(
        repo_root / "theta_rule1.parquet",
        config_path=config_path,
    )

    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(library_path=library_path, target_id="tgt"),
    )

    integrated_off = repo_root / "integrated-off.yaml"
    integrated_off.write_text(
        "\n".join(
            [
                "pathyes_mode: pat-backed",
                f"pat_diagnostics_path: {pat_diagnostics_path}",
                f"theta_rule1_table: {theta_table_path}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    integrated_on = repo_root / "integrated-on.yaml"
    integrated_on.write_text(
        "\n".join(
            [
                "pathyes_mode: pat-backed",
                f"pat_diagnostics_path: {pat_diagnostics_path}",
                f"theta_rule1_table: {theta_table_path}",
                "v3_sidecar:",
                "  enabled: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    off_dir = tmp_path / "shadow-off" / "run"
    on_dir = tmp_path / "shadow-on" / "run"
    off_result = run_integrated_v29(
        repo_root=repo_root,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        out_dir=off_dir,
        integrated_config_path=integrated_off,
        run_mode="core+rule1",
    )
    on_result = run_integrated_v29(
        repo_root=repo_root,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        out_dir=on_dir,
        integrated_config_path=integrated_on,
        run_mode="core+rule1",
    )

    assert off_result["run_mode_complete"] is True
    assert on_result["run_mode_complete"] is True
    assert _snapshot_rc2_files(off_dir) == _snapshot_rc2_files(on_dir)
    assert not (off_dir / "v3_sidecar").exists()
    assert (on_dir / "v3_sidecar" / "generator_manifest.json").exists()

    on_inventory = json.loads((on_dir / "output_inventory.json").read_text(encoding="utf-8"))
    assert all(not name.startswith("v3_sidecar/") for name in on_inventory["generated_outputs"])
