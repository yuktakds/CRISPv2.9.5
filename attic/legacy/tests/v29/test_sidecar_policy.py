from __future__ import annotations

from crisp.v29.sidecar_policy import SIDECAR_POLICIES, sidecar_policy_rows


def test_sidecar_policy_catalog_covers_current_v29_sidecars() -> None:
    rows = sidecar_policy_rows()
    names = {row["artifact_name"] for row in rows}

    assert names == {
        "core_bridge_diagnostics.json",
        "legacy_phase1_evidence_alias.json",
        "rule3_trace_summary.json",
        "theta_rule1_resolution.json",
        "rule1_branch_diagnostics.json",
    }


def test_sidecar_policy_inventory_treatment_stays_generated_outputs_only() -> None:
    assert all(
        policy.inventory_treatment == "generated_outputs_only"
        for policy in SIDECAR_POLICIES.values()
    )
    assert all(policy.completion_blocking is False for policy in SIDECAR_POLICIES.values())


def test_sidecar_policy_distinguishes_rule1_and_rule3_handling() -> None:
    theta_policy = SIDECAR_POLICIES["theta_rule1_resolution.json"]
    rule3_policy = SIDECAR_POLICIES["rule3_trace_summary.json"]

    assert theta_policy.policy_class == "conditional"
    assert theta_policy.replay_handling == "required_for_rule1_replay"
    assert "fail_fast" in theta_policy.validator_handling

    assert rule3_policy.policy_class == "conditional"
    assert rule3_policy.replay_handling == "observe_only"
    assert rule3_policy.validator_handling == "non_blocking"
