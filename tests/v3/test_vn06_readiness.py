from __future__ import annotations

from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    SIDECAR_RUN_RECORD_ROLE,
)
from crisp.v3.vn06_readiness import (
    VN06_M1_SOAK_WINDOW_SIZE,
    VN06_M2_TRIGGER_GATES,
    build_verdict_record_expected_pairs,
    collect_verdict_record_dual_write_mismatches,
    collect_verdict_record_dual_write_source_gaps,
    evaluate_vn06_readiness,
    evaluate_vn06_soak_window,
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
                    "full_verdict_computable": False,
                    "full_verdict_comparable_count": 0,
                    "verdict_match_rate": None,
                    "verdict_mismatch_rate": None,
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


def _m2_verdict_record() -> dict[str, object]:
    return {
        "schema_version": "crisp.v3.verdict_record/v1",
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
        "full_verdict_computable": False,
        "full_verdict_comparable_count": 0,
        "verdict_match_rate": None,
        "verdict_mismatch_rate": None,
        "path_component_match_rate": 1.0,
        "v3_shadow_verdict": None,
        "authority_transfer_complete": True,
        "sidecar_run_record_artifact": "sidecar_run_record.json",
        "generator_manifest_artifact": "generator_manifest.json",
    }


def _m2_sidecar_run_record() -> dict[str, object]:
    return {
        **_sidecar_run_record(),
        "bridge_diagnostics": {
            **dict(_sidecar_run_record()["bridge_diagnostics"]),
            "layer0_authority_artifact": "verdict_record.json",
            "layer0_authority_mode": "M2",
            "sidecar_run_record_role": "backward_compatible_mirror",
            "layer0_authority_mirror": {
                key: value
                for key, value in _m2_verdict_record().items()
                if key
                in {
                    "run_id",
                    "output_root",
                    "semantic_policy_version",
                    "comparator_scope",
                    "comparable_channels",
                    "v3_only_evidence_channels",
                    "channel_lifecycle_states",
                    "full_verdict_computable",
                    "full_verdict_comparable_count",
                    "verdict_match_rate",
                    "verdict_mismatch_rate",
                    "path_component_match_rate",
                    "v3_shadow_verdict",
                    "authority_transfer_complete",
                }
            },
        },
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

    assert readiness["authority_phase"] == "M1"
    assert readiness["schema_complete"] is True
    assert readiness["dual_write_mismatch_count"] == 0
    assert readiness["manifest_registration_complete"] is True
    assert readiness["manifest_required_outputs"] == ["verdict_record.json"]
    assert readiness["authority_source_map_complete"] is True
    assert readiness["authority_source_gaps"] == []
    assert readiness["current_run_operator_surface_inactive"] is True
    assert readiness["current_run_passes_m1_soak_conditions"] is True
    assert readiness["current_run_post_cutover_alignment_clean"] is False
    assert readiness["m1_soak_requirement"]["required_window_size"] == VN06_M1_SOAK_WINDOW_SIZE
    assert readiness["authority_transfer_not_yet_executed"] is True
    assert readiness["authority_transfer_executed"] is False
    assert readiness["authority_transfer_executable"] is True
    assert readiness["authority_transfer_requires_separate_m2_decision"] is True
    assert readiness["exact_m2_trigger"]["requires_vn_gates"] == list(VN06_M2_TRIGGER_GATES)
    assert any(
        row["target_field"] == "full_verdict_computable"
        and row["source_field"].endswith(".full_verdict_computable")
        for row in readiness["authority_field_map"]
    )


def test_vn06_readiness_reports_clean_post_cutover_alignment_in_m2() -> None:
    readiness = evaluate_vn06_readiness(
        verdict_record=_m2_verdict_record(),
        sidecar_run_record=_m2_sidecar_run_record(),
        manifest_outputs=[
            {"relative_path": "verdict_record.json"},
            {"relative_path": "sidecar_run_record.json"},
        ],
    )

    assert readiness["authority_phase"] == "M2"
    assert readiness["canonical_layer0_authority_artifact"] == CANONICAL_LAYER0_AUTHORITY_ARTIFACT
    assert readiness["sidecar_run_record_role"] == SIDECAR_RUN_RECORD_ROLE
    assert readiness["authority_transfer_not_yet_executed"] is False
    assert readiness["authority_transfer_executed"] is True
    assert readiness["authority_transfer_executable"] is False
    assert readiness["authority_transfer_requires_separate_m2_decision"] is False
    assert readiness["current_run_passes_m1_soak_conditions"] is False
    assert readiness["current_run_post_cutover_alignment_clean"] is True
    assert readiness["manifest_required_outputs"] == ["sidecar_run_record.json", "verdict_record.json"]
    assert readiness["authority_source_map_complete"] is True
    assert readiness["dual_write_mismatch_count"] == 0
    assert all(
        row["source_field"].startswith("bridge_diagnostics.layer0_authority_mirror.")
        for row in readiness["authority_field_map"]
    )


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


def test_vn06_readiness_reports_source_gap_from_m2_sidecar_mirror() -> None:
    sidecar_run_record = _m2_sidecar_run_record()
    del sidecar_run_record["bridge_diagnostics"]["layer0_authority_mirror"]["full_verdict_computable"]

    source_gaps = collect_verdict_record_dual_write_source_gaps(
        sidecar_run_record=sidecar_run_record,
        verdict_record=_m2_verdict_record(),
    )
    readiness = evaluate_vn06_readiness(
        verdict_record=_m2_verdict_record(),
        sidecar_run_record=sidecar_run_record,
        manifest_outputs=[
            {"relative_path": "verdict_record.json"},
            {"relative_path": "sidecar_run_record.json"},
        ],
    )

    assert source_gaps == ("full_verdict_computable",)
    assert readiness["authority_source_map_complete"] is False
    assert readiness["authority_source_gaps"] == ["full_verdict_computable"]
    assert readiness["dual_write_mismatches"][0] == "source_missing:full_verdict_computable"


def test_vn06_readiness_requires_sidecar_manifest_registration_after_cutover() -> None:
    readiness = evaluate_vn06_readiness(
        verdict_record=_m2_verdict_record(),
        sidecar_run_record=_m2_sidecar_run_record(),
        manifest_outputs=[{"relative_path": "verdict_record.json"}],
    )

    assert readiness["manifest_registration_complete"] is False
    assert readiness["manifest_missing_outputs"] == ["sidecar_run_record.json"]
    assert readiness["current_run_post_cutover_alignment_clean"] is False


def test_vn06_soak_window_requires_30_consecutive_clean_m1_runs() -> None:
    readiness_history = [
        evaluate_vn06_readiness(
            verdict_record=_verdict_record(),
            sidecar_run_record=_sidecar_run_record(),
            manifest_outputs=[{"relative_path": "verdict_record.json"}],
        )
        for _ in range(VN06_M1_SOAK_WINDOW_SIZE)
    ]

    soak = evaluate_vn06_soak_window(readiness_history=readiness_history)

    assert soak["required_window_size"] == VN06_M1_SOAK_WINDOW_SIZE
    assert soak["required_consecutive_runs"] == VN06_M1_SOAK_WINDOW_SIZE
    assert soak["authority_phase_m1_streak"] is True
    assert soak["window_passed"] is True


def test_vn06_soak_window_fails_when_operator_surface_activates() -> None:
    readiness_history = [
        evaluate_vn06_readiness(
            verdict_record=_verdict_record(),
            sidecar_run_record=_sidecar_run_record(),
            manifest_outputs=[{"relative_path": "verdict_record.json"}],
        )
        for _ in range(VN06_M1_SOAK_WINDOW_SIZE - 1)
    ]
    activated = evaluate_vn06_readiness(
        verdict_record={
            **_verdict_record(),
            "verdict_mismatch_rate": 0.0,
        },
        sidecar_run_record=_sidecar_run_record(),
        manifest_outputs=[{"relative_path": "verdict_record.json"}],
    )

    soak = evaluate_vn06_soak_window(readiness_history=[*readiness_history, activated])

    assert activated["current_run_operator_surface_inactive"] is False
    assert soak["operator_surface_inactive_streak"] is False
    assert soak["window_passed"] is False
