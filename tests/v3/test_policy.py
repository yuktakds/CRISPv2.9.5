from __future__ import annotations

from crisp.v3.policy import PATH_CHANNEL_FAMILY, PATH_CHANNEL_NAME, SEMANTIC_POLICY_VERSION, parse_sidecar_options, semantic_policy_payload


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


def test_cap_channel_policy_and_opt_in_parse_contract() -> None:
    payload = semantic_policy_payload()
    options = parse_sidecar_options(
        {"v3_sidecar": {"enabled": True, "channels": {"cap": {"enabled": True}}}}
    )

    assert payload["channels"]["cap"]["enabled_by_default"] is False
    assert payload["channels"]["cap"]["materialization_policy"] == "read_only_snapshot_opt_in"
    assert payload["channels"]["cap"]["truth_source_handling"] == "read_only_pair_features_snapshot_not_final_verdict"
    assert options.enabled is True
    assert options.cap_enabled is True


def test_catalytic_channel_policy_and_opt_in_parse_contract() -> None:
    payload = semantic_policy_payload()
    options = parse_sidecar_options(
        {"v3_sidecar": {"enabled": True, "channels": {"catalytic": {"enabled": True}}}}
    )

    assert payload["channels"]["catalytic"]["enabled_by_default"] is False
    assert payload["channels"]["catalytic"]["materialization_policy"] == "read_only_snapshot_opt_in"
    assert payload["channels"]["catalytic"]["truth_source_handling"] == "read_only_evidence_core_snapshot_not_final_verdict"
    assert payload["channels"]["catalytic"]["forbidden_scope"] == [
        "proposal_connected_rule3",
        "same_pose_requirement",
        "corescv_reverse_flow",
        "taxonomy_redesign",
    ]
    assert options.enabled is True
    assert options.catalytic_enabled is True
