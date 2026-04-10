from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.io.tableio import write_records_table
from crisp.v3.policy import parse_sidecar_options
from crisp.v3.readiness.consistency import reconstruct_truth_source_claims
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
            }
        ],
    )
    return Path(table.path)


def test_truth_source_reconstruction_rebuilds_required_fields_from_layer0_and_layer1(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    (run_dir / "output_inventory.json").write_text(
        json.dumps({"generated_outputs": ["run_manifest.json", "output_inventory.json"]}),
        encoding="utf-8",
    )
    _write_evidence_core(run_dir / "evidence_core.parquet")
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
        rc2_generated_outputs=["run_manifest.json", "output_inventory.json", "evidence_core.parquet"],
        cap_pair_features_path=pair_features_path,
    )

    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options(
            {
                "v3_sidecar": {
                    "enabled": True,
                    "channels": {
                        "cap": {"enabled": True},
                        "catalytic": {"enabled": True},
                    },
                }
            }
        ),
    )

    assert result is not None
    builder_provenance = json.loads((run_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    run_record = json.loads((run_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    claims = reconstruct_truth_source_claims(
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    )

    assert set(claims) == {"path", "cap", "catalytic"}
    assert claims["path"]["channel_evidence_artifact_pointer"] == "channel_evidence_path.jsonl"
    assert claims["cap"]["channel_evidence_artifact_pointer"] == "channel_evidence_cap.jsonl"
    assert claims["catalytic"]["channel_evidence_artifact_pointer"] == "channel_evidence_catalytic.jsonl"
    assert claims["path"]["source_location_kind"] == "repo_input_snapshot"
    assert claims["cap"]["source_location_kind"] == "repo_input_snapshot"
    assert claims["catalytic"]["source_location_kind"] == "run_output_snapshot"
    for channel_id, claim in claims.items():
        assert claim["source_label"] is not None
        assert claim["source_digest"] is not None
        assert claim["builder_identity"] is not None
        assert claim["projector_identity"] is not None
        assert claim["observation_artifact_pointer"] == "observation_bundle.json"
        assert claim["observation_artifact_descriptor"]["relative_path"] == "observation_bundle.json"
        assert claim["required_fields_complete"] is True
        assert claim["truth_source_chain_matches"] is True
        assert claim["builder_status_matches"] is True
        assert claim["channel_state_matches"] is True
        assert claim["observation_present_matches"] is True
        assert claim["observation_artifact_unique"] is True
        assert claim["channel_evidence_artifact_unique"] is True
        assert claim["manifest_duplicate_relative_paths"] == []
        assert claim["reconstruction_complete"] is True
        assert claim["manifest_expected_output_digest"] == manifest["expected_output_digest"]
