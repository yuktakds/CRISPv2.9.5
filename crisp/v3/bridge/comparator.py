from __future__ import annotations

from dataclasses import asdict
from typing import Any

from crisp.v3.contracts import (
    BridgeComparisonResult,
    BridgeComparisonSummary,
    ComparisonScope,
    CompoundDriftReport,
    CompoundPathComparability,
    DriftRecord,
    EvidenceState,
    RC2AdaptResult,
    RunDriftReport,
    SCVObservation,
    SCVObservationBundle,
    SCVVerdict,
    VerdictComparability,
)
from crisp.v3.migration_scope import all_required_components_frozen, get_mapping_status, required_scv_components
from crisp.v3.policy import PATH_CHANNEL_NAME, SEMANTIC_POLICY_VERSION

_V3_SHADOW_KIND = "v3_sidecar_observation_bundle"
PATH_ONLY_COMPARATOR_CONTRACT_VERSION = "crisp.v3.bridge_comparator.path_only/v1"
_PATH_QUANTITATIVE_KEYS = (
    "max_blockage_ratio",
    "numeric_resolution_limited",
    "persistence_confidence",
)
_PATH_EXPLORATION_KEYS = (
    "apo_accessible_goal_voxels",
    "goal_voxel_count",
    "feasible_count",
)
_PATH_WITNESS_KEYS = (
    "witness_pose_id",
    "obstruction_path_ids",
    "path_family",
)
_PATH_APPLICABILITY_KEYS = (
    "goal_precheck_passed",
    "goal_precheck_reason",
    "supported_path_model",
    "pathyes_rule1_applicability",
    "pathyes_mode_resolved",
    "pathyes_diagnostics_status",
    "pathyes_diagnostics_error_code",
)
_NON_COMPARABLE_DRIFT_KINDS = {"coverage_drift", "applicability_drift"}
_FINAL_VERDICT_FIELDS = {"v3_shadow_verdict", "verdict_match"}
_PRIMARY_CHANNEL_LIFECYCLE_STATES = {
    "disabled",
    "applicability_only",
    "observation_materialized",
}


def required_scv_components_frozen() -> bool:
    return all_required_components_frozen()


