from __future__ import annotations

import json
from pathlib import Path

from crisp.repro.hashing import sha256_json
from crisp.v3.io.tableio import write_records_table
from crisp.v3.preconditions import audit_readiness_consistency
from crisp.v3.policy import parse_sidecar_options
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from tests.v3.helpers import make_config, write_pat_fixture


def _write_evidence_core(path: Path) -> Path:
    table = write_records_table(
        path,
        [
            {
                "run_id": "run",
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
                    "anchor_candidate_atoms": [0, 1, 2],
                    "struct_conn_status": "present",
                },
                "evidence_path": "ignored-a.json",
            },
            {
                "run_id": "run",
                "molecule_id": "m2",
                "target_id": "tgt",
                "candidate_order_hash": "sha256:b",
                "proposal_policy_version": "v29.trace-only.noop",
                "stage_history_json": [],
                "proposal_trace_json": {
                    "proposal_policy_version": "v29.trace-only.noop",
                    "semantic_mode": "trace-only-noop",
                    "candidate_order_hash": "sha256:b",
                    "near_band_triggered": False,
                    "anchor_candidate_atoms": [0, 1],
                    "struct_conn_status": "missing",
                },
                "evidence_path": "ignored-b.json",
            },
        ],
    )
    return Path(table.path)


def _write_core_compounds(path: Path) -> Path:
    table = write_records_table(
        path,
        [
            {
                "run_id": "run",
                "molecule_id": "m1",
                "target_id": "tgt",
                "core_verdict": "PASS",
                "core_reason_code": None,
                "best_target_distance": 1.8,
                "best_offtarget_distance": 5.1,
                "final_stage": 1,
                "config_hash": "cfg",
                "legacy_core_final_verdict": "PASS",
            },
            {
                "run_id": "run",
                "molecule_id": "m2",
                "target_id": "tgt",
                "core_verdict": "PASS",
                "core_reason_code": None,
                "best_target_distance": 2.0,
                "best_offtarget_distance": 4.9,
                "final_stage": 1,
                "config_hash": "cfg",
                "legacy_core_final_verdict": "PASS",
            },
        ],
    )
    return Path(table.path)


def test_catalytic_sidecar_materializes_bundle_manifest_and_provenance(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    _write_evidence_core(run_dir / "evidence_core.parquet")
    _write_core_compounds(run_dir / "core_compounds.parquet")
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
        rc2_generated_outputs=["run_manifest.json", "output_inventory.json", "evidence_core.parquet", "core_compounds.parquet"],
        core_compounds_path=run_dir / "core_compounds.parquet",
    )
    options = parse_sidecar_options(
        {"v3_sidecar": {"enabled": True, "channels": {"catalytic": {"enabled": True}}}}
    )

    result = run_sidecar(snapshot=snapshot, options=options)

    assert result is not None
    assert result.rc2_outputs_unchanged is True
    assert "channel_evidence_catalytic.jsonl" in result.materialized_outputs
    assert "run_drift_report.json" not in result.materialized_outputs
    assert "preconditions_readiness.json" in result.materialized_outputs

    bundle = json.loads((run_dir / "v3_sidecar" / "observation_bundle.json").read_text(encoding="utf-8"))
    assert [item["channel_name"] for item in bundle["observations"]] == ["path", "catalytic"]
    catalytic_observation = next(item for item in bundle["observations"] if item["channel_name"] == "catalytic")
    assert catalytic_observation["bridge_metrics"]["truth_source_kind"] == "read_only_evidence_core_snapshot"
    assert catalytic_observation["payload"]["constraint_set"]["state"] == "SATISFIED"
    assert catalytic_observation["payload"]["quantitative_metrics"]["best_target_distance"] == 1.8

    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    assert builder_provenance["channels"]["catalytic"]["truth_source_chain"][0]["kind"] == "evidence_core_snapshot"
    assert builder_provenance["channels"]["catalytic"]["truth_source_chain"][0]["source_label"] in {"evidence_core.parquet", "evidence_core.jsonl"}
    assert builder_provenance["channels"]["catalytic"]["channel_evidence_artifact"] == "channel_evidence_catalytic.jsonl"

    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    assert run_record["channel_records"]["catalytic"]["enabled"] is True
    assert run_record["channel_records"]["catalytic"]["channel_state"] == "SATISFIED"
    assert run_record["channel_records"]["catalytic"]["truth_source_kind"] == "read_only_evidence_core_snapshot"
    assert run_record["bridge_diagnostics"]["catalytic_channel_enabled"] is True
    assert run_record["bridge_diagnostics"]["preconditions_readiness_artifact"] == "preconditions_readiness.json"
    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    assert readiness["comparator_scope"] == "path_and_catalytic_partial"
    assert readiness["comparable_channels"] == ["path", "catalytic"]
    assert readiness["full_migration_ready"] is False
    assert readiness["channel_states"]["path"] == "observation_materialized"
    assert readiness["channel_states"]["catalytic"] == "observation_materialized"
    assert readiness["truth_source_audits"]["path"]["status"] == "pass"
    assert readiness["truth_source_audits"]["catalytic"]["status"] == "pass"

    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))
    assert {item["relative_path"] for item in manifest["outputs"]} >= {
        "semantic_policy_version.json",
        "preconditions_readiness.json",
        "sidecar_run_record.json",
        "observation_bundle.json",
        "channel_evidence_path.jsonl",
        "channel_evidence_catalytic.jsonl",
        "builder_provenance.json",
    }
    assert manifest["expected_output_digest"] == sha256_json({"outputs": manifest["outputs"]})
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

    inventory = json.loads((run_dir / "output_inventory.json").read_text(encoding="utf-8"))
    assert all(not name.startswith("v3_sidecar/") for name in inventory["generated_outputs"])


