from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.policy import parse_sidecar_options
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from tests.v3.helpers import make_config, write_pat_fixture


def test_generator_manifest_is_stable_across_repeat_sidecar_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_blockage_supported.json")

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
    options = parse_sidecar_options({"v3_sidecar": {"enabled": True}})

    first = run_sidecar(snapshot=snapshot, options=options)
    manifest_path = run_dir / "v3_sidecar" / "generator_manifest.json"
    first_manifest = manifest_path.read_bytes()
    first_expected_digest = None if first is None else first.expected_output_digest

    second = run_sidecar(snapshot=snapshot, options=options)
    second_manifest = manifest_path.read_bytes()
    second_expected_digest = None if second is None else second.expected_output_digest

    assert first is not None
    assert second is not None
    assert first_manifest == second_manifest
    assert first_expected_digest == second_expected_digest
    assert first.materialized_outputs == second.materialized_outputs

