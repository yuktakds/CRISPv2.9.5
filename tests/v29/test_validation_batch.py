"""検証バッチ: FAIL-4 修正（ablation 条件追加）の確認。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from crisp.v29.validation import run_validation_batch


def _write_manifest(
    tmp_path: Path,
    run_mode: str = "core-only",
    *,
    target_config_role: str | None = None,
    completion_basis_json: dict[str, object] | None = None,
) -> Path:
    manifest = {
        "run_id": "test_run",
        "run_mode": run_mode,
        "generated_outputs": ["run_manifest.json"],
    }
    if target_config_role is not None:
        manifest["target_config_role"] = target_config_role
    if completion_basis_json is not None:
        manifest["completion_basis_json"] = completion_basis_json
    p = tmp_path / "run_manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


def _write_rule1_assessments(tmp_path: Path) -> None:
    """rule1_assessments.jsonl をダミーで生成する。"""
    rows = [
        {
            "molecule_id": f"mol_{i:03d}",
            "rule1_verdict": "PASS" if i % 2 == 0 else "FAIL",
            "rule1_reason_code": None if i % 2 == 0 else "FAIL_R1_NO_RING_LOCK",
            "rule1_applicability": "PATH_EVALUABLE",
            "ring_lock_present": i % 2 == 0,
            "rigid_volume_proxy": 1.2 if i % 2 == 0 else 0.3,
        }
        for i in range(6)
    ]
    p = tmp_path / "rule1_assessments.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_validation_batch_writes_reports(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")
    assert result.result in {"PASS", "FAIL", "UNCLEAR"}
    assert Path(result.qc_report_path).exists()
    assert Path(result.eval_report_path).exists()
    assert Path(result.collapse_figure_spec_path).exists()


def test_validation_batch_includes_native_condition(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")
    assert "native" in result.conditions_run


def test_validation_batch_adds_rule1_ablation_conditions(tmp_path: Path) -> None:
    """FAIL-4 修正確認: rule1 ablation 条件が conditions_run に含まれる。"""
    manifest_path = _write_manifest(tmp_path, run_mode="core+rule1")
    _write_rule1_assessments(tmp_path)

    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")

    assert "rule1_sensor_drop" in result.conditions_run, (
        f"rule1_sensor_drop not in conditions_run: {result.conditions_run}"
    )
    assert "rule1_threshold_off" in result.conditions_run, (
        f"rule1_threshold_off not in conditions_run: {result.conditions_run}"
    )


def test_validation_batch_rule3_conditions_are_skipped(tmp_path: Path) -> None:
    """Phase-aware rule: rule3 条件は current snapshot でスキップ記録される。"""
    manifest_path = _write_manifest(tmp_path)
    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")

    qc = json.loads(Path(result.qc_report_path).read_text(encoding="utf-8"))
    skipped = qc.get("skipped_conditions", [])
    assert "rule3_no_struct_conn" in skipped
    assert "rule3_random_order" in skipped
    assert "rule3_no_near_band" in skipped


def test_validation_batch_ablation_diagnostics_recorded(tmp_path: Path) -> None:
    """ablation_diagnostics が qc_report に記録されている。"""
    manifest_path = _write_manifest(tmp_path, run_mode="core+rule1")
    _write_rule1_assessments(tmp_path)

    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")
    qc = json.loads(Path(result.qc_report_path).read_text(encoding="utf-8"))

    diag = qc.get("ablation_diagnostics", {})
    assert "rule1_sensor_drop" in diag
    assert "rule1_threshold_off" in diag
    # rule1_sensor_drop は全行 UNCLEAR になる
    sensor_drop = diag["rule1_sensor_drop"]
    assert sensor_drop["verdict_distribution"].get("UNCLEAR", 0) == 6


def test_validation_batch_does_not_emit_pathyes_skip_without_request(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path, run_mode="core+rule1")
    _write_rule1_assessments(tmp_path)

    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")
    qc = json.loads(Path(result.qc_report_path).read_text(encoding="utf-8"))

    warnings = qc.get("warnings", [])
    assert not any("SKIP_PATHYES_BOOTSTRAP" in warning for warning in warnings)


def test_validation_batch_emits_pathyes_skip_only_for_requested_bootstrap_force_false(tmp_path: Path) -> None:
    manifest = {
        "run_id": "test_run",
        "run_mode": "core+rule1",
        "generated_outputs": ["run_manifest.json"],
        "completion_basis_json": {
            "pathyes_mode_requested": "bootstrap",
            "pathyes_force_false_requested": True,
            "skip_reason_codes": ["SKIP_PATHYES_BOOTSTRAP"],
        },
    }
    manifest_path = tmp_path / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _write_rule1_assessments(tmp_path)

    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")
    qc = json.loads(Path(result.qc_report_path).read_text(encoding="utf-8"))

    warnings = qc.get("warnings", [])
    assert any("SKIP_PATHYES_BOOTSTRAP" in warning for warning in warnings)


def test_validation_batch_reads_machine_readable_skip_reason_codes(tmp_path: Path) -> None:
    manifest = {
        "run_id": "test_run",
        "run_mode": "core+rule1",
        "generated_outputs": ["run_manifest.json"],
        "completion_basis_json": {
            "skip_reason_codes": ["SKIP_PATHYES_BOOTSTRAP"],
        },
    }
    manifest_path = tmp_path / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _write_rule1_assessments(tmp_path)

    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")
    qc = json.loads(Path(result.qc_report_path).read_text(encoding="utf-8"))

    warnings = qc.get("warnings", [])
    assert any("SKIP_PATHYES_BOOTSTRAP" in warning for warning in warnings)


def test_validation_batch_writes_machine_readable_report_metadata(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        run_mode="core+rule1",
        target_config_role="production",
        completion_basis_json={
            "comparison_type": "cross-regime",
            "comparison_type_source": "explicit_override",
            "skip_reason_codes": ["SKIP_PATHYES_BOOTSTRAP"],
            "pathyes_mode_requested": "pat-backed",
            "pathyes_mode_resolved": "pat-backed",
            "pathyes_state_source": "pat_diagnostics_json",
            "pathyes_diagnostics_status": "loaded",
            "pathyes_diagnostics_source": "D:/runs/test_run/pat.json",
            "pathyes_goal_precheck_passed": True,
            "pathyes_rule1_applicability": "PATH_EVALUABLE",
        },
    )
    _write_rule1_assessments(tmp_path)

    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")

    qc = json.loads(Path(result.qc_report_path).read_text(encoding="utf-8"))
    eval_report = json.loads(Path(result.eval_report_path).read_text(encoding="utf-8"))
    collapse = json.loads(Path(result.collapse_figure_spec_path).read_text(encoding="utf-8"))

    assert qc["comparison_type"] == "cross-regime"
    assert qc["comparison_type_source"] == "explicit_override"
    assert qc["skip_reason_codes"] == ["SKIP_PATHYES_BOOTSTRAP"]
    assert qc["inventory_json_errors"] == []
    assert qc["pathyes_mode_requested"] == "pat-backed"
    assert qc["pathyes_mode_resolved"] == "pat-backed"
    assert qc["pathyes_state_source"] == "pat_diagnostics_json"
    assert qc["pathyes_diagnostics_status"] == "loaded"
    assert qc["pathyes_goal_precheck_passed"] is True
    assert qc["pathyes_rule1_applicability"] == "PATH_EVALUABLE"
    assert eval_report["comparison_type"] == "cross-regime"
    assert eval_report["comparison_type_source"] == "explicit_override"
    assert eval_report["skip_reason_codes"] == ["SKIP_PATHYES_BOOTSTRAP"]
    assert eval_report["inventory_json_errors"] == []
    assert eval_report["pathyes_mode_requested"] == "pat-backed"
    assert eval_report["pathyes_mode_resolved"] == "pat-backed"
    assert eval_report["pathyes_state_source"] == "pat_diagnostics_json"
    assert eval_report["pathyes_diagnostics_status"] == "loaded"
    assert eval_report["pathyes_goal_precheck_passed"] is True
    assert eval_report["pathyes_rule1_applicability"] == "PATH_EVALUABLE"
    assert collapse["comparison_type"] == "cross-regime"
    assert collapse["comparison_type_source"] == "explicit_override"
    assert collapse["skip_reason_codes"] == ["SKIP_PATHYES_BOOTSTRAP"]
    assert collapse["inventory_json_errors"] == []
    assert collapse["pathyes_mode_requested"] == "pat-backed"
    assert collapse["pathyes_mode_resolved"] == "pat-backed"
    assert collapse["pathyes_state_source"] == "pat_diagnostics_json"
    assert collapse["pathyes_diagnostics_status"] == "loaded"
    assert collapse["pathyes_goal_precheck_passed"] is True
    assert collapse["pathyes_rule1_applicability"] == "PATH_EVALUABLE"


def test_validation_batch_derives_comparison_type_from_target_role(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        run_mode="core-only",
        target_config_role="benchmark",
    )

    result = run_validation_batch(manifest_path, "smoke", tmp_path / "out")

    qc = json.loads(Path(result.qc_report_path).read_text(encoding="utf-8"))
    assert qc["comparison_type"] == "same-config"
    assert qc["comparison_type_source"] == "config_role_default"
