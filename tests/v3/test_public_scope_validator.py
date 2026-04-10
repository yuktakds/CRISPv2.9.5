from __future__ import annotations

from crisp.v3.public_scope_validator import validate_keep_path_rc_bundle


def _sidecar_run_record() -> dict[str, object]:
    return {
        "comparator_scope": "path_only_partial",
        "comparable_channels": ["path"],
        "v3_only_evidence_channels": ["cap", "catalytic"],
        "channel_lifecycle_states": {
            "path": "observation_materialized",
            "cap": "observation_materialized",
            "catalytic": "observation_materialized",
        },
        "channel_comparability": {
            "path": "component_verdict_comparable",
            "cap": None,
            "catalytic": None,
        },
        "bridge_diagnostics": {
            "layer0_authority_artifact": "verdict_record.json",
            "sidecar_run_record_role": "backward_compatible_mirror",
            "layer0_authority_mirror": {
                "run_id": "run-1",
                "output_root": "out/v3_sidecar",
                "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
                "comparator_scope": "path_only_partial",
                "comparable_channels": ["path"],
                "v3_only_evidence_channels": ["cap", "catalytic"],
                "channel_lifecycle_states": {
                    "path": "observation_materialized",
                    "cap": "observation_materialized",
                    "catalytic": "observation_materialized",
                },
                "full_verdict_computable": False,
                "full_verdict_comparable_count": 0,
                "verdict_match_rate": None,
                "verdict_mismatch_rate": None,
                "path_component_match_rate": 1.0,
                "v3_shadow_verdict": None,
                "authority_transfer_complete": True,
            },
        },
    }


def _verdict_record() -> dict[str, object]:
    return {
        "schema_version": "crisp.v3.verdict_record/v1",
        "run_id": "run-1",
        "output_root": "out/v3_sidecar",
        "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
        "comparator_scope": "path_only_partial",
        "comparable_channels": ["path"],
        "v3_only_evidence_channels": ["cap", "catalytic"],
        "channel_lifecycle_states": {
            "path": "observation_materialized",
            "cap": "observation_materialized",
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


def _output_inventory() -> dict[str, object]:
    return {
        "generated_outputs": [
            "run_manifest.json",
            "output_inventory.json",
        ]
    }


def _bridge_summary() -> dict[str, object]:
    return {
        "component_matches": {
            "path": True,
        }
    }


def test_keep_path_rc_validator_accepts_valid_bundle() -> None:
    errors, warnings, diagnostics = validate_keep_path_rc_bundle(
        sidecar_run_record=_sidecar_run_record(),
        verdict_record=_verdict_record(),
        output_inventory=_output_inventory(),
        bridge_summary=_bridge_summary(),
        operator_summary=(
            "# [exploratory] Bridge Operator Summary\n"
            "- semantic_policy_version: `crisp.v3.semantic_policy/rev3-sidecar-first`\n"
            "- verdict_match_rate: `N/A`\n"
        ),
    )

    assert errors == []
    assert warnings == []
    assert diagnostics["validation_passed"] is True


def test_keep_path_rc_validator_rejects_numeric_verdict_match_rate_in_path_only_scope() -> None:
    verdict_record = _verdict_record()
    verdict_record["verdict_match_rate"] = 1.0

    errors, _, diagnostics = validate_keep_path_rc_bundle(
        sidecar_run_record=_sidecar_run_record(),
        verdict_record=verdict_record,
        output_inventory=_output_inventory(),
    )

    assert "KEEP_PATH_RC_NUMERIC_VERDICT_MATCH_RATE_FORBIDDEN:verdict_record" in errors
    assert diagnostics["validation_passed"] is False


def test_keep_path_rc_validator_rejects_v3_shadow_verdict_activation() -> None:
    verdict_record = _verdict_record()
    verdict_record["v3_shadow_verdict"] = "PASS"

    errors, _, _ = validate_keep_path_rc_bundle(
        sidecar_run_record=_sidecar_run_record(),
        verdict_record=verdict_record,
        output_inventory=_output_inventory(),
    )

    assert "KEEP_PATH_RC_V3_SHADOW_VERDICT_ACTIVE:verdict_record" in errors


def test_keep_path_rc_validator_rejects_cap_or_catalytic_as_comparable() -> None:
    sidecar_run_record = _sidecar_run_record()
    sidecar_run_record["comparable_channels"] = ["path", "cap"]
    sidecar_run_record["channel_comparability"] = {
        "path": "component_verdict_comparable",
        "cap": "component_verdict_comparable",
        "catalytic": None,
    }
    verdict_record = _verdict_record()
    verdict_record["comparable_channels"] = ["path", "cap"]

    errors, _, _ = validate_keep_path_rc_bundle(
        sidecar_run_record=sidecar_run_record,
        verdict_record=verdict_record,
        output_inventory=_output_inventory(),
    )

    assert "KEEP_PATH_RC_V3_ONLY_CHANNEL_BECAME_COMPARABLE" in errors
    assert any(error.startswith("KEEP_PATH_RC_CHANNEL_SEMANTICS:") for error in errors)


def test_keep_path_rc_validator_rejects_component_match_leak_and_output_inventory_mutation() -> None:
    errors, _, _ = validate_keep_path_rc_bundle(
        sidecar_run_record=_sidecar_run_record(),
        verdict_record=_verdict_record(),
        output_inventory={
            "generated_outputs": [
                "run_manifest.json",
                "v3_sidecar/verdict_record.json",
            ]
        },
        bridge_summary={
            "component_matches": {
                "path": True,
                "catalytic": True,
            }
        },
    )

    assert "KEEP_PATH_RC_COMPONENT_MATCH_LEAK:catalytic" in errors
    assert "KEEP_PATH_RC_OUTPUT_INVENTORY_MUTATED:v3_sidecar/verdict_record.json" in errors
