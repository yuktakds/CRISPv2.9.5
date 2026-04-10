from __future__ import annotations

from typing import Any, Mapping

from crisp.v3.policy import VERDICT_RECORD_SCHEMA_VERSION

M1_LAYER0_AUTHORITY_MODE = "M1"
CANONICAL_LAYER0_AUTHORITY_ARTIFACT = "verdict_record.json"
SIDECAR_RUN_RECORD_ARTIFACT = "sidecar_run_record.json"
GENERATOR_MANIFEST_ARTIFACT = "generator_manifest.json"
LAYER0_AUTHORITY_MODE = "M2"
VERDICT_RECORD_ROLE = "canonical_layer0_authority"
SIDECAR_RUN_RECORD_ROLE = "backward_compatible_mirror"
M1_SIDECAR_RUN_RECORD_ROLE = "canonical_layer0_authority"
TRANSFERRED_AUTHORITY_FIELDS = (
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
)


def build_verdict_record_authority_fields(
    *,
    run_id: str,
    output_root: str,
    semantic_policy_version: str,
    comparator_scope: str | None,
    comparable_channels: list[str],
    v3_only_evidence_channels: list[str],
    channel_lifecycle_states: dict[str, str],
    full_verdict_computable: bool,
    full_verdict_comparable_count: int,
    verdict_match_rate: float | None,
    verdict_mismatch_rate: float | None,
    path_component_match_rate: float | None,
    v3_shadow_verdict: str | None,
    authority_transfer_complete: bool,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "output_root": output_root,
        "semantic_policy_version": semantic_policy_version,
        "comparator_scope": comparator_scope,
        "comparable_channels": list(comparable_channels),
        "v3_only_evidence_channels": list(v3_only_evidence_channels),
        "channel_lifecycle_states": dict(channel_lifecycle_states),
        "full_verdict_computable": bool(full_verdict_computable),
        "full_verdict_comparable_count": int(full_verdict_comparable_count),
        "verdict_match_rate": verdict_match_rate,
        "verdict_mismatch_rate": verdict_mismatch_rate,
        "path_component_match_rate": path_component_match_rate,
        "v3_shadow_verdict": v3_shadow_verdict,
        "authority_transfer_complete": bool(authority_transfer_complete),
    }


def build_verdict_record_payload(
    *,
    authority_fields: Mapping[str, Any],
    sidecar_run_record_artifact: str = SIDECAR_RUN_RECORD_ARTIFACT,
    generator_manifest_artifact: str = GENERATOR_MANIFEST_ARTIFACT,
) -> dict[str, Any]:
    return {
        "schema_version": VERDICT_RECORD_SCHEMA_VERSION,
        **{field_name: authority_fields.get(field_name) for field_name in TRANSFERRED_AUTHORITY_FIELDS},
        "sidecar_run_record_artifact": sidecar_run_record_artifact,
        "generator_manifest_artifact": generator_manifest_artifact,
    }


def build_sidecar_layer0_authority_metadata(
    *,
    verdict_record_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "layer0_authority_artifact": CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
        "layer0_authority_mode": LAYER0_AUTHORITY_MODE,
        "verdict_record_role": VERDICT_RECORD_ROLE,
        "sidecar_run_record_role": SIDECAR_RUN_RECORD_ROLE,
        "layer0_authority_mirror": {
            field_name: verdict_record_payload.get(field_name)
            for field_name in TRANSFERRED_AUTHORITY_FIELDS
        },
    }


def extract_sidecar_layer0_authority_mirror(
    sidecar_run_record: Mapping[str, Any],
) -> dict[str, Any]:
    bridge_diagnostics = sidecar_run_record.get("bridge_diagnostics") or {}
    if not isinstance(bridge_diagnostics, Mapping):
        return {}
    mirror = bridge_diagnostics.get("layer0_authority_mirror") or {}
    return dict(mirror) if isinstance(mirror, Mapping) else {}


def sidecar_layer0_authority_artifact(sidecar_run_record: Mapping[str, Any]) -> str | None:
    bridge_diagnostics = sidecar_run_record.get("bridge_diagnostics") or {}
    if not isinstance(bridge_diagnostics, Mapping):
        return None
    artifact = bridge_diagnostics.get("layer0_authority_artifact")
    return None if artifact is None else str(artifact)


def sidecar_layer0_authority_mode(sidecar_run_record: Mapping[str, Any]) -> str | None:
    bridge_diagnostics = sidecar_run_record.get("bridge_diagnostics") or {}
    if not isinstance(bridge_diagnostics, Mapping):
        return None
    mode = bridge_diagnostics.get("layer0_authority_mode")
    return None if mode is None else str(mode)


def sidecar_run_record_role(sidecar_run_record: Mapping[str, Any]) -> str | None:
    bridge_diagnostics = sidecar_run_record.get("bridge_diagnostics") or {}
    if not isinstance(bridge_diagnostics, Mapping):
        return None
    role = bridge_diagnostics.get("sidecar_run_record_role")
    return None if role is None else str(role)
