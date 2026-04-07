from __future__ import annotations

from dataclasses import asdict
from typing import Any

from crisp.v3.contracts import (
    BridgeComparisonResult,
    BridgeComparisonSummary,
    ComparisonScope,
    DriftRecord,
    RC2AdaptResult,
    SCVObservation,
    SCVObservationBundle,
    VerdictComparability,
)
from crisp.v3.policy import PATH_CHANNEL_NAME, SEMANTIC_POLICY_VERSION

_V3_SHADOW_KIND = "v3_sidecar_observation_bundle"


def _bundle_index(bundle: SCVObservationBundle) -> dict[str, SCVObservation]:
    return {observation.channel_name: observation for observation in bundle.observations}


def _path_view(observation: SCVObservation | None) -> dict[str, dict[str, Any]]:
    if observation is None:
        return {
            "quantitative_metrics": {},
            "exploration_slice": {},
            "witness_bundle": {},
            "applicability": {},
        }

    payload = dict(observation.payload)
    quantitative_metrics = payload.get("quantitative_metrics")
    if not isinstance(quantitative_metrics, dict):
        quantitative_metrics = {
            key: payload[key]
            for key in ("blockage_ratio", "numeric_resolution_limited", "persistence_confidence")
            if key in payload
        }
    exploration_slice = payload.get("exploration_slice")
    if not isinstance(exploration_slice, dict):
        exploration_slice = {
            key: payload[key]
            for key in ("feasible_count", "apo_accessible_goal_voxels", "goal_voxel_count")
            if key in payload
        }
    witness_bundle = payload.get("witness_bundle")
    if not isinstance(witness_bundle, dict):
        witness_bundle = {
            "witness_pose_id": payload.get("witness_pose_id"),
            "obstruction_path_ids": payload.get("obstruction_path_ids", []),
            "path_family": observation.family,
        }
    applicability = payload.get("applicability")
    if not isinstance(applicability, dict):
        applicability = {
            key: payload[key]
            for key in (
                "goal_precheck_passed",
                "supported_path_model",
                "pathyes_rule1_applicability",
                "pathyes_mode_resolved",
                "pathyes_diagnostics_status",
                "pathyes_diagnostics_error_code",
            )
            if key in payload
        }
    return {
        "quantitative_metrics": quantitative_metrics,
        "exploration_slice": exploration_slice,
        "witness_bundle": witness_bundle,
        "applicability": applicability,
    }


