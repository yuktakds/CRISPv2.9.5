from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from crisp.v3.contracts import BridgeComparisonResult
from crisp.v3.contracts.bridge_header import BridgeHeader
from crisp.v3.current_public_scope import CATALYTIC_PUBLIC_COMPARABLE_COMPONENT
from crisp.v3.operator_surface_state import (
    PROMOTION_AUTHORITY_REFERENCE,
    build_operator_surface_state,
    suppression_reason_by_surface,
)
from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v3.report_guards import enforce_channel_semantics, render_guarded_exploratory_report
from crisp.v3.rp3_activation import ActivationUnit

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


def _format_numeric_rate(
    *,
    rate: float | None,
    numerator: int | None,
    denominator: int,
) -> str:
    if rate is None:
        return "N/A"
    percentage = rate * 100.0
    return f"{numerator or 0}/{denominator} ({percentage:.1f}%)"


def _format_verdict_match_rate(result: BridgeComparisonResult) -> str:
    run_report = result.run_report
    if not run_report.full_verdict_computable or run_report.verdict_match_rate is None:
        return "N/A"
    return _format_numeric_rate(
        rate=run_report.verdict_match_rate,
        numerator=run_report.verdict_match_count,
        denominator=run_report.full_verdict_comparable_count,
    )


def _format_verdict_mismatch_rate(result: BridgeComparisonResult) -> str:
    run_report = result.run_report
    if not run_report.full_verdict_computable or run_report.verdict_mismatch_rate is None:
        return "N/A"
    return _format_numeric_rate(
        rate=run_report.verdict_mismatch_rate,
        numerator=run_report.verdict_mismatch_count,
        denominator=run_report.full_verdict_comparable_count,
    )


def _format_component_match(component_match: bool | None) -> str:
    if component_match is None:
        return "N/A"
    return "match" if component_match else "mismatch"


