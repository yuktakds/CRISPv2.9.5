from __future__ import annotations

from dataclasses import asdict

from crisp.v3.contracts import BridgeComparisonResult


def build_bridge_comparison_summary_payload(result: BridgeComparisonResult) -> dict[str, object]:
    return {
        **asdict(result.summary),
        "drift_count": len(result.drifts),
        "drift_kinds": sorted({drift.drift_kind for drift in result.drifts}),
    }


def build_bridge_drift_rows(result: BridgeComparisonResult) -> list[dict[str, object]]:
    return [asdict(drift) for drift in result.drifts]


def build_bridge_operator_summary(result: BridgeComparisonResult) -> str:
    summary = result.summary
    lines = [
        "# Bridge Operator Summary",
        "",
        f"- semantic_policy_version: `{summary.semantic_policy_version}`",
        f"- comparison_scope: `{summary.comparison_scope.value}`",
        f"- verdict_comparability: `{summary.verdict_comparability.value}`",
        f"- rc2_reference_kind: `{summary.rc2_reference_kind}`",
        f"- v3_shadow_kind: `{summary.v3_shadow_kind}`",
        f"- comparable_channels: `{', '.join(summary.comparable_channels) if summary.comparable_channels else 'none'}`",
        f"- unavailable_channels: `{', '.join(summary.unavailable_channels) if summary.unavailable_channels else 'none'}`",
        f"- run_level_flags: `{', '.join(summary.run_level_flags) if summary.run_level_flags else 'none'}`",
        "",
        "This report is exploratory only. It does not publish a final verdict and it does not change rc2 meaning.",
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
    return "\n".join(lines) + "\n"

