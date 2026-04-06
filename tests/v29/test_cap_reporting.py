from __future__ import annotations

import json
from pathlib import Path

from crisp.v29.cap_reporting import (
    build_cap_report_bundle,
    validate_cap_report_bundle,
    write_cap_report_bundle,
)


def _cap_payload() -> dict[str, object]:
    return {
        "run_id": "r1",
        "status": "OK",
        "source_of_truth": True,
        "diagnostics_json": {},
        "reason_codes": [],
        "cap_batch_verdict": "PASS",
        "cap_batch_reason_code": None,
        "verdict_layer0": "PASS",
        "verdict_layer1": "PASS",
        "verdict_layer2": None,
        "verdict_final": "PASS",
    }


def test_build_cap_report_bundle_uses_supplied_provenance_without_reestimating() -> None:
    provenance = {
        "cap_truth_source_path": "cap_batch_eval.json",
        "cap_truth_source_digest": "sha256:manual",
        "cap_truth_source_run_id": "r1",
        "cap_truth_source_keys": sorted(_cap_payload().keys()),
        "cap_truth_source_layer_consistency": True,
        "cap_truth_source_status": "verified",
    }
    bundle = build_cap_report_bundle(
        run_id="r1",
        cap_batch_eval_path="cap_batch_eval.json",
        cap_truth_source_provenance=provenance,
        layer2_result=None,
        comparison_type="cross-regime",
        comparison_type_source="explicit_override",
        skip_reason_codes=[],
        inventory_json_errors=[],
        pathyes_metadata={},
        eval_notes=[],
        qc_conditions_run=["native"],
        qc_excluded_rows_count=0,
        qc_warnings=[],
        qc_result="PASS",
        qc_extra=None,
        resource_profile="smoke",
        collapse_conditions=["native"],
        collapse_cap_metrics={},
    )

    assert bundle.eval_report["cap_truth_source_digest"] == "sha256:manual"
    assert bundle.qc_report["cap_truth_source_digest"] == "sha256:manual"
    assert bundle.collapse_figure_spec["cap_truth_source_digest"] == "sha256:manual"


def test_validate_cap_report_bundle_detects_truth_source_drift() -> None:
    provenance = {
        "cap_truth_source_path": "cap_batch_eval.json",
        "cap_truth_source_digest": "sha256:manual",
        "cap_truth_source_run_id": "r1",
        "cap_truth_source_keys": sorted(_cap_payload().keys()),
        "cap_truth_source_layer_consistency": True,
        "cap_truth_source_status": "verified",
    }
    bundle = build_cap_report_bundle(
        run_id="r1",
        cap_batch_eval_path="cap_batch_eval.json",
        cap_truth_source_provenance=provenance,
        layer2_result=None,
        comparison_type="cross-regime",
        comparison_type_source="explicit_override",
        skip_reason_codes=[],
        inventory_json_errors=[],
        pathyes_metadata={},
        eval_notes=[],
        qc_conditions_run=["native"],
        qc_excluded_rows_count=0,
        qc_warnings=[],
        qc_result="PASS",
        qc_extra=None,
        resource_profile="smoke",
        collapse_conditions=["native"],
        collapse_cap_metrics={},
    )

    errors, warnings = validate_cap_report_bundle(bundle, cap_batch_eval_source=_cap_payload())

    assert warnings == []
    assert "CAP_TRUTH_SOURCE_MISMATCH:eval_report:cap_truth_source_digest" in errors


def test_write_cap_report_bundle_writes_prebuilt_payloads(tmp_path: Path) -> None:
    provenance = {
        "cap_truth_source_path": "cap_batch_eval.json",
        "cap_truth_source_digest": "sha256:manual",
        "cap_truth_source_run_id": "r1",
        "cap_truth_source_keys": sorted(_cap_payload().keys()),
        "cap_truth_source_layer_consistency": True,
        "cap_truth_source_status": "verified",
    }
    bundle = build_cap_report_bundle(
        run_id="r1",
        cap_batch_eval_path="cap_batch_eval.json",
        cap_truth_source_provenance=provenance,
        layer2_result=None,
        comparison_type="cross-regime",
        comparison_type_source="explicit_override",
        skip_reason_codes=[],
        inventory_json_errors=[],
        pathyes_metadata={},
        eval_notes=[],
        qc_conditions_run=["native"],
        qc_excluded_rows_count=0,
        qc_warnings=[],
        qc_result="PASS",
        qc_extra=None,
        resource_profile="smoke",
        collapse_conditions=["native"],
        collapse_cap_metrics={},
    )

    written = write_cap_report_bundle(tmp_path, bundle)
    eval_payload = json.loads(written["eval_report.json"].read_text(encoding="utf-8"))

    assert written["qc_report.json"].exists()
    assert written["collapse_figure_spec.json"].exists()
    assert eval_payload["cap_truth_source_digest"] == "sha256:manual"
