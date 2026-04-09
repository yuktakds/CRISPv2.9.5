from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.contracts import BridgeComparatorOptions
from crisp.v3.preconditions import audit_readiness_consistency
from crisp.v3.policy import SEMANTIC_POLICY_VERSION, parse_sidecar_options
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from tests.v3.helpers import make_config, write_pat_fixture


def test_readiness_consistency_tracks_guarded_operator_artifacts_when_comparator_enabled(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
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
    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))
    operator_summary = (run_dir / "v3_sidecar" / "bridge_operator_summary.md").read_text(encoding="utf-8")

    assert readiness["gate_evidence"]["P4"]["guarded_operator_report_refs"] == [
        {
            "artifact_name": "bridge_operator_summary.md",
            "generator_id": "v3.bridge_operator_summary/v1",
            "section_id": "guarded_render_path",
        }
    ]
    assert audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
        operator_summary=operator_summary,
    ) == ()
    assert "[exploratory] Bridge Operator Summary" in operator_summary
    assert SEMANTIC_POLICY_VERSION in operator_summary


def test_readiness_consistency_fails_on_builder_provenance_digest_mismatch(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    builder_provenance["channels"]["path"]["truth_source_chain"][0]["source_digest"] = "sha256:tampered"
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P2 path source_digest does not reconstruct from builder_provenance" in findings


def test_readiness_consistency_fails_on_gate_schema_field_omission(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    readiness["gate_evidence"]["P2"].pop("schema_version", None)
    readiness["gate_evidence"]["P2"]["builder_provenance_ref"].pop("generator_id", None)
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P2 gate_evidence schema_version mismatch" in findings
    assert "P2 builder_provenance_ref generator_id is missing" in findings


def test_readiness_consistency_fails_on_artifact_ref_generator_and_section_mismatch(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
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
    run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}),
        comparator_options=BridgeComparatorOptions(enabled=True),
    )

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    readiness["gate_evidence"]["P4"]["guarded_operator_report_refs"][0]["generator_id"] = "v3.wrong/v1"
    readiness["gate_evidence"]["P4"]["guarded_operator_report_refs"][0]["section_id"] = "wrong_section"
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P4 guarded_operator_report_ref generator_id mismatch" in findings
    assert "P4 guarded_operator_report_ref section_id mismatch" in findings


def test_readiness_consistency_fails_on_missing_manifest_entry(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    manifest["outputs"] = [
        item for item in manifest["outputs"] if item["relative_path"] != "builder_provenance.json"
    ]
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P7 generator_manifest missing required entry: builder_provenance.json" in findings


def test_readiness_consistency_fails_on_expected_output_digest_mismatch(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    manifest["expected_output_digest"] = "sha256:tampered"
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P7 generator_manifest expected_output_digest does not match manifest outputs" in findings


def test_readiness_consistency_fails_on_run_record_builder_status_spoof(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    run_record["channel_records"]["path"]["builder_status"] = "applicability_only"
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P2 path run_record builder_status mismatch" in findings


def test_readiness_consistency_fails_on_cross_artifact_channel_state_contradiction(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    run_record["channel_records"]["path"]["channel_state"] = None
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P2 path run_record channel_state missing for materialized observation" in findings


def test_readiness_consistency_fails_on_builder_provenance_and_run_record_channel_state_mismatch(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    builder_provenance["channels"]["path"]["channel_state"] = "REFUTED"
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P2 path channel_state mismatch between builder_provenance and run_record" in findings
    assert "P2 path truth-source reconstruction is incomplete" in findings


def test_readiness_consistency_fails_on_disallowed_truth_source_class(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    run_record["channel_records"]["path"]["truth_source_kind"] = "external_tool_output"
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P2 path truth_source_kind is not in the allowed source classes" in findings


def test_readiness_consistency_fails_on_duplicate_generator_manifest_relative_paths(tmp_path: Path) -> None:
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
    run_sidecar(snapshot=snapshot, options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}))

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))
    duplicate = next(item for item in manifest["outputs"] if item["relative_path"] == "observation_bundle.json")
    manifest["outputs"].append(dict(duplicate))

    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "P7 generator_manifest contains duplicate relative_path entries: observation_bundle.json" in findings
    assert "P2 path observation_artifact pointer is not uniquely reconstructable from generator_manifest" in findings
    assert "P2 path truth-source reconstruction is incomplete" in findings


def test_readiness_consistency_fails_on_invalid_source_class_even_with_guarded_operator_summary(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
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
    run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}),
        comparator_options=BridgeComparatorOptions(enabled=True),
    )

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))
    operator_summary = (run_dir / "v3_sidecar" / "bridge_operator_summary.md").read_text(encoding="utf-8")

    readiness["gate_evidence"]["P2"]["channel_claims"]["path"]["input_source_kind"] = "external_tool_output"
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )
    assert "[exploratory] Bridge Operator Summary" in operator_summary
    assert "P2 path input source kind is not in the allowed source classes" in findings


def test_readiness_consistency_fails_on_ci_promotion_claim_drift(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
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
    run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True}}),
        comparator_options=BridgeComparatorOptions(enabled=True),
    )

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    readiness["ci_status"]["required_promotion_blocked"] = False
    readiness["gate_evidence"]["P5"]["allowed_required_v3_job_names"] = []
    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )

    assert "P5 ci_status required_promotion_blocked mismatch" in findings
    assert "P5 allowed_required_v3_job_names mismatch" in findings


def test_readiness_consistency_fails_on_operator_summary_v3_only_drift(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    pat_path = write_pat_fixture(tmp_path / "pat.json", "pat_numeric_resolution_limited.json")
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
        cap_pair_features_path=tmp_path / "pair_features.parquet",
    )
    from tests.v3.test_cap_materialization import _write_cap_pair_features

    _write_cap_pair_features(tmp_path / "pair_features.parquet")
    run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True, "channels": {"cap": {"enabled": True}}}}),
        comparator_options=BridgeComparatorOptions(enabled=True),
    )

    readiness = json.loads((run_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))
    operator_summary = (run_dir / "v3_sidecar" / "bridge_operator_summary.md").read_text(encoding="utf-8")
    tampered_summary = operator_summary.replace("[v3-only] cap: `observation_materialized`", "")

    findings = audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
        operator_summary=tampered_summary,
    )

    assert "P4 operator_summary v3-only lifecycle labels mismatch" in findings
    assert "P4 operator_summary must visibly label v3-only evidence" in findings
