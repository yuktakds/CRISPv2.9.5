from __future__ import annotations

from typing import Any, Iterable, Mapping

from crisp.v3.readiness.consistency import build_inventory_authority_payload

EXPLORATORY_OPERATOR_ARTIFACTS = ("bridge_operator_summary.md",)


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

    for section in sections:
        semantic_source = section.get("semantic_source")
        label = str(section.get("label", ""))

        if semantic_source == "mixed":
            raise ReportGuardError("mixed semantic source is forbidden")

        if semantic_source == "v3" and "[exploratory]" not in label:
            raise ReportGuardError("v3 section must carry [exploratory] label")

        if semantic_source == "rc2" and "[exploratory]" in label:
            raise ReportGuardError("rc2 primary section must not carry [exploratory] label")


def guarded_operator_artifacts(*, bridge_comparator_enabled: bool) -> tuple[str, ...]:
    return EXPLORATORY_OPERATOR_ARTIFACTS if bridge_comparator_enabled else ()


def render_guarded_exploratory_report(
    *,
    artifact_name: str,
    metadata: Mapping[str, Any],
    sections: Iterable[Mapping[str, Any]],
    lines: Iterable[str],
) -> str:
    if artifact_name not in EXPLORATORY_OPERATOR_ARTIFACTS:
        raise ReportGuardError(f"unknown operator-facing artifact: {artifact_name}")
    enforce_inventory_authority_split(metadata=metadata)
    enforce_exploratory_report_guard(metadata=metadata, sections=sections)
    return "\n".join(lines) + "\n"
