from __future__ import annotations

from crisp.v3.contracts import (
    ComparisonScope,
    CompoundDriftReport,
    CompoundPathComparability,
    DriftRecord,
    RunDriftReport,
)
from crisp.v3.migration_scope import (
    all_required_components_frozen,
    get_comparator_scope,
    get_mapping_status,
    required_scv_components,
    scope_allows_full_verdict_aggregation,
)


def required_scv_components_frozen() -> bool:
    return all_required_components_frozen()


def compute_full_verdict_comparable_subset(
    *,
    comparator_scope: str,
    compound_reports: tuple[CompoundDriftReport, ...],
    v3_only_evidence_channels: tuple[str, ...],
) -> dict[str, object]:
    normalized_scope = get_comparator_scope(comparator_scope)
    mapping_status = {
        component_name: get_mapping_status(component_name)
        for component_name in required_scv_components()
    }
    if not scope_allows_full_verdict_aggregation(normalized_scope):
        return {
            "computable": False,
            "subset_indices": (),
            "mapping_status": mapping_status,
            "reason": f"full verdict comparability is unavailable in {normalized_scope} scope",
        }
    if not required_scv_components_frozen():
        return {
            "computable": False,
            "subset_indices": (),
            "mapping_status": mapping_status,
            "reason": "required SCV components are not all FROZEN",
        }
    subset_indices: list[int] = []
    for index, report in enumerate(compound_reports):
        drift_kinds = {drift.drift_kind for drift in report.drifts}
        if drift_kinds & {"coverage_drift", "applicability_drift", "metrics_drift"}:
            continue
        if set(report.component_matches) & set(v3_only_evidence_channels):
            continue
        subset_indices.append(index)
    return {
        "computable": True,
        "subset_indices": tuple(subset_indices),
        "mapping_status": mapping_status,
        "reason": "all required SCV components are FROZEN and subset is drift-clean",
    }


def resolve_denominators(
    *,
    total_compounds: int,
    component_verdict_comparable_count: int,
    full_verdict_comparable_count: int,
) -> dict[str, int]:
    return {
        "coverage_drift_rate": total_compounds,
        "applicability_drift_rate": total_compounds,
        "verdict_match_rate": full_verdict_comparable_count,
        "verdict_mismatch_rate": full_verdict_comparable_count,
        "path_component_match_rate": component_verdict_comparable_count,
    }


def guard_current_scope_no_full_aggregation(
    *,
    comparator_scope: str,
    full_verdict_computable: bool,
    full_verdict_comparable_count: int,
    verdict_match_rate: float | None,
    verdict_mismatch_rate: float | None,
) -> None:
    normalized_scope = get_comparator_scope(comparator_scope)
    if not scope_allows_full_verdict_aggregation(normalized_scope) and (
        full_verdict_computable
        or full_verdict_comparable_count != 0
        or verdict_match_rate is not None
        or verdict_mismatch_rate is not None
    ):
        raise ValueError(f"{normalized_scope} scope must not activate full-scope aggregation")


def build_run_report(
    *,
    comparator_scope: str,
    comparable_channels: tuple[str, ...],
    compound_reports: tuple[CompoundDriftReport, ...],
    drifts: tuple[DriftRecord, ...],
    v3_only_evidence_channels: tuple[str, ...],
) -> RunDriftReport:
    normalized_scope = ComparisonScope(get_comparator_scope(comparator_scope))
    component_matches = [
        match
        for report in compound_reports
        for match in report.component_matches.values()
        if match is not None
    ]
    comparable_subset_size = sum(
        1
        for report in compound_reports
        for comparability in report.component_comparability.values()
        if comparability != CompoundPathComparability.NOT_COMPARABLE.value
    )
    component_verdict_comparable_count = len(component_matches)
    component_match_count = sum(1 for match in component_matches if match is True)
    path_component_match_rate = (
        component_match_count / component_verdict_comparable_count
        if component_verdict_comparable_count
        else None
    )
    full_subset = compute_full_verdict_comparable_subset(
        comparator_scope=comparator_scope,
        compound_reports=compound_reports,
        v3_only_evidence_channels=v3_only_evidence_channels,
    )
    full_verdict_computable = bool(full_subset["computable"])
    full_verdict_comparable_count = len(full_subset["subset_indices"])
    verdict_match_rate = None
    verdict_mismatch_rate = None
    guard_current_scope_no_full_aggregation(
        comparator_scope=normalized_scope.value,
        full_verdict_computable=full_verdict_computable,
        full_verdict_comparable_count=full_verdict_comparable_count,
        verdict_match_rate=verdict_match_rate,
        verdict_mismatch_rate=verdict_mismatch_rate,
    )
    return RunDriftReport(
        comparator_scope=normalized_scope,
        comparable_channels=comparable_channels,
        comparable_subset_size=comparable_subset_size,
        component_verdict_comparable_count=component_verdict_comparable_count,
        component_match_count=component_match_count,
        full_verdict_computable=full_verdict_computable,
        full_verdict_comparable_count=full_verdict_comparable_count,
        verdict_match_count=None,
        verdict_mismatch_count=None,
        verdict_match_rate=verdict_match_rate,
        verdict_mismatch_rate=verdict_mismatch_rate,
        path_component_match_rate=path_component_match_rate,
        coverage_drift_count=sum(1 for drift in drifts if drift.drift_kind == "coverage_drift"),
        applicability_drift_count=sum(1 for drift in drifts if drift.drift_kind == "applicability_drift"),
        metrics_drift_count=sum(1 for drift in drifts if drift.drift_kind == "metrics_drift"),
        witness_drift_count=sum(1 for drift in drifts if drift.drift_kind == "witness_drift"),
        v3_only_evidence_count=len(v3_only_evidence_channels),
    )