def _promotion_lines(required_candidacy_payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(required_candidacy_payload, Mapping):
        return []
    pr_gates = required_candidacy_payload.get("pr_gates", {})
    if not isinstance(pr_gates, Mapping):
        pr_gates = {}
    failed_gate_ids = sorted(
        gate_id
        for gate_id, gate in pr_gates.items()
        if not (isinstance(gate, Mapping) and bool(gate.get("passed", False)))
    )
    return [
        "## [exploratory] Promotion Candidacy",
        "",
        f"- lane_id: `{required_candidacy_payload.get('channel_name', 'unknown')}`",
        (
            f"- promotion_candidate: "
            f"`{str(bool(required_candidacy_payload.get('promotion_candidate', False))).lower()}`"
        ),
        (
            f"- failed_pr_gates: "
            f"`{', '.join(failed_gate_ids) if failed_gate_ids else 'none'}`"
        ),
        f"- authority_reference: `{PROMOTION_AUTHORITY_REFERENCE}`",
        (
            f"- human_explicit_decision_required: "
            f"`{str(bool(required_candidacy_payload.get('human_explicit_decision_required', True))).lower()}`"
        ),
        (
            f"- required_matrix_mutation_allowed: "
            f"`{str(bool(required_candidacy_payload.get('required_matrix_mutation_allowed', False))).lower()}`"
        ),
        "",
    ]


def build_bridge_operator_summary(
    result: BridgeComparisonResult,
    *,
    activation_decisions: Mapping[str, Any] | None = None,
    vn_gates: Mapping[str, Mapping[str, Any]] | None = None,
    vn_gate_state: Mapping[str, Any] | None = None,
    denominator_contract_satisfied: bool = False,
    required_candidacy_payload: Mapping[str, Any] | None = None,
    v3_shadow_verdict: str | None = None,
) -> str:
    summary = result.summary
    header = build_bridge_header(result)
    run_report = result.run_report
    inventory_authority = build_inventory_authority_payload(rc2_output_inventory_mutated=False)
    operator_surface_state = build_operator_surface_state(
        activation_decisions=activation_decisions,
        vn_gates=vn_gates,
        vn_gate_state=vn_gate_state,
        full_verdict_computable=run_report.full_verdict_computable,
        denominator_contract_satisfied=denominator_contract_satisfied,
        required_candidacy_payload=required_candidacy_payload,
    )
    suppression_reasons = suppression_reason_by_surface(operator_surface_state)
    shadow_renderable = bool(operator_surface_state["v3_shadow_verdict_renderable"])
    numeric_rates_renderable = bool(operator_surface_state["numeric_verdict_rates_renderable"])
    rendered_shadow_verdict = v3_shadow_verdict if shadow_renderable and v3_shadow_verdict is not None else "N/A"
    rendered_verdict_match_rate = (
        _format_verdict_match_rate(result) if numeric_rates_renderable else "N/A"
    )
    rendered_verdict_mismatch_rate = (
        _format_verdict_mismatch_rate(result) if numeric_rates_renderable else "N/A"
    )
    normalized_activation_decisions = operator_surface_state["activation_decisions"]
    normalized_vn_gate_state = operator_surface_state["vn_gate_state"]
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
        f"- verdict_match_rate: `{rendered_verdict_match_rate}`",
        f"- verdict_mismatch_rate: `{rendered_verdict_mismatch_rate}`",
        f"- path_component_match_rate: `{_format_component_match_rate(result)}`",
        (
            f"- catalytic_rule3a_component_match: "
            f"`{_format_component_match(summary.component_matches.get(CATALYTIC_PUBLIC_COMPARABLE_COMPONENT))}`"
        ),
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
        "## [exploratory] Activation State",
        "",
        f"- shadow_verdict_rendering: `{'rendered' if shadow_renderable else 'suppressed'}`",
        (
            f"- shadow_verdict_suppression_reason: "
            f"`{suppression_reasons.get(ActivationUnit.V3_SHADOW_VERDICT.value, 'none')}`"
        ),
        (
            f"- numeric_verdict_rates_suppression_reason: "
            f"`{suppression_reasons.get(ActivationUnit.NUMERIC_VERDICT_RATES.value, 'none')}`"
        ),
        (
            f"- activation_decision.shadow_verdict: "
            f"`{str(normalized_activation_decisions[ActivationUnit.V3_SHADOW_VERDICT.value]).lower()}`"
        ),
        (
            f"- activation_decision.numeric_verdict_rates: "
            f"`{str(normalized_activation_decisions[ActivationUnit.NUMERIC_VERDICT_RATES.value]).lower()}`"
        ),
        f"- vn_gate_all_satisfied: `{str(normalized_vn_gate_state['all_satisfied']).lower()}`",
        f"- denominator_contract_satisfied: `{str(denominator_contract_satisfied).lower()}`",
        "",
        "## Comparison Summary",
        "",
        f"- rc2_reference_kind: `{summary.rc2_reference_kind}`",
        f"- v3_shadow_kind: `{summary.v3_shadow_kind}`",
        f"- unavailable_channels: `{', '.join(summary.unavailable_channels) if summary.unavailable_channels else 'none'}`",
        f"- run_level_flags: `{', '.join(summary.run_level_flags) if summary.run_level_flags else 'none'}`",
        "",
        "This report is [exploratory] only. It does not publish a final verdict and it does not change rc2 meaning.",
        "Path and catalytic component indicators remain component-level only; they are not verdict proxies.",
        "Catalytic public comparable surface is rendered as `catalytic_rule3a`; Rule3B remains [v3-only].",
        "",
        "## Channel Coverage",
        "",
    ]
    if shadow_renderable:
        lines.insert(lines.index("## Comparison Summary") - 1, f"- v3_shadow_verdict: `{rendered_shadow_verdict}`")
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
    lines.extend(_promotion_lines(required_candidacy_payload))
    lines.extend(
        [
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
            "verdict_match_rate": rendered_verdict_match_rate,
            "verdict_mismatch_rate": rendered_verdict_mismatch_rate,
            "v3_shadow_verdict": v3_shadow_verdict if shadow_renderable else None,
            "activation_decisions": normalized_activation_decisions,
            "vn_gate_state": normalized_vn_gate_state,
            "full_verdict_computable": run_report.full_verdict_computable,
            "denominator_contract_satisfied": denominator_contract_satisfied,
            "comparator_scope": header.comparator_scope,
            "comparable_channels": header.comparable_channels,
            "v3_only_evidence_channels": summary.v3_only_evidence_channels,
            "channel_lifecycle_states": summary.channel_lifecycle_states,
            "component_matches": summary.component_matches,
            "inventory_authority": inventory_authority,
        },
        sections=[
            {"semantic_source": "rc2", "label": "rc2 primary reference"},
            {"semantic_source": "v3", "label": "[exploratory] v3 secondary summary"},
            {"semantic_source": "v3", "label": "[exploratory] v3 secondary activation state"},
            {"semantic_source": "v3", "label": "[exploratory] v3 secondary promotion candidacy"},
        ],
        lines=lines,
    )
