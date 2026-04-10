from __future__ import annotations

import json
from pathlib import Path

import pytest

from crisp.v29.cli import run_integrated_v29
from crisp.v29.ops_guard import (
    evaluate_manifest_artifact_state,
    validate_preexisting_run_artifacts,
)
from tests.v29_smoke_helpers import (
    CONFIG_DIR,
    DATA_DIR,
    REPO_ROOT,
    make_stub_core_bridge,
    write_managed_theta_table,
    write_real_library_subset,
)


def test_validate_preexisting_run_artifacts_detects_stale_manifest_and_role_mismatch(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_mode": "core+rule1+cap",
                "target_config_role": "production",
                "generated_outputs": ["output_inventory.json", "cap_batch_eval.json"],
                "completion_basis_json": {
                    "required_outputs_by_mode": {
                        "core+rule1+cap": [
                            "output_inventory.json",
                            "cap_batch_eval.json",
                        ]
                    }
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    errors, warnings, diagnostics = validate_preexisting_run_artifacts(
        run_dir,
        expected_config_role="benchmark",
        expected_run_mode="core+rule1+cap",
    )

    assert warnings == []
    assert any(error.startswith("STALE_MANIFEST_ROLE_MISMATCH:") for error in errors)
    assert any(error.startswith("STALE_MANIFEST_MISSING_REQUIRED_ARTIFACTS:") for error in errors)
    assert any(error.startswith("STALE_MANIFEST_MISSING_GENERATED_ARTIFACTS:") for error in errors)
    assert diagnostics["artifact_state"]["stale_manifest_detected"] is True


def test_validate_preexisting_run_artifacts_warns_for_local_heavy_run(tmp_path: Path) -> None:
    errors, warnings, _ = validate_preexisting_run_artifacts(
        tmp_path / "run",
        expected_config_role="production",
        expected_run_mode="full",
    )

    assert errors == []
    assert warnings == [
        "LOCAL_HEAVY_RUN_NOT_CI_REQUIRED: full runs are operator-only local checks and require the heavy-run checklist"
    ]


def test_evaluate_manifest_artifact_state_reports_missing_required_outputs(tmp_path: Path) -> None:
    payload = evaluate_manifest_artifact_state(
        tmp_path,
        {
            "run_mode": "core+rule1",
            "generated_outputs": ["run_manifest.json", "output_inventory.json"],
            "completion_basis_json": {
                "required_outputs_by_mode": {
                    "core+rule1": ["run_manifest.json", "output_inventory.json", "rule1_assessments.parquet"]
                }
            },
        },
    )

    assert payload["missing_required_outputs"] == [
        "run_manifest.json",
        "output_inventory.json",
        "rule1_assessments.parquet",
    ]
    assert payload["stale_manifest_detected"] is True


def test_run_integrated_v29_warn_policy_falls_back_from_stale_theta_table(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = CONFIG_DIR / "9kr6_cys328.benchmark.yaml"
    library_path = write_real_library_subset(
        DATA_DIR / "libraries" / "CYS-3200.smiles",
        tmp_path / "libraries" / "benchmark-bootstrap.smiles",
        limit=2,
    )
    stale_theta_table_path = write_managed_theta_table(
        tmp_path / "theta" / "stale_theta_rule1_table.parquet",
        config_path=config_path,
        table_status="stale",
        calibration_cohort="bootstrap-warn",
    )
    integrated_config_path = tmp_path / "integrated-bootstrap.json"
    integrated_config_path.write_text(
        json.dumps(
            {
                "pathyes_mode": "bootstrap",
                "theta_rule1_table": str(stale_theta_table_path),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(
            library_path=library_path,
            target_id="9KR6_CYS328",
        ),
    )

    out_dir = tmp_path / "runs" / "benchmark-bootstrap"
    result = run_integrated_v29(
        repo_root=REPO_ROOT,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=CONFIG_DIR / "stageplan.empty.json",
        out_dir=out_dir,
        integrated_config_path=integrated_config_path,
        run_mode="core+rule1",
    )

    theta_resolution = json.loads((out_dir / "theta_rule1_resolution.json").read_text(encoding="utf-8"))
    assert result["run_mode_complete"] is True
    assert theta_resolution["theta_runtime_policy"] == "warn"
    assert theta_resolution["theta_runtime_fallback_used"] is True
    assert theta_resolution["theta_runtime_policy_reason"] == "THETA_RULE1_TABLE_STALE"
    assert theta_resolution["table_id"] == "builtin:none"


def test_run_integrated_v29_rejects_stale_production_manifest_for_benchmark_role(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = CONFIG_DIR / "9kr6_cys328.benchmark.yaml"
    library_path = write_real_library_subset(
        DATA_DIR / "libraries" / "CYS-3200.smiles",
        tmp_path / "libraries" / "benchmark-stale-manifest.smiles",
        limit=2,
    )
    out_dir = tmp_path / "runs" / "benchmark-stale-manifest"
    out_dir.mkdir(parents=True)
    (out_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_mode": "core+rule1+cap",
                "target_config_role": "production",
                "generated_outputs": ["output_inventory.json"],
                "completion_basis_json": {
                    "required_outputs_by_mode": {
                        "core+rule1+cap": ["output_inventory.json"]
                    }
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(
            library_path=library_path,
            target_id="9KR6_CYS328",
        ),
    )

    with pytest.raises(Exception, match="STALE_MANIFEST_ROLE_MISMATCH"):
        run_integrated_v29(
            repo_root=REPO_ROOT,
            config_path=config_path,
            library_path=library_path,
            stageplan_path=CONFIG_DIR / "stageplan.empty.json",
            out_dir=out_dir,
            run_mode="core-only",
        )
