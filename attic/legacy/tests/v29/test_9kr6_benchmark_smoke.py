from __future__ import annotations

import json
from pathlib import Path

from crisp.config.loader import load_target_config
from crisp.v29.cli import run_integrated_v29
from tests.v29_smoke_helpers import (
    CONFIG_DIR,
    DATA_DIR,
    REPO_ROOT,
    assert_outputs_exist,
    make_stub_core_bridge,
    required_cap_smoke_outputs,
    write_managed_theta_table,
    write_minimal_caps_fixture,
    write_pat_diagnostics,
    write_real_library_subset,
)


def test_9kr6_benchmark_integrated_smoke_replays_frozen_baseline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = CONFIG_DIR / "9kr6_cys328.benchmark.yaml"
    config = load_target_config(config_path)
    assert config.frozen_for_regression is True
    assert config.default_comparison_type().value == "same-config"

    library_path = write_real_library_subset(
        DATA_DIR / "libraries" / "CYS-3200.smiles",
        tmp_path / "libraries" / "9kr6-benchmark.smiles",
        limit=2,
    )
    caps_path = write_minimal_caps_fixture(
        tmp_path / "caps" / "caps.parquet",
        target_id=config.target_name,
    )
    pat_diagnostics_path = write_pat_diagnostics(
        tmp_path / "diagnostics" / "pat.json",
        goal_precheck_passed=True,
    )
    theta_table_path = write_managed_theta_table(
        tmp_path / "theta" / "theta_rule1_table.parquet",
        config_path=config_path,
        calibration_cohort="benchmark-smoke",
    )
    integrated_config_path = tmp_path / "integrated-benchmark.json"
    integrated_config_path.write_text(
        json.dumps(
            {
                "pathyes_mode": "pat-backed",
                "pat_diagnostics_path": str(pat_diagnostics_path),
                "theta_rule1_table": str(theta_table_path),
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(
            library_path=library_path,
            target_id=config.target_name,
        ),
    )

    out_dir = tmp_path / "runs" / "benchmark"
    result = run_integrated_v29(
        repo_root=REPO_ROOT,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=CONFIG_DIR / "stageplan.empty.json",
        out_dir=out_dir,
        integrated_config_path=integrated_config_path,
        run_mode="core+rule1+cap",
        caps_path=caps_path,
    )

    assert result["run_mode_complete"] is True
    assert_outputs_exist(out_dir, required_cap_smoke_outputs())

    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads((out_dir / "output_inventory.json").read_text(encoding="utf-8"))
    theta_resolution = json.loads((out_dir / "theta_rule1_resolution.json").read_text(encoding="utf-8"))
    qc_report = json.loads((out_dir / "qc_report.json").read_text(encoding="utf-8"))
    eval_report = json.loads((out_dir / "eval_report.json").read_text(encoding="utf-8"))
    collapse_spec = json.loads((out_dir / "collapse_figure_spec.json").read_text(encoding="utf-8"))
    replay_audit = json.loads((out_dir / "replay_audit.json").read_text(encoding="utf-8"))

    assert manifest["target_config_role"] == "benchmark"
    assert manifest["target_config_frozen_for_regression"] is True
    assert manifest["completion_basis_json"]["comparison_type"] == "same-config"
    assert manifest["completion_basis_json"]["comparison_type_source"] == "config_role_default"
    assert manifest["completion_basis_json"]["pathyes_mode_resolved"] == "pat-backed"
    assert manifest["completion_basis_json"]["pathyes_diagnostics_status"] == "loaded"
    assert manifest["completion_basis_json"]["pathyes_rule1_applicability"] == "PATH_EVALUABLE"
    assert manifest["theta_rule1_table_version"] == "2026-04-03"
    assert manifest["theta_rule1_table_digest"].startswith("sha256:")
    assert manifest["theta_rule1_runtime_contract"] == "crisp.v29.theta_rule1.runtime/v1"
    assert theta_resolution["resolution_status"] == "exact_target"
    assert theta_resolution["resolved_lookup_key"] == config.target_name
    assert theta_resolution["validator_errors"] == []

    assert inventory["run_mode_complete"] is True
    assert inventory["completion_checks_json"]["run_mode_complete"] is True
    assert inventory["completion_checks_json"]["required_branch_statuses"]["rule1"] == "COMPLETE"
    assert inventory["completion_checks_json"]["required_branch_statuses"]["cap"] == "COMPLETE"

    for payload in (qc_report, eval_report, collapse_spec, replay_audit):
        assert payload["comparison_type"] == "same-config"
        assert payload["comparison_type_source"] == "config_role_default"
        assert payload["pathyes_mode_resolved"] == "pat-backed"
        assert payload["pathyes_diagnostics_status"] == "loaded"
        assert payload["pathyes_rule1_applicability"] == "PATH_EVALUABLE"

    assert replay_audit["inventory_consistency"] is True
    assert replay_audit["theta_rule1_resolution_available"] is True
    assert replay_audit["theta_rule1_resolution_status"] == "exact_target"
    assert replay_audit["theta_rule1_consistency"] is True
    assert replay_audit["inventory_run_mode_complete"] is True
    assert replay_audit["missing_generated_outputs"] == []
    assert replay_audit["result"] == "PASS"
