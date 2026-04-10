from __future__ import annotations

from typing import Any, Mapping

from crisp.v3.preconditions_types import ARTIFACT_GENERATOR_IDS, ArtifactSectionReference


def _artifact_generator_id(artifact_name: str) -> str:
    return ARTIFACT_GENERATOR_IDS.get(artifact_name, "v3.unknown_artifact/v1")


def _artifact_ref(artifact_name: str, *, section_id: str) -> ArtifactSectionReference:
    return ArtifactSectionReference(
        artifact_name=artifact_name,
        generator_id=_artifact_generator_id(artifact_name),
        section_id=section_id,
    )


def _validate_artifact_ref(
    *,
    ref: Mapping[str, Any] | None,
    expected_artifact_name: str | None,
    expected_section_id: str | None,
    finding_prefix: str,
) -> list[str]:
    findings: list[str] = []
    if not isinstance(ref, Mapping):
        return [f"{finding_prefix} artifact reference is missing"]
    artifact_name = ref.get("artifact_name")
    generator_id = ref.get("generator_id")
    section_id = ref.get("section_id")
    if not artifact_name:
        findings.append(f"{finding_prefix} artifact_name is missing")
    if not generator_id:
        findings.append(f"{finding_prefix} generator_id is missing")
    if not section_id:
        findings.append(f"{finding_prefix} section_id is missing")
    if expected_artifact_name is not None and artifact_name != expected_artifact_name:
        findings.append(f"{finding_prefix} artifact_name mismatch")
    if artifact_name and generator_id and generator_id != _artifact_generator_id(str(artifact_name)):
        findings.append(f"{finding_prefix} generator_id mismatch")
    if expected_section_id is not None and section_id != expected_section_id:
        findings.append(f"{finding_prefix} section_id mismatch")
    return findings


def _descriptor_claim(descriptor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relative_path": descriptor.get("relative_path"),
        "layer": descriptor.get("layer"),
        "content_type": descriptor.get("content_type"),
        "sha256": descriptor.get("sha256"),
        "byte_count": descriptor.get("byte_count"),
    }