def compute_full_verdict_comparable_subset(
    *,
    comparator_scope: str,
    compound_reports: tuple[CompoundDriftReport, ...],
    v3_only_evidence_channels: tuple[str, ...],
) -> dict[str, Any]:
    mapping_status = {
        component_name: get_mapping_status(component_name)
        for component_name in required_scv_components()
    }
    if comparator_scope == ComparisonScope.PATH_ONLY_PARTIAL.value:
        return {
            "computable": False,
            "subset_indices": (),
            "mapping_status": mapping_status,
            "reason": "full verdict comparability is unavailable in path_only_partial scope",
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
    if comparator_scope == ComparisonScope.PATH_ONLY_PARTIAL.value and (
        full_verdict_computable
        or full_verdict_comparable_count != 0
        or verdict_match_rate is not None
        or verdict_mismatch_rate is not None
    ):
        raise ValueError("path_only_partial scope must not activate full-scope aggregation")


def _bundle_index(bundle: SCVObservationBundle) -> dict[str, SCVObservation]:
    return {observation.channel_name: observation for observation in bundle.observations}


def _normalize_numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalize_bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return None


def _normalize_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _normalize_str_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return None


def _path_threshold(observation: SCVObservation) -> float | None:
    payload_value = _normalize_numeric(observation.payload.get("blockage_pass_threshold"))
    if payload_value is not None:
        return payload_value
    return _normalize_numeric(observation.bridge_metrics.get("blockage_pass_threshold"))


def _path_view(observation: SCVObservation | None) -> dict[str, Any]:
    if observation is None:
        return {
            "quantitative_metrics": {key: None for key in _PATH_QUANTITATIVE_KEYS},
            "exploration_slice": {key: None for key in _PATH_EXPLORATION_KEYS},
            "witness_bundle": {
                "witness_pose_id": None,
                "obstruction_path_ids": None,
                "path_family": None,
            },
            "applicability": {key: None for key in _PATH_APPLICABILITY_KEYS},
            "blockage_pass_threshold": None,
        }

    payload = dict(observation.payload)
    raw_quantitative = payload.get("quantitative_metrics")
    quantitative_metrics = {
        "max_blockage_ratio": _normalize_numeric(
            raw_quantitative.get("max_blockage_ratio") if isinstance(raw_quantitative, dict) else payload.get("max_blockage_ratio", payload.get("blockage_ratio"))
        ),
        "numeric_resolution_limited": _normalize_bool_or_none(
            raw_quantitative.get("numeric_resolution_limited") if isinstance(raw_quantitative, dict) else payload.get("numeric_resolution_limited")
        ),
        "persistence_confidence": _normalize_numeric(
            raw_quantitative.get("persistence_confidence") if isinstance(raw_quantitative, dict) else payload.get("persistence_confidence")
        ),
    }
    raw_exploration = payload.get("exploration_slice")
    exploration_slice = {
        "apo_accessible_goal_voxels": _normalize_int(
            raw_exploration.get("apo_accessible_goal_voxels") if isinstance(raw_exploration, dict) else payload.get("apo_accessible_goal_voxels")
        ),
        "goal_voxel_count": _normalize_int(
            raw_exploration.get("goal_voxel_count") if isinstance(raw_exploration, dict) else payload.get("goal_voxel_count")
        ),
        "feasible_count": _normalize_int(
            raw_exploration.get("feasible_count") if isinstance(raw_exploration, dict) else payload.get("feasible_count")
        ),
    }
    raw_witness = payload.get("witness_bundle")
    witness_bundle = {
        "witness_pose_id": (
            raw_witness.get("witness_pose_id")
            if isinstance(raw_witness, dict)
            else payload.get("witness_pose_id")
        ),
        "obstruction_path_ids": _normalize_str_list(
            raw_witness.get("obstruction_path_ids") if isinstance(raw_witness, dict) else payload.get("obstruction_path_ids")
        ),
        "path_family": (
            raw_witness.get("path_family")
            if isinstance(raw_witness, dict)
            else payload.get("path_family", observation.family)
        ),
    }
    raw_applicability = payload.get("applicability")
    applicability = {
        "goal_precheck_passed": _normalize_bool_or_none(
            raw_applicability.get("goal_precheck_passed") if isinstance(raw_applicability, dict) else payload.get("goal_precheck_passed")
        ),
        "goal_precheck_reason": (
            raw_applicability.get("goal_precheck_reason")
            if isinstance(raw_applicability, dict)
            else payload.get("goal_precheck_reason")
        ),
        "supported_path_model": _normalize_bool_or_none(
            raw_applicability.get("supported_path_model") if isinstance(raw_applicability, dict) else payload.get("supported_path_model")
        ),
        "pathyes_rule1_applicability": (
            raw_applicability.get("pathyes_rule1_applicability")
            if isinstance(raw_applicability, dict)
            else payload.get("pathyes_rule1_applicability")
        ),
        "pathyes_mode_resolved": (
            raw_applicability.get("pathyes_mode_resolved")
            if isinstance(raw_applicability, dict)
            else payload.get("pathyes_mode_resolved")
        ),
        "pathyes_diagnostics_status": (
            raw_applicability.get("pathyes_diagnostics_status")
            if isinstance(raw_applicability, dict)
            else payload.get("pathyes_diagnostics_status")
        ),
        "pathyes_diagnostics_error_code": (
            raw_applicability.get("pathyes_diagnostics_error_code")
            if isinstance(raw_applicability, dict)
            else payload.get("pathyes_diagnostics_error_code")
        ),
    }
    return {
        "quantitative_metrics": quantitative_metrics,
        "exploration_slice": exploration_slice,
        "witness_bundle": witness_bundle,
        "applicability": applicability,
        "blockage_pass_threshold": _path_threshold(observation),
    }


def _applicability_signature(bundle: SCVObservationBundle, *, channel_name: str) -> list[dict[str, Any]]:
    rows = [
        {
            "reason_code": record.reason_code,
            "detail": record.detail,
            "scope": record.scope,
            "applicable": record.applicable,
        }
        for record in bundle.applicability_records
        if record.channel_name == channel_name
    ]
    return sorted(rows, key=lambda row: (str(row["reason_code"]), str(row["detail"])))


def _derive_component_evidence_state(observation: SCVObservation | None, path_view: dict[str, Any]) -> str | None:
    if observation is None:
        return None
    if observation.evidence_state is not None:
        return observation.evidence_state.value
    quantitative_metrics = path_view["quantitative_metrics"]
    numeric_resolution_limited = quantitative_metrics["numeric_resolution_limited"]
    max_blockage_ratio = quantitative_metrics["max_blockage_ratio"]
    blockage_pass_threshold = path_view["blockage_pass_threshold"]
    if numeric_resolution_limited is True:
        return EvidenceState.INSUFFICIENT.value
    if max_blockage_ratio is None or blockage_pass_threshold is None:
        return None
    if max_blockage_ratio >= blockage_pass_threshold:
        return EvidenceState.SUPPORTED.value
    return EvidenceState.REFUTED.value


def _derive_component_verdict(observation: SCVObservation | None, path_view: dict[str, Any]) -> str | None:
    if observation is None:
        return None
    if observation.verdict is not None:
        return observation.verdict.value
    evidence_state = _derive_component_evidence_state(observation, path_view)
    if evidence_state == EvidenceState.SUPPORTED.value:
        return SCVVerdict.PASS.value
    if evidence_state == EvidenceState.REFUTED.value:
        return SCVVerdict.FAIL.value
    if evidence_state == EvidenceState.INSUFFICIENT.value:
        return SCVVerdict.UNCLEAR.value
    return None


class BridgeComparator:
    def compare(
        self,
        *,
        semantic_policy_version: str,
        rc2_adapt_result: RC2AdaptResult,
        v3_bundle: SCVObservationBundle,
    ) -> BridgeComparisonResult:
        rc2_bundle = rc2_adapt_result.bundle
        rc2_index = _bundle_index(rc2_bundle)
        v3_index = _bundle_index(v3_bundle)

        path_report, channel_coverage = self._compare_path(
            rc2_bundle=rc2_bundle,
            v3_bundle=v3_bundle,
            rc2_observation=rc2_index.get(PATH_CHANNEL_NAME),
            v3_observation=v3_index.get(PATH_CHANNEL_NAME),
        )
        path_comparability = path_report.component_comparability[PATH_CHANNEL_NAME]
        path_component_match = path_report.component_matches[PATH_CHANNEL_NAME]
        comparable_channels = (PATH_CHANNEL_NAME,)
        channel_lifecycle_states = {
            PATH_CHANNEL_NAME: (
                "observation_materialized" if v3_index.get(PATH_CHANNEL_NAME) is not None else "applicability_only"
            ),
            "cap": "observation_materialized" if v3_index.get("cap") is not None else "applicability_only",
            "catalytic": (
                "observation_materialized" if v3_index.get("catalytic") is not None else "applicability_only"
            ),
        }
        v3_only_evidence_channels = tuple(
            channel_name
            for channel_name in ("cap", "catalytic")
            if channel_lifecycle_states[channel_name] == "observation_materialized"
        )
        unavailable_channels = (
            ()
            if channel_coverage == "present_on_both_sides"
            else (PATH_CHANNEL_NAME,)
        )
        all_drifts = tuple(path_report.drifts)
        run_report = self._build_run_report(
            comparator_scope=ComparisonScope.PATH_ONLY_PARTIAL.value,
            comparable_channels=comparable_channels,
            compound_reports=(path_report,),
            drifts=all_drifts,
            v3_only_evidence_channels=v3_only_evidence_channels,
        )
        summary = BridgeComparisonSummary(
            semantic_policy_version=semantic_policy_version,
            comparison_scope=ComparisonScope.PATH_ONLY_PARTIAL,
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
                "PATH_ONLY_PARTIAL",
                "FINAL_VERDICT_NOT_COMPARABLE",
                "PATH_COMPONENT_BRIDGE_CONSUMER_PRESENT",
                "PATH_COMPONENT_VERDICT_COMPARABILITY_DEFINED",
            ),
            channel_lifecycle_states=channel_lifecycle_states,
            channel_coverage={PATH_CHANNEL_NAME: channel_coverage},
            channel_comparability={PATH_CHANNEL_NAME: path_comparability},
            component_matches={PATH_CHANNEL_NAME: path_component_match},
        )
        return BridgeComparisonResult(
            summary=summary,
            run_report=run_report,
            compound_reports=(path_report,),
            drifts=all_drifts,
        )

    def _compare_path(
        self,
        *,
        rc2_bundle: SCVObservationBundle,
        v3_bundle: SCVObservationBundle,
        rc2_observation: SCVObservation | None,
        v3_observation: SCVObservation | None,
    ) -> tuple[CompoundDriftReport, str]:
        drifts: list[DriftRecord] = []
        channel_coverage = "present_on_both_sides"
        if rc2_observation is None or v3_observation is None:
            channel_coverage = (
                "unavailable_on_both_sides"
                if rc2_observation is None and v3_observation is None
                else "unavailable_in_rc2_reference"
                if rc2_observation is None
                else "unavailable_in_v3_shadow"
            )
            drifts.append(
                DriftRecord(
                    channel_name=PATH_CHANNEL_NAME,
                    drift_kind="coverage_drift",
                    message="channel unavailable on one side",
                    details={
                        "rc2_present": rc2_observation is not None,
                        "v3_present": v3_observation is not None,
                    },
                )
            )

        rc2_view = _path_view(rc2_observation)
        v3_view = _path_view(v3_observation)
        rc2_run_applicability = _applicability_signature(rc2_bundle, channel_name=PATH_CHANNEL_NAME)
        v3_run_applicability = _applicability_signature(v3_bundle, channel_name=PATH_CHANNEL_NAME)
        if rc2_run_applicability != v3_run_applicability:
            drifts.append(
                DriftRecord(
                    channel_name=PATH_CHANNEL_NAME,
                    drift_kind="applicability_drift",
                    message="run-level applicability records differ",
                    details={
                        "rc2": rc2_run_applicability,
                        "v3": v3_run_applicability,
                    },
                )
            )

        if rc2_observation is not None and v3_observation is not None:
            for key in _PATH_APPLICABILITY_KEYS:
                if rc2_view["applicability"][key] != v3_view["applicability"][key]:
                    drifts.append(
                        DriftRecord(
                            channel_name=PATH_CHANNEL_NAME,
                            drift_kind="applicability_drift",
                            message=f"applicability differs: {key}",
                            details={
                                "field": key,
                                "rc2": rc2_view["applicability"][key],
                                "v3": v3_view["applicability"][key],
                            },
                        )
                    )
            for section_name, keys in (
                ("quantitative_metrics", _PATH_QUANTITATIVE_KEYS),
                ("exploration_slice", _PATH_EXPLORATION_KEYS),
            ):
                for key in keys:
                    if rc2_view[section_name][key] != v3_view[section_name][key]:
                        drifts.append(
                            DriftRecord(
                                channel_name=PATH_CHANNEL_NAME,
                                drift_kind="metrics_drift",
                                message=f"{section_name} differs: {key}",
                                details={
                                    "section": section_name,
                                    "metric": key,
                                    "rc2": rc2_view[section_name][key],
                                    "v3": v3_view[section_name][key],
                                },
                            )
                        )
            for key in _PATH_WITNESS_KEYS:
                if rc2_view["witness_bundle"][key] != v3_view["witness_bundle"][key]:
                    drifts.append(
                        DriftRecord(
                            channel_name=PATH_CHANNEL_NAME,
                            drift_kind="witness_drift",
                            message=f"witness differs: {key}",
                            details={
                                "field": key,
                                "rc2": rc2_view["witness_bundle"][key],
                                "v3": v3_view["witness_bundle"][key],
                            },
                        )
                    )

        component_comparability = CompoundPathComparability.COMPONENT_VERDICT_COMPARABLE
        drift_kinds = {drift.drift_kind for drift in drifts}
        if drift_kinds & _NON_COMPARABLE_DRIFT_KINDS:
            component_comparability = CompoundPathComparability.NOT_COMPARABLE
        elif "metrics_drift" in drift_kinds:
            component_comparability = CompoundPathComparability.EVIDENCE_COMPARABLE

        rc2_component_verdict = _derive_component_verdict(rc2_observation, rc2_view)
        v3_component_verdict = _derive_component_verdict(v3_observation, v3_view)
        component_match = (
            None
            if component_comparability is CompoundPathComparability.NOT_COMPARABLE
            or rc2_component_verdict is None
            or v3_component_verdict is None
            else rc2_component_verdict == v3_component_verdict
        )
        report = CompoundDriftReport(
            channel_name=PATH_CHANNEL_NAME,
            component_comparability={PATH_CHANNEL_NAME: component_comparability.value},
            component_matches={PATH_CHANNEL_NAME: component_match},
            rc2_component_verdicts={PATH_CHANNEL_NAME: rc2_component_verdict},
            v3_component_verdicts={PATH_CHANNEL_NAME: v3_component_verdict},
            rc2_component_states={PATH_CHANNEL_NAME: _derive_component_evidence_state(rc2_observation, rc2_view)},
            v3_component_states={PATH_CHANNEL_NAME: _derive_component_evidence_state(v3_observation, v3_view)},
            v3_shadow_verdict=None,
            verdict_match=None,
            drifts=tuple(drifts),
        )
        return report, channel_coverage

    def _build_run_report(
        self,
        *,
        comparator_scope: str,
        comparable_channels: tuple[str, ...],
        compound_reports: tuple[CompoundDriftReport, ...],
        drifts: tuple[DriftRecord, ...],
        v3_only_evidence_channels: tuple[str, ...],
    ) -> RunDriftReport:
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
        denominators = resolve_denominators(
            total_compounds=len(compound_reports),
            component_verdict_comparable_count=component_verdict_comparable_count,
            full_verdict_comparable_count=full_verdict_comparable_count,
        )
        verdict_match_rate = None
        verdict_mismatch_rate = None
        guard_current_scope_no_full_aggregation(
            comparator_scope=comparator_scope,
            full_verdict_computable=full_verdict_computable,
            full_verdict_comparable_count=full_verdict_comparable_count,
            verdict_match_rate=verdict_match_rate,
            verdict_mismatch_rate=verdict_mismatch_rate,
        )
        return RunDriftReport(
            comparator_scope=ComparisonScope.PATH_ONLY_PARTIAL,
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


def comparison_result_to_dict(result: BridgeComparisonResult) -> dict[str, Any]:
    compound_reports = []
    for report in result.compound_reports:
        payload = asdict(report)
        for field_name in _FINAL_VERDICT_FIELDS:
            payload.pop(field_name, None)
        compound_reports.append(payload)
    return {
        "summary": asdict(result.summary),
        "run_drift_report": asdict(result.run_report),
        "compound_drift_reports": compound_reports,
        "drifts": [asdict(drift) for drift in result.drifts],
        "semantic_policy_version": SEMANTIC_POLICY_VERSION,
        "comparator_contract_version": PATH_ONLY_COMPARATOR_CONTRACT_VERSION,
    }