def _applicability_signature(bundle: SCVObservationBundle, *, channel_name: str) -> list[dict[str, Any]]:
    records = [
        {
            "reason_code": record.reason_code,
            "detail": record.detail,
            "scope": record.scope,
            "applicable": record.applicable,
        }
        for record in bundle.applicability_records
        if record.channel_name == channel_name
    ]
    return sorted(records, key=lambda record: (str(record["reason_code"]), str(record["detail"])))


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

        comparable_channels: list[str] = []
        unavailable_channels: list[str] = []
        drifts: list[DriftRecord] = []

        for channel_name in (PATH_CHANNEL_NAME,):
            rc2_observation = rc2_index.get(channel_name)
            v3_observation = v3_index.get(channel_name)
            if rc2_observation is None or v3_observation is None:
                unavailable_channels.append(channel_name)
                drifts.append(
                    DriftRecord(
                        channel_name=channel_name,
                        drift_kind="coverage_drift",
                        message="channel unavailable on one side",
                        details={
                            "rc2_present": rc2_observation is not None,
                            "v3_present": v3_observation is not None,
                        },
                    )
                )
                continue

            comparable_channels.append(channel_name)
            drifts.extend(self._compare_path(channel_name=channel_name, rc2_observation=rc2_observation, v3_observation=v3_observation))

        rc2_applicability = _applicability_signature(rc2_bundle, channel_name=PATH_CHANNEL_NAME)
        v3_applicability = _applicability_signature(v3_bundle, channel_name=PATH_CHANNEL_NAME)
        if rc2_applicability != v3_applicability:
            drifts.append(
                DriftRecord(
                    channel_name=PATH_CHANNEL_NAME,
                    drift_kind="applicability_drift",
                    message="run-level applicability records differ",
                    details={
                        "rc2": rc2_applicability,
                        "v3": v3_applicability,
                    },
                )
            )

        if comparable_channels:
            verdict_comparability = VerdictComparability.PARTIALLY_COMPARABLE
        else:
            verdict_comparability = VerdictComparability.NOT_COMPARABLE

        summary = BridgeComparisonSummary(
            semantic_policy_version=semantic_policy_version,
            comparison_scope=ComparisonScope.PATH_ONLY_PARTIAL,
            verdict_comparability=verdict_comparability,
            rc2_reference_kind=rc2_adapt_result.reference_kind,
            v3_shadow_kind=_V3_SHADOW_KIND,
            comparable_channels=tuple(comparable_channels),
            unavailable_channels=tuple(unavailable_channels),
            run_level_flags=(
                "PARTIAL_PATH_ONLY",
                "FINAL_VERDICT_NOT_COMPARABLE",
            ),
            channel_coverage={
                PATH_CHANNEL_NAME: (
                    "comparable"
                    if PATH_CHANNEL_NAME in comparable_channels
                    else (
                        "unavailable_on_both_sides"
                        if PATH_CHANNEL_NAME not in rc2_index and PATH_CHANNEL_NAME not in v3_index
                        else "unavailable_in_rc2_reference"
                        if PATH_CHANNEL_NAME not in rc2_index
                        else "unavailable_in_v3_shadow"
                    )
                )
            },
        )
        return BridgeComparisonResult(summary=summary, drifts=tuple(drifts))

    def _compare_path(
        self,
        *,
        channel_name: str,
        rc2_observation: SCVObservation,
        v3_observation: SCVObservation,
    ) -> list[DriftRecord]:
        rc2_view = _path_view(rc2_observation)
        v3_view = _path_view(v3_observation)
        drifts: list[DriftRecord] = []

        for section_name in ("quantitative_metrics", "exploration_slice"):
            rc2_section = rc2_view[section_name]
            v3_section = v3_view[section_name]
            rc2_keys = set(rc2_section)
            v3_keys = set(v3_section)
            if rc2_keys != v3_keys:
                drifts.append(
                    DriftRecord(
                        channel_name=channel_name,
                        drift_kind="metrics_drift",
                        message=f"{section_name} key set differs",
                        details={
                            "section": section_name,
                            "rc2_keys": sorted(rc2_keys),
                            "v3_keys": sorted(v3_keys),
                        },
                    )
                )
            for key in sorted(rc2_keys & v3_keys):
                if rc2_section.get(key) != v3_section.get(key):
                    drifts.append(
                        DriftRecord(
                            channel_name=channel_name,
                            drift_kind="metrics_drift",
                            message=f"{section_name} differs: {key}",
                            details={
                                "section": section_name,
                                "metric": key,
                                "rc2": rc2_section.get(key),
                                "v3": v3_section.get(key),
                            },
                        )
                    )

        rc2_witness = rc2_view["witness_bundle"]
        v3_witness = v3_view["witness_bundle"]
        for key in ("witness_pose_id", "obstruction_path_ids", "path_family"):
            if rc2_witness.get(key) != v3_witness.get(key):
                drifts.append(
                    DriftRecord(
                        channel_name=channel_name,
                        drift_kind="witness_drift",
                        message=f"witness differs: {key}",
                        details={
                            "field": key,
                            "rc2": rc2_witness.get(key),
                            "v3": v3_witness.get(key),
                        },
                    )
                )

        rc2_applicability = rc2_view["applicability"]
        v3_applicability = v3_view["applicability"]
        rc2_keys = set(rc2_applicability)
        v3_keys = set(v3_applicability)
        if rc2_keys != v3_keys:
            drifts.append(
                DriftRecord(
                    channel_name=channel_name,
                    drift_kind="applicability_drift",
                    message="applicability key set differs",
                    details={
                        "rc2_keys": sorted(rc2_keys),
                        "v3_keys": sorted(v3_keys),
                    },
                )
            )
        for key in sorted(rc2_keys & v3_keys):
            if rc2_applicability.get(key) != v3_applicability.get(key):
                drifts.append(
                    DriftRecord(
                        channel_name=channel_name,
                        drift_kind="applicability_drift",
                        message=f"applicability differs: {key}",
                        details={
                            "field": key,
                            "rc2": rc2_applicability.get(key),
                            "v3": v3_applicability.get(key),
                        },
                    )
                )

        return drifts


def comparison_result_to_dict(result: BridgeComparisonResult) -> dict[str, Any]:
    return {
        "summary": asdict(result.summary),
        "drifts": [asdict(drift) for drift in result.drifts],
        "semantic_policy_version": SEMANTIC_POLICY_VERSION,
    }
