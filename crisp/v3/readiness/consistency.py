from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

REQUIRED_TRUTH_SOURCE_FIELDS = (
    "source_label",
    "source_digest",
    "source_location_kind",
    "builder_identity",
    "projector_identity",
    "observation_artifact_pointer",
)

TRUTH_SOURCE_RECONSTRUCTION_SCHEMA_VERSION = "crisp.v3.truth_source_reconstruction/v1"
SIDECAR_INVENTORY_SOURCE = "v3_sidecar/generator_manifest.json"
SIDECAR_INVENTORY_ENUMERATION = "generator_manifest.outputs"
RC2_INVENTORY_SOURCE = "output_inventory.json"
RC2_INVENTORY_ENUMERATION = "output_inventory.generated_outputs"


def build_inventory_authority_payload(*, rc2_output_inventory_mutated: bool) -> dict[str, Any]:
    return {
        "sidecar_inventory_source": SIDECAR_INVENTORY_SOURCE,
        "sidecar_outputs_authority": SIDECAR_INVENTORY_ENUMERATION,
        "sidecar_truth_source_authority": (
            "builder_provenance.json + sidecar_run_record.json + generator_manifest.json"
        ),
        "operator_report_enumeration_authority": SIDECAR_INVENTORY_ENUMERATION,
        "rc2_inventory_source": RC2_INVENTORY_SOURCE,
        "rc2_outputs_authority": RC2_INVENTORY_ENUMERATION,
        "rc2_inventory_mutated": rc2_output_inventory_mutated,
    }


def find_truth_source_stage(
    truth_source_chain: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    stage_name: str,
) -> dict[str, Any]:
    for item in truth_source_chain:
        if str(item.get("stage")) == stage_name:
            return dict(item)
    return {}


def derive_truth_source_record(channel_record: Mapping[str, Any] | None) -> dict[str, Any]:
    if not channel_record:
        return {}
    if any(field_name in channel_record for field_name in REQUIRED_TRUTH_SOURCE_FIELDS):
        return {
            field_name: channel_record.get(field_name)
            for field_name in REQUIRED_TRUTH_SOURCE_FIELDS
        } | {
            "channel_evidence_artifact_pointer": channel_record.get("channel_evidence_artifact_pointer"),
            "input_source_kind": channel_record.get("input_source_kind"),
            "truth_source_kind": channel_record.get("truth_source_kind"),
        }
    truth_source_chain_raw = channel_record.get("truth_source_chain")
    if not isinstance(truth_source_chain_raw, (list, tuple)):
        return {}
    truth_source_chain = [
        dict(item)
        for item in truth_source_chain_raw
        if isinstance(item, Mapping)
    ]
    input_stage = find_truth_source_stage(truth_source_chain, "input_snapshot")
    builder_stage = find_truth_source_stage(truth_source_chain, "channel_builder")
    bridge_stage = find_truth_source_stage(truth_source_chain, "bridge_route")
    return {
        "source_label": input_stage.get("source_label"),
        "source_digest": input_stage.get("source_digest"),
        "source_location_kind": input_stage.get("source_location_kind"),
        "builder_identity": builder_stage.get("builder"),
        "projector_identity": builder_stage.get("projector"),
        "observation_artifact_pointer": bridge_stage.get("observation_artifact"),
        "channel_evidence_artifact_pointer": (
            builder_stage.get("channel_evidence_artifact")
            or channel_record.get("channel_evidence_artifact")
        ),
        "input_source_kind": input_stage.get("kind"),
        "truth_source_kind": channel_record.get("truth_source_kind"),
    }


def _descriptor_claim(descriptor: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not descriptor:
        return None
    return {
        "relative_path": descriptor.get("relative_path"),
        "layer": descriptor.get("layer"),
        "content_type": descriptor.get("content_type"),
        "sha256": descriptor.get("sha256"),
        "byte_count": descriptor.get("byte_count"),
    }


def _manifest_output_index(generator_manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("relative_path")): dict(item)
        for item in generator_manifest.get("outputs", [])
        if isinstance(item, Mapping)
    }


def _manifest_duplicate_relative_paths(generator_manifest: Mapping[str, Any]) -> tuple[str, ...]:
    relative_paths = [
        str(item.get("relative_path"))
        for item in generator_manifest.get("outputs", [])
        if isinstance(item, Mapping) and item.get("relative_path") is not None
    ]
    counts = Counter(relative_paths)
    return tuple(sorted(path for path, count in counts.items() if count > 1))


