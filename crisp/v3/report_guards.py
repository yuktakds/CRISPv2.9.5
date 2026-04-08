from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from crisp.v3.readiness.consistency import build_inventory_authority_payload


@dataclass(frozen=True, slots=True)
class OperatorSurfaceSpec:
    artifact_name: str
    title_label: str
    rc2_label_fragment: str = "primary"
    v3_label_fragment: str = "secondary"


OPERATOR_SURFACE_SPECS = {
    "bridge_operator_summary.md": OperatorSurfaceSpec(
        artifact_name="bridge_operator_summary.md",
        title_label="[exploratory] Bridge Operator Summary",
    )
}
EXPLORATORY_OPERATOR_ARTIFACTS = tuple(OPERATOR_SURFACE_SPECS)


class ReportGuardError(ValueError):
    pass


def enforce_inventory_authority_split(*, metadata: Mapping[str, Any]) -> None:
    inventory_authority = metadata.get("inventory_authority")
    if not isinstance(inventory_authority, Mapping):
        raise ReportGuardError("inventory_authority metadata is required")
    expected = build_inventory_authority_payload(rc2_output_inventory_mutated=False)
    for field_name, expected_value in expected.items():
        if inventory_authority.get(field_name) != expected_value:
            raise ReportGuardError(f"inventory_authority {field_name} mismatch")


def enforce_exploratory_report_guard(
    *,
    metadata: Mapping[str, Any],
    sections: Iterable[Mapping[str, Any]],
) -> None:
    semantic_policy_version = metadata.get("semantic_policy_version")
    if not semantic_policy_version:
        raise ReportGuardError("semantic_policy_version is required")

    verdict_comparability = metadata.get("verdict_comparability")
    verdict_match_rate = metadata.get("verdict_match_rate")
    if verdict_comparability != "fully_comparable" and verdict_match_rate not in (None, "N/A"):
        raise ReportGuardError(
            "verdict_match_rate must be None or 'N/A' when full verdict comparability is absent"
        )

    section_list = [dict(section) for section in sections]
    rc2_indices: list[int] = []
    v3_indices: list[int] = []
    for index, section in enumerate(section_list):
        semantic_source = section.get("semantic_source")
        label = str(section.get("label", ""))

        if semantic_source == "mixed":
            raise ReportGuardError("mixed semantic source is forbidden")
        if semantic_source not in {"rc2", "v3"}:
            raise ReportGuardError("unknown semantic source is forbidden")

        if semantic_source == "v3" and "[exploratory]" not in label:
            raise ReportGuardError("v3 section must carry [exploratory] label")
        if semantic_source == "v3" and "secondary" not in label.lower():
            raise ReportGuardError("v3 section must carry secondary label")

        if semantic_source == "rc2" and "[exploratory]" in label:
            raise ReportGuardError("rc2 primary section must not carry [exploratory] label")
        if semantic_source == "rc2" and "primary" not in label.lower():
            raise ReportGuardError("rc2 section must carry primary label")

        if semantic_source == "rc2":
            rc2_indices.append(index)
        if semantic_source == "v3":
            v3_indices.append(index)

    if not rc2_indices:
        raise ReportGuardError("rc2 primary section is required")
    if not v3_indices:
        raise ReportGuardError("v3 secondary section is required")
    if rc2_indices[0] != 0:
        raise ReportGuardError("rc2 primary section must be first")
    if max(rc2_indices) > min(v3_indices):
        raise ReportGuardError("v3 secondary sections must follow rc2 primary sections")


def guarded_operator_artifacts(*, bridge_comparator_enabled: bool) -> tuple[str, ...]:
    return EXPLORATORY_OPERATOR_ARTIFACTS if bridge_comparator_enabled else ()


def render_guarded_exploratory_report(
    *,
    artifact_name: str,
    metadata: Mapping[str, Any],
    sections: Iterable[Mapping[str, Any]],
    lines: Iterable[str],
) -> str:
    surface_spec = OPERATOR_SURFACE_SPECS.get(artifact_name)
    if surface_spec is None:
        raise ReportGuardError(f"unknown operator-facing artifact: {artifact_name}")
    enforce_inventory_authority_split(metadata=metadata)
    enforce_exploratory_report_guard(metadata=metadata, sections=sections)
    rendered = "\n".join(lines) + "\n"
    if surface_spec.title_label not in rendered:
        raise ReportGuardError(f"{artifact_name} missing exploratory title label")
    if "semantic_policy_version" not in rendered:
        raise ReportGuardError(f"{artifact_name} must render semantic_policy_version")
    return rendered
