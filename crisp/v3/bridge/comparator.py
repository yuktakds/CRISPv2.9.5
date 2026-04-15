"""Bridge comparator orchestration.

Path 比較、run-report 集計、結果整形は専用モジュールに委譲する。
このモジュールは public API と組み立てだけを担当する。
"""
from __future__ import annotations

from typing import Any

from crisp.v3.bridge.path_comparison import bundle_index, compare_path_channel
from crisp.v3.bridge.run_report import (
    build_run_report,
    compute_full_verdict_comparable_subset,
    guard_current_scope_no_full_aggregation,
    required_scv_components_frozen,
    resolve_denominators,
)
from crisp.v3.bridge.serialization import comparison_result_to_dict as _comparison_result_to_dict
from crisp.v3.contracts import (
    BridgeComparisonResult,
    BridgeComparisonSummary,
    ComparisonScope,
    CompoundPathComparability,
    RC2AdaptResult,
    SCVObservationBundle,
    VerdictComparability,
)
from crisp.v3.current_public_scope import (
    CATALYTIC_PUBLIC_COMPARABLE_COMPONENT,
    CURRENT_PUBLIC_COMPARABLE_CHANNELS,
    CURRENT_PUBLIC_COMPARATOR_SCOPE,
    derive_v3_only_evidence_channels,
)
from crisp.v3.policy import (
    CAP_CHANNEL_NAME,
    CATALYTIC_CHANNEL_NAME,
    PATH_CHANNEL_NAME,
)

_V3_SHADOW_KIND = "v3_sidecar_observation_bundle"
PARTIAL_SCOPE_COMPARATOR_CONTRACT_VERSION = "crisp.v3.bridge_comparator.partial_scope/v1"
PATH_ONLY_COMPARATOR_CONTRACT_VERSION = PARTIAL_SCOPE_COMPARATOR_CONTRACT_VERSION
_FINAL_VERDICT_FIELDS = {"v3_shadow_verdict", "verdict_match"}


def _channel_lifecycle_states(v3_bundle: SCVObservationBundle) -> dict[str, str]:
    v3_index = bundle_index(v3_bundle)
    return {
        PATH_CHANNEL_NAME: (
            "observation_materialized"
            if v3_index.get(PATH_CHANNEL_NAME) is not None
            else "applicability_only"
        ),
        CAP_CHANNEL_NAME: (
            "observation_materialized"
            if v3_index.get(CAP_CHANNEL_NAME) is not None
            else "applicability_only"
        ),
        CATALYTIC_CHANNEL_NAME: (
            "observation_materialized"
            if v3_index.get(CATALYTIC_CHANNEL_NAME) is not None
            else "applicability_only"
        ),
    }


class BridgeComparator:
    def compare(
        self,
        *,
        semantic_policy_version: str,
        rc2_adapt_result: RC2AdaptResult,
        v3_bundle: SCVObservationBundle,
    ) -> BridgeComparisonResult:
        rc2_bundle = rc2_adapt_result.bundle
        rc2_index = bundle_index(rc2_bundle)
        v3_index = bundle_index(v3_bundle)
        rc2_catalytic_observation = rc2_index.get(CATALYTIC_CHANNEL_NAME)
        v3_catalytic_observation = v3_index.get(CATALYTIC_CHANNEL_NAME)

        path_report, channel_coverage = compare_path_channel(
            rc2_bundle=rc2_bundle,
            v3_bundle=v3_bundle,
            rc2_observation=rc2_index.get(PATH_CHANNEL_NAME),
            v3_observation=v3_index.get(PATH_CHANNEL_NAME),
        )
        path_comparability = path_report.component_comparability[PATH_CHANNEL_NAME]
        path_component_match = path_report.component_matches[PATH_CHANNEL_NAME]
        comparable_channels = CURRENT_PUBLIC_COMPARABLE_CHANNELS
        channel_lifecycle_states = _channel_lifecycle_states(v3_bundle)
        v3_only_evidence_channels = derive_v3_only_evidence_channels(channel_lifecycle_states)
        catalytic_channel_coverage = _catalytic_channel_coverage(
            rc2_observation=rc2_catalytic_observation,
            v3_observation=v3_catalytic_observation,
        )
        unavailable_channels = tuple(
            current_channel_name
            for current_channel_name, current_channel_coverage in (
                (PATH_CHANNEL_NAME, channel_coverage),
                (CATALYTIC_CHANNEL_NAME, catalytic_channel_coverage),
            )
            if current_channel_coverage != "present_on_both_sides"
        )
        all_drifts = tuple(path_report.drifts)
        run_report = build_run_report(
            comparator_scope=CURRENT_PUBLIC_COMPARATOR_SCOPE,
            comparable_channels=comparable_channels,
            compound_reports=(path_report,),
            drifts=all_drifts,
            v3_only_evidence_channels=v3_only_evidence_channels,
        )
        summary = BridgeComparisonSummary(
            semantic_policy_version=semantic_policy_version,
            comparison_scope=ComparisonScope(CURRENT_PUBLIC_COMPARATOR_SCOPE),
            verdict_comparability=(
                VerdictComparability.PARTIALLY_COMPARABLE
                if comparable_channels
                else VerdictComparability.NOT_COMPARABLE
            ),
            rc2_reference_kind=rc2_adapt_result.reference_kind,
            v3_shadow_kind=_V3_SHADOW_KIND,
            comparable_channels=comparable_channels,
            v3_only_evidence_channels=v3_only_evidence_channels,
            unavailable_channels=unavailable_channels,
            run_level_flags=(
                "PATH_AND_CATALYTIC_PARTIAL",
                "FINAL_VERDICT_NOT_COMPARABLE",
                "PATH_COMPONENT_BRIDGE_CONSUMER_PRESENT",
                "PATH_COMPONENT_VERDICT_COMPARABILITY_DEFINED",
            ),
            channel_lifecycle_states=channel_lifecycle_states,
            channel_coverage={
                PATH_CHANNEL_NAME: channel_coverage,
                CATALYTIC_CHANNEL_NAME: catalytic_channel_coverage,
            },
            channel_comparability={
                PATH_CHANNEL_NAME: path_comparability,
                CATALYTIC_CHANNEL_NAME: CompoundPathComparability.NOT_COMPARABLE.value,
            },
            component_matches={
                PATH_CHANNEL_NAME: path_component_match,
                CATALYTIC_PUBLIC_COMPARABLE_COMPONENT: None,
            },
        )
        return BridgeComparisonResult(
            summary=summary,
            run_report=run_report,
            compound_reports=(path_report,),
            drifts=all_drifts,
        )


def _catalytic_channel_coverage(
    *,
    rc2_observation: Any,
    v3_observation: Any,
) -> str:
    if rc2_observation is None and v3_observation is None:
        return "unavailable_on_both_sides"
    if rc2_observation is None:
        return "unavailable_in_rc2_reference"
    if v3_observation is None:
        return "unavailable_in_v3_shadow"
    return "present_on_both_sides"


def comparison_result_to_dict(result: BridgeComparisonResult) -> dict[str, Any]:
    return _comparison_result_to_dict(
        result,
        comparator_contract_version=PARTIAL_SCOPE_COMPARATOR_CONTRACT_VERSION,
        final_verdict_fields=_FINAL_VERDICT_FIELDS,
    )