def reconstruct_truth_source_claims(
    *,
    builder_provenance: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
    generator_manifest: Mapping[str, Any],
    channel_ids: tuple[str, ...] = ("path", "cap", "catalytic"),
) -> dict[str, dict[str, Any]]:
    provenance_channels = builder_provenance.get("channels", {})
    run_record_channels = sidecar_run_record.get("channel_records", {})
    manifest_outputs = _manifest_output_index(generator_manifest)
    manifest_duplicate_relative_paths = _manifest_duplicate_relative_paths(generator_manifest)
    reconstructed: dict[str, dict[str, Any]] = {}
    for channel_id in channel_ids:
        provenance_channel = provenance_channels.get(channel_id, {})
        run_record_channel = run_record_channels.get(channel_id, {})
        derived = derive_truth_source_record(provenance_channel)
        observation_artifact_pointer = derived.get("observation_artifact_pointer")
        channel_evidence_artifact_pointer = derived.get("channel_evidence_artifact_pointer")
        builder_status = run_record_channel.get("builder_status")
        channel_state = run_record_channel.get("channel_state")
        observation_present = bool(run_record_channel.get("observation_present"))
        required_fields_complete = all(
            derived.get(field_name)
            for field_name in REQUIRED_TRUTH_SOURCE_FIELDS
        )
        observation_artifact_unique = (
            observation_artifact_pointer is not None
            and str(observation_artifact_pointer) not in manifest_duplicate_relative_paths
            and str(observation_artifact_pointer) in manifest_outputs
        )
        channel_evidence_artifact_unique = (
            channel_evidence_artifact_pointer is not None
            and str(channel_evidence_artifact_pointer) not in manifest_duplicate_relative_paths
            and str(channel_evidence_artifact_pointer) in manifest_outputs
        )
        builder_status_matches = (
            provenance_channel.get("builder_status") == builder_status
        )
        channel_state_matches = (
            provenance_channel.get("channel_state") == channel_state
        )
        observation_present_matches = (
            bool(provenance_channel.get("observation_present")) == observation_present
        )
        reconstructed[channel_id] = {
            "schema_version": TRUTH_SOURCE_RECONSTRUCTION_SCHEMA_VERSION,
            "channel_id": channel_id,
            "source_label": derived.get("source_label"),
            "source_digest": derived.get("source_digest"),
            "source_location_kind": derived.get("source_location_kind"),
            "builder_identity": derived.get("builder_identity"),
            "projector_identity": derived.get("projector_identity"),
            "observation_artifact_pointer": observation_artifact_pointer,
            "channel_evidence_artifact_pointer": channel_evidence_artifact_pointer,
            "input_source_kind": derived.get("input_source_kind"),
            "truth_source_kind": run_record_channel.get("truth_source_kind", derived.get("truth_source_kind")),
            "builder_status": run_record_channel.get("builder_status"),
            "channel_state": run_record_channel.get("channel_state"),
            "observation_present": bool(run_record_channel.get("observation_present")),
            "required_fields_complete": required_fields_complete,
            "truth_source_chain_matches": (
                run_record_channel.get("truth_source_chain") == provenance_channel.get("truth_source_chain")
            ),
            "builder_status_matches": builder_status_matches,
            "channel_state_matches": channel_state_matches,
            "observation_present_matches": observation_present_matches,
            "observation_artifact_unique": observation_artifact_unique,
            "channel_evidence_artifact_unique": channel_evidence_artifact_unique,
            "manifest_duplicate_relative_paths": list(manifest_duplicate_relative_paths),
            "observation_artifact_descriptor": _descriptor_claim(
                manifest_outputs.get(str(observation_artifact_pointer))
            ),
            "channel_evidence_artifact_descriptor": _descriptor_claim(
                manifest_outputs.get(str(channel_evidence_artifact_pointer))
            ),
            "manifest_expected_output_digest": generator_manifest.get("expected_output_digest"),
            "reconstruction_complete": (
                required_fields_complete
                and builder_status_matches
                and channel_state_matches
                and observation_present_matches
                and observation_artifact_unique
                and channel_evidence_artifact_unique
                and not manifest_duplicate_relative_paths
            ),
        }
    return reconstructed


def audit_inventory_authority_split(
    *,
    readiness: Mapping[str, Any],
    output_inventory: Mapping[str, Any],
) -> tuple[str, ...]:
    findings: list[str] = []
    inventory_authority = readiness.get("inventory_authority", {})
    expected = build_inventory_authority_payload(rc2_output_inventory_mutated=False)
    for field_name, expected_value in expected.items():
        if inventory_authority.get(field_name) != expected_value:
            findings.append(f"inventory_authority {field_name} mismatch")
    generated_outputs = output_inventory.get("generated_outputs", [])
    if not isinstance(generated_outputs, list):
        findings.append("output_inventory generated_outputs is not a list")
        return tuple(findings)
    for relative_path in generated_outputs:
        if str(relative_path).startswith("v3_sidecar/"):
            findings.append(f"output_inventory enumerates sidecar artifact: {relative_path}")
    return tuple(findings)
