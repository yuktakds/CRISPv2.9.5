from __future__ import annotations

from dataclasses import asdict

from crisp.v3.contracts import BridgeComparisonResult
from crisp.v3.contracts.bridge_header import BridgeHeader
from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.report_guards import enforce_channel_semantics, render_guarded_exploratory_report

_RC2_POLICY_VERSION = "v2.9.5-rc2"
BRIDGE_OPERATOR_SUMMARY_ARTIFACT = "bridge_operator_summary.md"
_FINAL_VERDICT_FIELDS = {"v3_shadow_verdict", "verdict_match"}


def build_bridge_header(result: BridgeComparisonResult) -> BridgeHeader:
    summary = result.summary
    verdict_comparability = (
        "fully_comparable"
        if summary.verdict_comparability.value == "comparable"
        else summary.verdict_comparability.value
    )
    return BridgeHeader(
        semantic_policy_version=summary.semantic_policy_version,
        comparator_scope=summary.comparison_scope.value,
        verdict_comparability=verdict_comparability,
        comparable_channels=summary.comparable_channels,
        rc2_policy_version=_RC2_POLICY_VERSION,
    )


def build_bridge_comparison_summary_payload(result: BridgeComparisonResult) -> dict[str, object]:
    enforce_channel_semantics(
        comparable_channels=result.summary.comparable_channels,
        v3_only_evidence_channels=result.summary.v3_only_evidence_channels,
        component_matches=result.summary.component_matches,
        channel_lifecycle_states=result.summary.channel_lifecycle_states,
    )
    header = build_bridge_header(result)
    run_report = asdict(result.run_report)
    compound_reports = []
    for report in result.compound_reports:
        payload = asdict(report)
        for field_name in _FINAL_VERDICT_FIELDS:
            payload.pop(field_name, None)
        compound_reports.append(payload)
    return {
        **asdict(result.summary),
        "comparable_channels": list(result.summary.comparable_channels),
        "v3_only_evidence_channels": list(result.summary.v3_only_evidence_channels),
        "unavailable_channels": list(result.summary.unavailable_channels),
        "bridge_header": header.to_dict(),
        "run_drift_report": run_report,
        "compound_drift_reports": compound_reports,
        "drift_count": len(result.drifts),
        "drift_kinds": sorted({drift.drift_kind for drift in result.drifts}),
    }


def build_bridge_drift_rows(result: BridgeComparisonResult) -> list[dict[str, object]]:
    return [asdict(drift) for drift in result.drifts]


def _format_component_match_rate(result: BridgeComparisonResult) -> str:
    run_report = result.run_report
    if run_report.path_component_match_rate is None:
        return "N/A"
    numerator = run_report.component_match_count
    denominator = run_report.component_verdict_comparable_count
    percentage = run_report.path_component_match_rate * 100.0
    return f"{numerator}/{denominator} ({percentage:.1f}%)"


def _format_verdict_match_rate(result: BridgeComparisonResult) -> str:
    run_report = result.run_report
    if not run_report.full_verdict_computable or run_report.verdict_match_rate is None:
        return "N/A"
    numerator = run_report.verdict_match_count or 0
    denominator = run_report.full_verdict_comparable_count
    percentage = run_report.verdict_match_rate * 100.0
    return f"{numerator}/{denominator} ({percentage:.1f}%)"


def build_bridge_operator_summary(result: BridgeComparisonResult) -> str:
    summary = result.summary
    header = build_bridge_header(result)
    run_report = result.run_report
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
        (
            f"- v3_only_evidence_channels: `{', '.join(summary.v3_only_evidence_channels)}`"
            if summary.v3_only_evidence_channels
            else "- v3_only_evidence_channels: `none`"
        ),
        f"- rc2_policy_version: `{header.rc2_policy_version or 'unknown'}`",
        f"- verdict_match_rate: `{_format_verdict_match_rate(result)}`",
        f"- path_component_match_rate: `{_format_component_match_rate(result)}`",
        f"- comparable_subset_size: `{run_report.comparable_subset_size}`",
        f"- full_verdict_computable: `{str(run_report.full_verdict_computable).lower()}`",
        f"- full_verdict_comparable_count: `{run_report.full_verdict_comparable_count}`",
        f"- sidecar_inventory_source: `{inventory_authority['sidecar_inventory_source']}`",
        f"- sidecar_outputs_authority: `{inventory_authority['sidecar_outputs_authority']}`",
        f"- rc2_inventory_source: `{inventory_authority['rc2_inventory_source']}`",
        f"- rc2_outputs_authority: `{inventory_authority['rc2_outputs_authority']}`",
        "",
        "## Surface Contract",
        "",
        "- rc2 display role: `primary`",
        "- v3 display role: `[exploratory] secondary`",
        "",
        "## Comparison Summary",
        "",
        f"- rc2_reference_kind: `{summary.rc2_reference_kind}`",
        f"- v3_shadow_kind: `{summary.v3_shadow_kind}`",
        f"- unavailable_channels: `{', '.join(summary.unavailable_channels) if summary.unavailable_channels else 'none'}`",
        f"- run_level_flags: `{', '.join(summary.run_level_flags) if summary.run_level_flags else 'none'}`",
        "",
        "This report is [exploratory] only. It does not publish a final verdict and it does not change rc2 meaning.",
        (
            "Current public scope is path_and_catalytic_partial; "
            "catalytic remains unavailable until catalytic_rule3a public projection is emitted."
        ),
        "",
        "## Channel Coverage",
        "",
    ]
    for channel_name, status in sorted(summary.channel_coverage.items()):
        lines.append(f"- {channel_name}: `{status}`")
    if summary.v3_only_evidence_channels:
        lines.extend(
            [
                "",
                "## V3-only Evidence",
                "",
            ]
        )
        for channel_name in summary.v3_only_evidence_channels:
            lifecycle_state = summary.channel_lifecycle_states.get(channel_name, "unknown")
            lines.append(f"- [v3-only] {channel_name}: `{lifecycle_state}`")
    lines.extend(
        [
        "",
        "## Drift Counts",
        "",
        f"- total_drifts: `{len(result.drifts)}`",
        f"- coverage_drift_count: `{run_report.coverage_drift_count}`",
        f"- applicability_drift_count: `{run_report.applicability_drift_count}`",
        f"- metrics_drift_count: `{run_report.metrics_drift_count}`",
        f"- witness_drift_count: `{run_report.witness_drift_count}`",
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
            "verdict_match_rate": _format_verdict_match_rate(result),
            "v3_shadow_verdict": None,
            "comparable_channels": header.comparable_channels,
            "v3_only_evidence_channels": summary.v3_only_evidence_channels,
            "channel_lifecycle_states": summary.channel_lifecycle_states,
            "component_matches": summary.component_matches,
            "inventory_authority": inventory_authority,
        },
        sections=[
            {"semantic_source": "rc2", "label": "rc2 primary reference"},
            {"semantic_source": "v3", "label": "[exploratory] v3 secondary summary"},
        ],
        lines=lines,
    )
