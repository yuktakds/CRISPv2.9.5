from __future__ import annotations

from typing import Any

from crisp.repro.hashing import sha256_json
from crisp.v3.contracts import BridgeComparatorOptions, SidecarOptions

SEMANTIC_POLICY_VERSION = "crisp.v3.semantic_policy/rev3-sidecar-first"
OBSERVATION_BUNDLE_SCHEMA_VERSION = "crisp.v3.observation_bundle/v1"
SIDECAR_RUN_RECORD_SCHEMA_VERSION = "crisp.v3.sidecar_run_record/v1"
GENERATOR_MANIFEST_SCHEMA_VERSION = "crisp.v3.generator_manifest/v1"
BUILDER_PROVENANCE_SCHEMA_VERSION = "crisp.v3.builder_provenance/v1"
VERDICT_RECORD_SCHEMA_VERSION = "crisp.v3.verdict_record/v1"
SHADOW_STABILITY_CAMPAIGN_SCHEMA_VERSION = "crisp.v3.shadow_stability_campaign/v1"
VN06_READINESS_SCHEMA_VERSION = "crisp.v3.vn06_readiness/v1"
PATH_CHANNEL_NAME = "path"
PATH_CHANNEL_FAMILY = "TUNNEL"
SCV_BRIDGE_POLICY = "crisp.v3.scv_bridge/v1"
DEFAULT_SIDECAR_OPTIONS = SidecarOptions()
DEFAULT_BRIDGE_COMPARATOR_OPTIONS = BridgeComparatorOptions()


def semantic_policy_payload() -> dict[str, Any]:
    return {
        "semantic_policy_version": SEMANTIC_POLICY_VERSION,
        "mode": "sidecar-first",
        "final_verdict_emitted": False,
        "contracts": {
            "scv_only_returns_verdicts": True,
            "channel_evidence_returns_verdicts": False,
            "scv_bridge_is_routing_shell": True,
        },
        "channels": {
            PATH_CHANNEL_NAME: {
                "formal_families": [PATH_CHANNEL_FAMILY],
                "evidence_state_mapping": {
                    "SUPPORTED": "PASS",
                    "REFUTED": "FAIL",
                    "INSUFFICIENT": "UNCLEAR",
                },
                "goal_precheck_failure_handling": "run_level_diagnostic_only",
                "persistence_confidence_handling": "record_only_not_a_gate",
            },
            "cap": {
                "formal_families": ["CAP"],
                "enabled_by_default": False,
                "validation_state_mapping": {
                    "VALIDATED": "PASS",
                    "PROVISIONAL": "UNCLEAR",
                    "REJECTED": "FAIL",
                },
                "materialization_policy": "read_only_snapshot_opt_in",
                "truth_source_handling": "read_only_pair_features_snapshot_not_final_verdict",
            },
            "catalytic": {
                "formal_families": ["CATALYTIC"],
                "enabled_by_default": False,
                "constraint_state_mapping": {
                    "SATISFIED": "PASS",
                    "PARTIAL": "UNCLEAR",
                    "VIOLATED": "FAIL",
                },
                "materialization_policy": "read_only_snapshot_opt_in",
                "truth_source_handling": "read_only_evidence_core_snapshot_not_final_verdict",
                "forbidden_scope": [
                    "proposal_connected_rule3",
                    "same_pose_requirement",
                    "corescv_reverse_flow",
                    "taxonomy_redesign",
                ],
            },
        },
    }


def parse_sidecar_options(integrated: dict[str, Any]) -> SidecarOptions:
    raw_options = integrated.get("v3_sidecar")
    if raw_options is None:
        return DEFAULT_SIDECAR_OPTIONS
    if isinstance(raw_options, bool):
        return SidecarOptions(enabled=raw_options, output_dirname=DEFAULT_SIDECAR_OPTIONS.output_dirname)
    if not isinstance(raw_options, dict):
        raise TypeError(
            f"integrated config v3_sidecar must be a mapping or bool, got {type(raw_options).__name__}"
        )

    enabled_raw = raw_options.get("enabled", False)
    output_dirname_raw = raw_options.get("output_dirname", DEFAULT_SIDECAR_OPTIONS.output_dirname)
    channels_raw = raw_options.get("channels", {})

    if not isinstance(enabled_raw, bool):
        raise TypeError("integrated config v3_sidecar.enabled must be a boolean")
    if not isinstance(output_dirname_raw, str) or not output_dirname_raw.strip():
        raise TypeError("integrated config v3_sidecar.output_dirname must be a non-empty string")
    if channels_raw is None:
        channels_raw = {}
    if not isinstance(channels_raw, dict):
        raise TypeError("integrated config v3_sidecar.channels must be a mapping when present")

    cap_enabled = False
    if "cap" in channels_raw:
        cap_raw = channels_raw["cap"]
        if isinstance(cap_raw, bool):
            cap_enabled = cap_raw
        elif isinstance(cap_raw, dict):
            cap_enabled_raw = cap_raw.get("enabled", False)
            if not isinstance(cap_enabled_raw, bool):
                raise TypeError("integrated config v3_sidecar.channels.cap.enabled must be a boolean")
            cap_enabled = cap_enabled_raw
        else:
            raise TypeError("integrated config v3_sidecar.channels.cap must be a mapping or bool")

    catalytic_enabled = False
    if "catalytic" in channels_raw:
        catalytic_raw = channels_raw["catalytic"]
        if isinstance(catalytic_raw, bool):
            catalytic_enabled = catalytic_raw
        elif isinstance(catalytic_raw, dict):
            catalytic_enabled_raw = catalytic_raw.get("enabled", False)
            if not isinstance(catalytic_enabled_raw, bool):
                raise TypeError("integrated config v3_sidecar.channels.catalytic.enabled must be a boolean")
            catalytic_enabled = catalytic_enabled_raw
        else:
            raise TypeError("integrated config v3_sidecar.channels.catalytic must be a mapping or bool")

    return SidecarOptions(
        enabled=enabled_raw,
        output_dirname=output_dirname_raw.strip(),
        cap_enabled=cap_enabled,
        catalytic_enabled=catalytic_enabled,
    )


def parse_bridge_comparator_options(integrated: dict[str, Any]) -> BridgeComparatorOptions:
    raw_options = integrated.get("v3_bridge_comparator")
    if raw_options is None:
        return DEFAULT_BRIDGE_COMPARATOR_OPTIONS
    if isinstance(raw_options, bool):
        return BridgeComparatorOptions(enabled=raw_options)
    if not isinstance(raw_options, dict):
        raise TypeError(
            f"integrated config v3_bridge_comparator must be a mapping or bool, got {type(raw_options).__name__}"
        )

    enabled_raw = raw_options.get("enabled", False)
    if not isinstance(enabled_raw, bool):
        raise TypeError("integrated config v3_bridge_comparator.enabled must be a boolean")
    return BridgeComparatorOptions(enabled=enabled_raw)


def expected_output_digest_payload(outputs: list[dict[str, Any]]) -> str:
    return sha256_json({"outputs": outputs})
