from __future__ import annotations

from crisp.v3.vn06_readiness import (
    VN06_M2_TRIGGER_GATES,
    build_verdict_record_expected_pairs,
    collect_verdict_record_dual_write_mismatches,
    evaluate_vn06_readiness,
)


def _sidecar_run_record() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "output_root": "out/v3_sidecar",
        "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
        "comparator_scope": "path_only_partial",
        "comparable_channels": ["path"],
        "v3_only_evidence_channels": ["catalytic"],
        "channel_lifecycle_states": {
            "path": "observation_materialized",
            "cap": "disabled",
            "catalytic": "observation_materialized",
        },
        "bridge_diagnostics": {
            "bridge_comparison_summary": {
                "run_drift_report": {
                    "path_component_match_rate": 1.0,
                }
            }
        },
    }


def _verdict_record() -> dict[str, object]:
    payload = build_verdict_record_expected_pairs(_sidecar_run_record())
    return {
        "schema_version": "crisp.v3.verdict_record/v1",
        **payload,
        "full_verdict_computable": False,
        "full_verdict_comparable_count": 0,
        "verdict_match_rate": None,
        "verdict_mismatch_rate": None,
        "v3_shadow_verdict": None,
        "authority_transfer_complete": False,
        "sidecar_run_record_artifact": "sidecar_run_record.json",
        "generator_manifest_artifact": "generator_manifest.json",
    }


def test_vn06_readiness_is_schema_complete_and_executable_when_m1_is_clean() -> None:
    readiness = evaluate_vn06_readiness(
        verdict_record=_verdict_record(),
        sidecar_run_record=_sidecar_run_record(),
        manifest_outputs=[
            {"relative_path": "verdict_record.json"},
            {"relative_path": "sidecar_run_record.json"},
        ],
    )

    assert readiness["schema_complete"] is True
    assert readiness["dual_write_mismatch_count"] == 0
    assert readiness["manifest_registration_complete"] is True
    assert readiness["authority_transfer_not_yet_executed"] is True
    assert readiness["authority_transfer_executable"] is True
    assert readiness["exact_m2_trigger"]["requires_vn_gates"] == list(VN06_M2_TRIGGER_GATES)


def test_vn06_readiness_reports_dual_write_mismatch() -> None:
    verdict_record = _verdict_record()
    verdict_record["comparable_channels"] = ["path", "cap"]

    mismatches = collect_verdict_record_dual_write_mismatches(
        verdict_record=verdict_record,
        sidecar_run_record=_sidecar_run_record(),
    )
    readiness = evaluate_vn06_readiness(
        verdict_record=verdict_record,
        sidecar_run_record=_sidecar_run_record(),
        manifest_outputs=[{"relative_path": "verdict_record.json"}],
    )

    assert mismatches == ("comparable_channels",)
    assert readiness["dual_write_mismatch_count"] == 1
    assert readiness["authority_transfer_executable"] is False


def test_vn06_readiness_requires_manifest_registration() -> None:
    readiness = evaluate_vn06_readiness(
        verdict_record=_verdict_record(),
        sidecar_run_record=_sidecar_run_record(),
        manifest_outputs=[{"relative_path": "sidecar_run_record.json"}],
    )

    assert readiness["manifest_registration_complete"] is False
    assert readiness["authority_transfer_executable"] is False
