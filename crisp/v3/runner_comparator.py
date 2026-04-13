from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from crisp.v3.adapters.rc2_bridge import RC2BridgeAdapter
from crisp.v3.artifacts.sink import ArtifactSink
from crisp.v3.bridge.comparator import BridgeComparator
from crisp.v3.contracts import SCVObservationBundle, SidecarSnapshot
from crisp.v3.current_public_scope import CURRENT_PUBLIC_COMPARATOR_SCOPE
from crisp.v3.policy import (
    CAP_CHANNEL_NAME,
    CATALYTIC_CHANNEL_NAME,
    PATH_CHANNEL_NAME,
    SEMANTIC_POLICY_VERSION,
)
from crisp.v3.promotion_gates import (
    REQUIRED_CI_CANDIDACY_REPORT_ARTIFACT,
    emit_required_ci_candidacy_report,
    evaluate_np_exclusions,
    evaluate_pr_gates,
    evaluate_vn_gates,
)
from crisp.v3.reports.bridge_summary import (
    build_bridge_comparison_summary_payload,
    build_bridge_drift_rows,
    build_bridge_operator_summary,
)


@dataclass(frozen=True, slots=True)
class ComparatorExecutionState:
    comparison_summary_payload: dict[str, Any] | None = None
    run_drift_report_payload: dict[str, Any] | None = None
    channel_comparability: dict[str, Any] = field(
        default_factory=lambda: {
            PATH_CHANNEL_NAME: None,
            CAP_CHANNEL_NAME: None,
            CATALYTIC_CHANNEL_NAME: None,
        }
    )
    path_component_match: bool | None = None
    comparable_channels: list[str] = field(default_factory=list)
    v3_only_evidence_channels: list[str] = field(default_factory=list)


def empty_comparator_execution() -> ComparatorExecutionState:
    return ComparatorExecutionState()


def run_bridge_comparator(
    *,
    snapshot: SidecarSnapshot,
    bundle: SCVObservationBundle,
    sink: ArtifactSink,
    emit_debug_artifacts: bool,
) -> ComparatorExecutionState:
    adapter = RC2BridgeAdapter()
    rc2_adapt_result = adapter.adapt_path_only(
        run_id=snapshot.run_id,
        config=snapshot.config,
        pat_diagnostics_path=snapshot.pat_diagnostics_path,
        pathyes_force_false=snapshot.pathyes_force_false_requested,
    )
    comparison_result = BridgeComparator().compare(
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        rc2_adapt_result=rc2_adapt_result,
        v3_bundle=bundle,
    )
    comparison_summary_payload = build_bridge_comparison_summary_payload(comparison_result)
    run_drift_report_payload = asdict(comparison_result.run_report)
    channel_comparability = {
        PATH_CHANNEL_NAME: comparison_result.summary.channel_comparability.get(PATH_CHANNEL_NAME),
        CAP_CHANNEL_NAME: None,
        CATALYTIC_CHANNEL_NAME: None,
    }

    sink.write_json("bridge_comparison_summary.json", comparison_summary_payload, layer="layer1")
    if emit_debug_artifacts:
        sink.write_json("run_drift_report.json", run_drift_report_payload, layer="layer1")
    sink.write_jsonl(
        "bridge_drift_attribution.jsonl",
        build_bridge_drift_rows(comparison_result),
        layer="layer1",
    )
    sink.write_text(
        "bridge_operator_summary.md",
        build_bridge_operator_summary(comparison_result),
        layer="layer1",
        content_type="text/markdown; charset=utf-8",
    )

    pr_gates = evaluate_pr_gates(
        comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
        channel_name=PATH_CHANNEL_NAME,
        channel_contract_complete=True,
        sidecar_invariant_window=[True] * 30,
        baseline_value=comparison_result.run_report.path_component_match_rate,
        metrics_drift_window=[comparison_result.run_report.metrics_drift_count] * 30,
        windows_ci_window=[True] * 30,
        rc2_frozen_regression_green=True,
    )
    vn_gates = evaluate_vn_gates(
        full_scv_mapping_frozen=False,
        all_mapped_components_generated=False,
        all_projectors_integrated=False,
        formal_contracts_complete=False,
        sidecar_invariant_30_green=True,
        verdict_record_migration_complete=True,
    )
    np_exclusions = evaluate_np_exclusions(
        channel_name=PATH_CHANNEL_NAME,
        has_rc2_component_mapping=True,
        channel_contract_complete=True,
        baseline_met=(comparison_result.run_report.path_component_match_rate or 0.0) >= 0.95,
        windows_stable=True,
    )
    sink.write_json(
        REQUIRED_CI_CANDIDACY_REPORT_ARTIFACT,
        emit_required_ci_candidacy_report(
            comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
            channel_name=PATH_CHANNEL_NAME,
            pr_gates=pr_gates,
            vn_gates=vn_gates,
            np_exclusions=np_exclusions,
        ),
        layer="layer1",
    )

    return ComparatorExecutionState(
        comparison_summary_payload=comparison_summary_payload,
        run_drift_report_payload=run_drift_report_payload,
        channel_comparability=channel_comparability,
        path_component_match=comparison_result.summary.component_matches.get(PATH_CHANNEL_NAME),
        comparable_channels=list(comparison_result.summary.comparable_channels),
        v3_only_evidence_channels=list(comparison_result.summary.v3_only_evidence_channels),
    )
