from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.policy import parse_sidecar_options
from crisp.v3.readiness.consistency import (
    build_inventory_authority_payload,
    reconstruct_truth_source_claims,
)
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from tests.v3.helpers import make_config, write_pat_fixture


def test_generator_manifest_remains_sidecar_inventory_authority(tmp_path: Path) -> None:
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

    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}),
    )

    assert result is not None
    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    assert readiness["inventory_authority"] == build_inventory_authority_payload(
        rc2_output_inventory_mutated=False,
    )
    assert run_record["bridge_diagnostics"]["sidecar_inventory_authority"] == "v3_sidecar/generator_manifest.json"
    assert run_record["bridge_diagnostics"]["rc2_inventory_authority"] == "output_inventory.json"
    assert {item["relative_path"] for item in manifest["outputs"]} == set(run_record["materialized_outputs"])
    assert "output_inventory.json" not in {item["relative_path"] for item in manifest["outputs"]}


def test_truth_source_reconstruction_detects_duplicate_manifest_relative_paths(tmp_path: Path) -> None:
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

    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}),
    )

    assert result is not None
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))
    duplicate = next(item for item in manifest["outputs"] if item["relative_path"] == "observation_bundle.json")
    manifest["outputs"].append(dict(duplicate))

    claims = reconstruct_truth_source_claims(
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )

    assert claims["path"]["manifest_duplicate_relative_paths"] == ["observation_bundle.json"]
    assert claims["path"]["observation_artifact_unique"] is False
    assert claims["path"]["reconstruction_complete"] is False
