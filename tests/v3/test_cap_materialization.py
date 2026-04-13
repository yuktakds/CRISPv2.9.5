from __future__ import annotations

import json
from pathlib import Path

from crisp.repro.hashing import sha256_json
from crisp.v3.preconditions import audit_readiness_consistency
from crisp.v3.io.tableio import write_records_table
from crisp.v3.policy import parse_sidecar_options
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from tests.v3.helpers import make_config, write_pat_fixture


def _write_cap_pair_features(path: Path) -> Path:
    table = write_records_table(
        path,
        [
            {"canonical_link_id": "a", "molecule_id": "n1", "cap_id": "c1", "pairing_role": "native", "comb": 0.82, "PAS": 0.75},
            {"canonical_link_id": "a", "molecule_id": "n2", "cap_id": "c2", "pairing_role": "native", "comb": 0.80, "PAS": 0.72},
            {"canonical_link_id": "a", "molecule_id": "n3", "cap_id": "c3", "pairing_role": "native", "comb": 0.78, "PAS": 0.70},
            {"canonical_link_id": "a", "molecule_id": "f1", "cap_id": "c4", "pairing_role": "matched_falsification", "comb": 0.22, "PAS": 0.18},
            {"canonical_link_id": "a", "molecule_id": "f2", "cap_id": "c5", "pairing_role": "matched_falsification", "comb": 0.20, "PAS": 0.15},
        ],
    )
    return Path(table.path)


def test_cap_sidecar_materializes_bundle_and_manifest_entries(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_blockage_supported.json")
    pair_features_path = _write_cap_pair_features(tmp_path / "pair_features.parquet")

    snapshot = build_sidecar_snapshot(
        run_id="run",
        run_mode="core+rule1+cap",
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
        cap_pair_features_path=pair_features_path,
    )

    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options(
            {"v3_sidecar": {"enabled": True, "channels": {"cap": {"enabled": True}}}}
        ),
    )

    assert result is not None
    assert "channel_evidence_cap.jsonl" in result.materialized_outputs
    assert "run_drift_report.json" not in result.materialized_outputs
    assert "preconditions_readiness.json" in result.materialized_outputs
    bundle = json.loads((run_dir / "v3_sidecar" / "observation_bundle.json").read_text(encoding="utf-8"))
    channel_names = [item["channel_name"] for item in bundle["observations"]]
    assert channel_names == ["path", "cap"]
    cap_observation = next(item for item in bundle["observations"] if item["channel_name"] == "cap")
    assert cap_observation["bridge_metrics"]["truth_source_kind"] == "read_only_pair_features_snapshot"
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    assert builder_provenance["channels"]["cap"]["truth_source_chain"][0]["kind"] == "pair_features_snapshot"
    assert builder_provenance["channels"]["cap"]["truth_source_chain"][0]["source_label"] in {"pair_features.parquet", "pair_features.jsonl"}
    assert builder_provenance["channels"]["cap"]["channel_evidence_artifact"] == "channel_evidence_cap.jsonl"
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    assert run_record["channel_records"]["cap"]["channel_state"] == "VALIDATED"
    assert run_record["channel_records"]["cap"]["truth_source_kind"] == "read_only_pair_features_snapshot"
    assert run_record["bridge_diagnostics"]["builder_provenance_artifact"] == "builder_provenance.json"
    assert run_record["bridge_diagnostics"]["preconditions_readiness_artifact"] == "preconditions_readiness.json"
    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    assert readiness["comparator_scope"] == "path_and_catalytic_partial"
    assert readiness["comparable_channels"] == ["path", "catalytic"]
    assert readiness["full_migration_ready"] is False
    assert readiness["channel_states"]["path"] == "observation_materialized"
    assert readiness["channel_states"]["cap"] == "observation_materialized"
    assert readiness["truth_source_audits"]["path"]["status"] == "pass"
    assert readiness["truth_source_audits"]["cap"]["status"] == "pass"

    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))
    assert {item["relative_path"] for item in manifest["outputs"]} >= {
        "semantic_policy_version.json",
        "preconditions_readiness.json",
        "sidecar_run_record.json",
        "observation_bundle.json",
        "channel_evidence_path.jsonl",
        "channel_evidence_cap.jsonl",
        "builder_provenance.json",
    }
    assert manifest["expected_output_digest"] == sha256_json({"outputs": manifest["outputs"]})
    cap_descriptor = next(item for item in manifest["outputs"] if item["relative_path"] == "channel_evidence_cap.jsonl")
    assert cap_descriptor["content_type"] == "application/jsonl"
    assert cap_descriptor["sha256"].startswith("sha256:")
    assert audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
        operator_summary=(
            (run_dir / "v3_sidecar" / "bridge_operator_summary.md").read_text(encoding="utf-8")
            if (run_dir / "v3_sidecar" / "bridge_operator_summary.md").exists()
            else None
        ),
    ) == ()


def test_cap_sidecar_materialization_is_stable_across_repeat_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_blockage_supported.json")
    pair_features_path = _write_cap_pair_features(tmp_path / "pair_features.parquet")
    snapshot = build_sidecar_snapshot(
        run_id="run",
        run_mode="core+rule1+cap",
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
        cap_pair_features_path=pair_features_path,
    )
    options = parse_sidecar_options(
        {"v3_sidecar": {"enabled": True, "channels": {"cap": {"enabled": True}}}}
    )

    first = run_sidecar(snapshot=snapshot, options=options)
    first_manifest = (run_dir / "v3_sidecar" / "generator_manifest.json").read_bytes()
    first_bundle = (run_dir / "v3_sidecar" / "observation_bundle.json").read_bytes()
    first_cap = (run_dir / "v3_sidecar" / "channel_evidence_cap.jsonl").read_bytes()
    first_provenance = (run_dir / "v3_sidecar" / "builder_provenance.json").read_bytes()
    first_readiness = (run_dir / "v3_sidecar" / "preconditions_readiness.json").read_bytes()
    first_run_record = (run_dir / "v3_sidecar" / "sidecar_run_record.json").read_bytes()

    second = run_sidecar(snapshot=snapshot, options=options)
    second_manifest = (run_dir / "v3_sidecar" / "generator_manifest.json").read_bytes()
    second_bundle = (run_dir / "v3_sidecar" / "observation_bundle.json").read_bytes()
    second_cap = (run_dir / "v3_sidecar" / "channel_evidence_cap.jsonl").read_bytes()
    second_provenance = (run_dir / "v3_sidecar" / "builder_provenance.json").read_bytes()
    second_readiness = (run_dir / "v3_sidecar" / "preconditions_readiness.json").read_bytes()
    second_run_record = (run_dir / "v3_sidecar" / "sidecar_run_record.json").read_bytes()

    assert first is not None
    assert second is not None
    assert first.expected_output_digest == second.expected_output_digest
    assert first.materialized_outputs == second.materialized_outputs
    assert first_manifest == second_manifest
    assert first_bundle == second_bundle
    assert first_cap == second_cap
    assert first_provenance == second_provenance
    assert first_readiness == second_readiness
    assert first_run_record == second_run_record
