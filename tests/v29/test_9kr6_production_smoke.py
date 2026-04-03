from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_9kr6_production_integrated_smoke_enforces_cross_regime_reports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = CONFIG_DIR / "9kr6_cys328.production.yaml"
    benchmark_config_path = CONFIG_DIR / "9kr6_cys328.benchmark.yaml"
    config = load_target_config(config_path)
    assert config.frozen_for_regression is False
    assert config.default_comparison_type().value == "cross-regime"

    library_path = write_real_library_subset(
        DATA_DIR / "libraries" / "CYS-3200.smiles",
        tmp_path / "libraries" / "9kr6-production.smiles",
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
        config_path=benchmark_config_path,
        calibration_cohort="production-smoke",
    )
    integrated_config_path = tmp_path / "integrated-production.json"
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

    out_dir = tmp_path / "runs" / "production"
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
    qc_report = json.loads((out_dir / "qc_report.json").read_text(encoding="utf-8"))
    eval_report = json.loads((out_dir / "eval_report.json").read_text(encoding="utf-8"))
    collapse_spec = json.loads((out_dir / "collapse_figure_spec.json").read_text(encoding="utf-8"))
    replay_audit = json.loads((out_dir / "replay_audit.json").read_text(encoding="utf-8"))

    assert manifest["target_config_role"] == "production"
    assert manifest["target_config_frozen_for_regression"] is False
    assert manifest["completion_basis_json"]["comparison_type"] == "cross-regime"
    assert manifest["completion_basis_json"]["comparison_type_source"] == "config_role_default"
    assert manifest["theta_rule1_table_source"].startswith("benchmark:9kr6_cys328.benchmark.yaml")
    assert manifest["theta_rule1_runtime_contract"] == "crisp.v29.theta_rule1.runtime/v1"

    assert inventory["run_mode_complete"] is True
    assert inventory["completion_checks_json"]["run_mode_complete"] is True

    for payload in (qc_report, eval_report, collapse_spec, replay_audit):
        assert payload["comparison_type"] == "cross-regime"
        assert payload["comparison_type_source"] == "config_role_default"
        assert payload["pathyes_mode_resolved"] == "pat-backed"
        assert payload["pathyes_diagnostics_status"] == "loaded"
        assert payload["pathyes_rule1_applicability"] == "PATH_EVALUABLE"

    assert replay_audit["inventory_consistency"] is True
    assert replay_audit["result"] == "PASS"


def test_9kr6_production_same_config_override_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = CONFIG_DIR / "9kr6_cys328.production.yaml"
    benchmark_config_path = CONFIG_DIR / "9kr6_cys328.benchmark.yaml"
    config = load_target_config(config_path)

    library_path = write_real_library_subset(
        DATA_DIR / "libraries" / "CYS-3200.smiles",
        tmp_path / "libraries" / "9kr6-production-invalid.smiles",
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
        config_path=benchmark_config_path,
        calibration_cohort="production-invalid",
    )
    integrated_config_path = tmp_path / "integrated-production-invalid.json"
    integrated_config_path.write_text(
        json.dumps(
            {
                "pathyes_mode": "pat-backed",
                "pat_diagnostics_path": str(pat_diagnostics_path),
                "theta_rule1_table": str(theta_table_path),
                "comparison_type": "same-config",
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

    out_dir = tmp_path / "runs" / "production-invalid"
    with pytest.raises(ValueError, match="comparison_type='same-config'"):
        run_integrated_v29(
            repo_root=REPO_ROOT,
            config_path=config_path,
            library_path=library_path,
            stageplan_path=CONFIG_DIR / "stageplan.empty.json",
            out_dir=out_dir,
            integrated_config_path=integrated_config_path,
            run_mode="core+rule1+cap",
            caps_path=caps_path,
        )

    assert not (out_dir / "run_manifest.json").exists()
    assert not (out_dir / "qc_report.json").exists()
