from __future__ import annotations

import json

from crisp.v3.contracts import BridgeComparatorOptions
from crisp.v3.policy import parse_sidecar_options
from crisp.v3.runner import build_sidecar_snapshot, run_sidecar
from tests.v3.helpers import make_config, write_pat_fixture


def test_runner_materializes_run_drift_candidacy_and_wp6_artifacts_when_comparator_enabled(tmp_path) -> None:
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
    assert "run_drift_report.json" in result.materialized_outputs
    assert "required_ci_candidacy_report.json" in result.materialized_outputs
    assert "verdict_record.json" in result.materialized_outputs
    assert "internal_full_scv_observation_bundle.json" in result.materialized_outputs
    assert "shadow_stability_campaign.json" in result.materialized_outputs

    run_drift_report = json.loads((run_dir / "v3_sidecar" / "run_drift_report.json").read_text(encoding="utf-8"))
    candidacy_report = json.loads((run_dir / "v3_sidecar" / "required_ci_candidacy_report.json").read_text(encoding="utf-8"))
    verdict_record = json.loads((run_dir / "v3_sidecar" / "verdict_record.json").read_text(encoding="utf-8"))
    internal_full_bundle = json.loads((run_dir / "v3_sidecar" / "internal_full_scv_observation_bundle.json").read_text(encoding="utf-8"))
    shadow_campaign = json.loads((run_dir / "v3_sidecar" / "shadow_stability_campaign.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))

    assert run_drift_report["full_verdict_computable"] is False
    assert run_drift_report["full_verdict_comparable_count"] == 0
    assert candidacy_report["required_matrix_mutation_allowed"] is False
    assert candidacy_report["human_explicit_decision_required"] is True
    assert verdict_record["authority_transfer_complete"] is False
    assert verdict_record["v3_shadow_verdict"] is None
    assert verdict_record["path_component_match_rate"] == run_drift_report["path_component_match_rate"]
    assert internal_full_bundle["bridge_diagnostics"]["bundle_kind"] == "internal_full_scv"
    assert internal_full_bundle["bridge_diagnostics"]["operator_surface_active"] is False
    assert shadow_campaign["required_window_size"] == 30
    assert shadow_campaign["campaign_passed"] is False
    assert {
        item["relative_path"]
        for item in manifest["outputs"]
    } >= {
        "run_drift_report.json",
        "required_ci_candidacy_report.json",
        "verdict_record.json",
        "internal_full_scv_observation_bundle.json",
        "shadow_stability_campaign.json",
    }
