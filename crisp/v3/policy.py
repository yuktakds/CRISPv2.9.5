from __future__ import annotations

from typing import Any

from crisp.repro.hashing import sha256_json
from crisp.v3.contracts import SidecarOptions

SEMANTIC_POLICY_VERSION = "crisp.v3.semantic_policy/rev3-sidecar-first"
OBSERVATION_BUNDLE_SCHEMA_VERSION = "crisp.v3.observation_bundle/v1"
SIDECAR_RUN_RECORD_SCHEMA_VERSION = "crisp.v3.sidecar_run_record/v1"
GENERATOR_MANIFEST_SCHEMA_VERSION = "crisp.v3.generator_manifest/v1"
PATH_CHANNEL_NAME = "path"
PATH_CHANNEL_FAMILY = "TUNNEL"
SCV_BRIDGE_POLICY = "crisp.v3.scv_bridge/v1"
DEFAULT_SIDECAR_OPTIONS = SidecarOptions()


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
            }
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

    if not isinstance(enabled_raw, bool):
        raise TypeError("integrated config v3_sidecar.enabled must be a boolean")
    if not isinstance(output_dirname_raw, str) or not output_dirname_raw.strip():
        raise TypeError("integrated config v3_sidecar.output_dirname must be a non-empty string")

    return SidecarOptions(enabled=enabled_raw, output_dirname=output_dirname_raw.strip())


def expected_output_digest_payload(outputs: list[dict[str, Any]]) -> str:
    return sha256_json({"outputs": outputs})