def test_catalytic_sidecar_materialization_is_stable_across_repeat_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    _write_evidence_core(run_dir / "evidence_core.parquet")
    _write_core_compounds(run_dir / "core_compounds.parquet")
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
        rc2_generated_outputs=["run_manifest.json", "output_inventory.json", "evidence_core.parquet", "core_compounds.parquet"],
        core_compounds_path=run_dir / "core_compounds.parquet",
    )
    options = parse_sidecar_options(
        {"v3_sidecar": {"enabled": True, "channels": {"catalytic": {"enabled": True}}}}
    )

    first = run_sidecar(snapshot=snapshot, options=options)
    first_manifest = (run_dir / "v3_sidecar" / "generator_manifest.json").read_bytes()
    first_bundle = (run_dir / "v3_sidecar" / "observation_bundle.json").read_bytes()
    first_catalytic = (run_dir / "v3_sidecar" / "channel_evidence_catalytic.jsonl").read_bytes()
    first_provenance = (run_dir / "v3_sidecar" / "builder_provenance.json").read_bytes()
    first_readiness = (run_dir / "v3_sidecar" / "preconditions_readiness.json").read_bytes()
    first_run_record = (run_dir / "v3_sidecar" / "sidecar_run_record.json").read_bytes()

    second = run_sidecar(snapshot=snapshot, options=options)
    second_manifest = (run_dir / "v3_sidecar" / "generator_manifest.json").read_bytes()
    second_bundle = (run_dir / "v3_sidecar" / "observation_bundle.json").read_bytes()
    second_catalytic = (run_dir / "v3_sidecar" / "channel_evidence_catalytic.jsonl").read_bytes()
    second_provenance = (run_dir / "v3_sidecar" / "builder_provenance.json").read_bytes()
    second_readiness = (run_dir / "v3_sidecar" / "preconditions_readiness.json").read_bytes()
    second_run_record = (run_dir / "v3_sidecar" / "sidecar_run_record.json").read_bytes()

    assert first is not None
    assert second is not None
    assert first.expected_output_digest == second.expected_output_digest
    assert first.materialized_outputs == second.materialized_outputs
    assert first_manifest == second_manifest
    assert first_bundle == second_bundle
    assert first_catalytic == second_catalytic
    assert first_provenance == second_provenance
    assert first_readiness == second_readiness
    assert first_run_record == second_run_record
