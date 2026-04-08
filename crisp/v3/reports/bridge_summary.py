from __future__ import annotations

from dataclasses import asdict

from crisp.v3.contracts import BridgeComparisonResult
from crisp.v3.contracts.bridge_header import BridgeHeader
from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.report_guards import render_guarded_exploratory_report

_RC2_POLICY_VERSION = "v2.9.5-rc2"
BRIDGE_OPERATOR_SUMMARY_ARTIFACT = "bridge_operator_summary.md"


def build_bridge_header(result: BridgeComparisonResult) -> BridgeHeader:
    summary = result.summary
    comparator_scope = (
        "path_only_partial"
        if summary.comparison_scope.value == "path_only_partial"
        else "full_bridge"
    )
    verdict_comparability = (
        "fully_comparable"
        if summary.verdict_comparability.value == "comparable"
        else summary.verdict_comparability.value
    )
    return BridgeHeader(
        semantic_policy_version=summary.semantic_policy_version,
        comparator_scope=comparator_scope,
        verdict_comparability=verdict_comparability,
        comparable_channels=summary.comparable_channels,
        rc2_policy_version=_RC2_POLICY_VERSION,
    )


def build_bridge_comparison_summary_payload(result: BridgeComparisonResult) -> dict[str, object]:
    header = build_bridge_header(result)
    return {
        **asdict(result.summary),
        "bridge_header": header.to_dict(),
        "drift_count": len(result.drifts),
        "drift_kinds": sorted({drift.drift_kind for drift in result.drifts}),
    }


def build_bridge_drift_rows(result: BridgeComparisonResult) -> list[dict[str, object]]:
    return [asdict(drift) for drift in result.drifts]


def build_bridge_operator_summary(result: BridgeComparisonResult) -> str:
    summary = result.summary
    header = build_bridge_header(result)
    inventory_authority = build_inventory_authority_payload(rc2_output_inventory_mutated=False)
    lines = [
        "# [exploratory] Bridge Operator Summary",
        "",
        "## Comparator Header",
        "",
        f"- semantic_policy_version: `{header.semantic_policy_version}`",
        f"- comparator_scope: `{header.comparator_scope}`",
        f"- verdict_comparability: `{header.verdict_comparability}`",
        f"- comparable_channels: `{', '.join(header.comparable_channels) if header.comparable_channels else 'none'}`",
        f"- rc2_policy_version: `{header.rc2_policy_version or 'unknown'}`",
        f"- sidecar_inventory_source: `{inventory_authority['sidecar_inventory_source']}`",
        f"- sidecar_outputs_authority: `{inventory_authority['sidecar_outputs_authority']}`",
        f"- rc2_inventory_source: `{inventory_authority['rc2_inventory_source']}`",
        f"- rc2_outputs_authority: `{inventory_authority['rc2_outputs_authority']}`",
        "",
        "## Comparison Summary",
        "",
        f"- rc2_reference_kind: `{summary.rc2_reference_kind}`",
        f"- v3_shadow_kind: `{summary.v3_shadow_kind}`",
        f"- unavailable_channels: `{', '.join(summary.unavailable_channels) if summary.unavailable_channels else 'none'}`",
        f"- run_level_flags: `{', '.join(summary.run_level_flags) if summary.run_level_flags else 'none'}`",
        "",
        "This report is [exploratory] only. It does not publish a final verdict and it does not change rc2 meaning.",
        "Cap / Catalytic sidecar materialization does not widen the current Path-only comparability claim.",
        "",
        "## Channel Coverage",
        "",
    ]
    for channel_name, status in sorted(summary.channel_coverage.items()):
        lines.append(f"- {channel_name}: `{status}`")
    lines.extend(
        [
            "",
            "## Drift Counts",
            "",
            f"- total_drifts: `{len(result.drifts)}`",
        ]
    )
    if result.drifts:
        for drift_kind in sorted({drift.drift_kind for drift in result.drifts}):
            count = sum(1 for drift in result.drifts if drift.drift_kind == drift_kind)
            lines.append(f"- {drift_kind}: `{count}`")
    return render_guarded_exploratory_report(
        artifact_name=BRIDGE_OPERATOR_SUMMARY_ARTIFACT,
        metadata={
            "semantic_policy_version": header.semantic_policy_version,
            "verdict_comparability": header.verdict_comparability,
            "verdict_match_rate": None,
            "inventory_authority": inventory_authority,
        },
        sections=[
            {"semantic_source": "rc2", "label": "rc2 frozen reference"},
            {"semantic_source": "v3", "label": "[exploratory] v3 shadow summary"},
        ],
        lines=lines,
    )
