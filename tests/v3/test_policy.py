from __future__ import annotations

from crisp.v3.policy import PATH_CHANNEL_FAMILY, PATH_CHANNEL_NAME, SEMANTIC_POLICY_VERSION, semantic_policy_payload


def test_semantic_policy_freezes_sidecar_first_contracts() -> None:
    payload = semantic_policy_payload()

    assert payload["semantic_policy_version"] == SEMANTIC_POLICY_VERSION
    assert payload["mode"] == "sidecar-first"
    assert payload["final_verdict_emitted"] is False
    assert payload["contracts"] == {
        "scv_only_returns_verdicts": True,
        "channel_evidence_returns_verdicts": False,
        "scv_bridge_is_routing_shell": True,
    }


def test_path_channel_policy_is_tunnel_only() -> None:
    payload = semantic_policy_payload()

    assert payload["channels"][PATH_CHANNEL_NAME]["formal_families"] == [PATH_CHANNEL_FAMILY]
    assert payload["channels"][PATH_CHANNEL_NAME]["goal_precheck_failure_handling"] == "run_level_diagnostic_only"
    assert payload["channels"][PATH_CHANNEL_NAME]["persistence_confidence_handling"] == "record_only_not_a_gate"

