from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from crisp.config.models import TargetConfig
from crisp.v29.pathyes import resolve_pathyes_state
from crisp.v3.contracts import RC2AdaptResult, RunApplicabilityRecord, SCVObservation, SCVObservationBundle
from crisp.v3.path_channel import load_pat_diagnostics_payload
from crisp.v3.policy import OBSERVATION_BUNDLE_SCHEMA_VERSION, PATH_CHANNEL_FAMILY, PATH_CHANNEL_NAME, SEMANTIC_POLICY_VERSION

_RC2_REFERENCE_KIND = "rc2_path_diagnostics_input"
_PAT_GOAL_INVALID = "PAT_GOAL_INVALID"
_PAT_UNSUPPORTED_PATH_MODEL = "PAT_UNSUPPORTED_PATH_MODEL"
PATH_ONLY_COVERAGE_CONTRACT_VERSION = "crisp.v3.rc2_bridge.path_only/v1"
PATH_ONLY_COVERAGE_FIELDS = {
    "quantitative_metrics": (
        "max_blockage_ratio",
        "numeric_resolution_limited",
        "persistence_confidence",
    ),
    "exploration_slice": (
        "apo_accessible_goal_voxels",
        "goal_voxel_count",
        "feasible_count",
    ),
    "witness_bundle": (
        "witness_pose_id",
        "obstruction_path_ids",
        "path_family",
    ),
    "applicability": (
        "goal_precheck_passed",
        "goal_precheck_reason",
        "supported_path_model",
        "pathyes_rule1_applicability",
        "pathyes_mode_resolved",
        "pathyes_diagnostics_status",
        "pathyes_diagnostics_error_code",
    ),
}


def _diagnostics_view(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("pat_run_diagnostics_json")
    if isinstance(nested, dict):
        return nested
    return {}


def _lookup_present(payload: dict[str, Any], key: str) -> tuple[bool, Any]:
    if key in payload:
        return True, payload[key]
    diagnostics = _diagnostics_view(payload)
    if key in diagnostics:
        return True, diagnostics[key]
    return False, None


def _normalize_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalize_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _normalize_str_list(value: Any) -> list[str] | None:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return None


def _project_bridge_payload(
    *,
    raw_payload: dict[str, Any],
    diagnostics_source: str,
    config: TargetConfig,
    pathyes_force_false: bool,
) -> tuple[dict[str, Any], list[RunApplicabilityRecord]]:
    pathyes_state = resolve_pathyes_state(
        config=config,
        mode="pat-backed",
        pat_diagnostics_path=diagnostics_source,
        pathyes_force_false=pathyes_force_false,
    )
    applicability_records: list[RunApplicabilityRecord] = []

    supported_present, supported_value = _lookup_present(raw_payload, "supported_path_model")
    if config.pat.path_model != PATH_CHANNEL_FAMILY or supported_value is False:
        applicability_records.append(
            RunApplicabilityRecord(
                channel_name=PATH_CHANNEL_NAME,
                family=PATH_CHANNEL_FAMILY,
                scope="run",
                applicable=False,
                reason_code=_PAT_UNSUPPORTED_PATH_MODEL,
                detail=f"formal family is {PATH_CHANNEL_FAMILY}, observed={config.pat.path_model}",
                diagnostics_source=diagnostics_source,
                diagnostics_payload=(
                    {"supported_path_model": supported_value}
                    if supported_present
                    else {}
                ),
            )
        )

    goal_present, goal_value = _lookup_present(raw_payload, "goal_precheck_passed")
    if goal_present and goal_value is False and not applicability_records:
        applicability_records.append(
            RunApplicabilityRecord(
                channel_name=PATH_CHANNEL_NAME,
                family=PATH_CHANNEL_FAMILY,
                scope="run",
                applicable=False,
                reason_code=_PAT_GOAL_INVALID,
                detail="goal_precheck_passed=false",
                diagnostics_source=diagnostics_source,
                diagnostics_payload={"goal_precheck_passed": False},
            )
        )

    quantitative_metrics: dict[str, Any] = {}
    _, blockage_ratio_raw = _lookup_present(raw_payload, "blockage_ratio")
    _, numeric_resolution_raw = _lookup_present(raw_payload, "numeric_resolution_limited")
    _, persistence_confidence_raw = _lookup_present(raw_payload, "persistence_confidence")
    blockage_ratio = _normalize_float(blockage_ratio_raw)
    numeric_resolution_limited = (
        None
        if numeric_resolution_raw is None or not isinstance(numeric_resolution_raw, bool)
        else numeric_resolution_raw
    )
    persistence_confidence = _normalize_float(persistence_confidence_raw)
    quantitative_metrics = {
        "max_blockage_ratio": blockage_ratio,
        "numeric_resolution_limited": numeric_resolution_limited,
        "persistence_confidence": persistence_confidence,
    }

    exploration_slice: dict[str, Any] = {
        "apo_accessible_goal_voxels": _normalize_int(_lookup_present(raw_payload, "apo_accessible_goal_voxels")[1]),
        "goal_voxel_count": _normalize_int(_lookup_present(raw_payload, "goal_voxel_count")[1]),
        "feasible_count": _normalize_int(_lookup_present(raw_payload, "feasible_count")[1]),
    }

    witness_bundle: dict[str, Any] = {
        "witness_pose_id": _lookup_present(raw_payload, "witness_pose_id")[1],
        "obstruction_path_ids": _normalize_str_list(_lookup_present(raw_payload, "obstruction_path_ids")[1]),
        "path_family": PATH_CHANNEL_FAMILY,
    }

    _, goal_precheck_reason = _lookup_present(raw_payload, "goal_precheck_reason")
    applicability: dict[str, Any] = {
        "goal_precheck_passed": goal_value if goal_present else None,
        "goal_precheck_reason": goal_precheck_reason,
        "supported_path_model": supported_value if supported_present else None,
        "pathyes_rule1_applicability": pathyes_state.rule1_applicability,
        "pathyes_mode_resolved": pathyes_state.mode,
        "pathyes_diagnostics_status": pathyes_state.diagnostics_status,
        "pathyes_diagnostics_error_code": pathyes_state.diagnostics_error_code,
    }

    payload = {
        "quantitative_metrics": quantitative_metrics,
        "exploration_slice": exploration_slice,
        "witness_bundle": witness_bundle,
        "applicability": applicability,
        "max_blockage_ratio": blockage_ratio,
        "blockage_ratio": blockage_ratio,
        "numeric_resolution_limited": numeric_resolution_limited,
        "persistence_confidence": persistence_confidence,
        "apo_accessible_goal_voxels": exploration_slice["apo_accessible_goal_voxels"],
        "goal_voxel_count": exploration_slice["goal_voxel_count"],
        "feasible_count": exploration_slice["feasible_count"],
        "witness_pose_id": witness_bundle["witness_pose_id"],
        "obstruction_path_ids": witness_bundle["obstruction_path_ids"],
        "goal_precheck_passed": applicability["goal_precheck_passed"],
        "goal_precheck_reason": applicability["goal_precheck_reason"],
        "supported_path_model": applicability["supported_path_model"],
        "pathyes_rule1_applicability": applicability["pathyes_rule1_applicability"],
        "pathyes_mode_resolved": applicability["pathyes_mode_resolved"],
        "pathyes_diagnostics_status": applicability["pathyes_diagnostics_status"],
        "pathyes_diagnostics_error_code": applicability["pathyes_diagnostics_error_code"],
        "blockage_pass_threshold": float(config.pat.blockage_pass_threshold),
        "source_payload": {
            "pat_run_diagnostics_json": raw_payload.get("pat_run_diagnostics_json", {}),
        },
    }
    return payload, applicability_records


class RC2BridgeAdapter:
    def adapt_path_only(
        self,
        *,
        run_id: str,
        config: TargetConfig,
        pat_diagnostics_path: str | Path | None,
        pathyes_force_false: bool = False,
    ) -> RC2AdaptResult:
        payload, load_record = load_pat_diagnostics_payload(pat_diagnostics_path)
        if load_record is not None:
            bundle = SCVObservationBundle(
                schema_version=OBSERVATION_BUNDLE_SCHEMA_VERSION,
                run_id=run_id,
                semantic_policy_version=SEMANTIC_POLICY_VERSION,
                observations=[],
                applicability_records=[load_record],
                bridge_diagnostics={
                    "reference_kind": _RC2_REFERENCE_KIND,
                    "coverage_channels": [],
                    "unavailable_channels": [PATH_CHANNEL_NAME],
                    "adapter_notes": [load_record.reason_code],
                    "coverage_contract_version": PATH_ONLY_COVERAGE_CONTRACT_VERSION,
                    "coverage_fields": {key: list(values) for key, values in PATH_ONLY_COVERAGE_FIELDS.items()},
                    "missing_fields_not_inferred": True,
                },
            )
            return RC2AdaptResult(
                bundle=bundle,
                coverage_channels=(),
                unavailable_channels=(PATH_CHANNEL_NAME,),
                notes=(load_record.reason_code,),
                reference_kind=_RC2_REFERENCE_KIND,
            )

        assert payload is not None
        diagnostics_source = str(Path(pat_diagnostics_path))
        projected_payload, applicability_records = _project_bridge_payload(
            raw_payload=payload,
            diagnostics_source=diagnostics_source,
            config=config,
            pathyes_force_false=pathyes_force_false,
        )

        observations: list[SCVObservation] = []
        coverage_channels: tuple[str, ...]
        unavailable_channels: tuple[str, ...]
        if applicability_records:
            coverage_channels = ()
            unavailable_channels = (PATH_CHANNEL_NAME,)
        else:
            observations.append(
                SCVObservation(
                    channel_name=PATH_CHANNEL_NAME,
                    family=PATH_CHANNEL_FAMILY,
                    verdict=None,
                    evidence_state=None,
                    payload=projected_payload,
                    source=diagnostics_source,
                    bridge_metrics={
                        "adapter_kind": _RC2_REFERENCE_KIND,
                        "missing_fields_not_inferred": True,
                        "blockage_pass_threshold": float(config.pat.blockage_pass_threshold),
                    },
                )
            )
            coverage_channels = (PATH_CHANNEL_NAME,)
            unavailable_channels = ()

        bundle = SCVObservationBundle(
            schema_version=OBSERVATION_BUNDLE_SCHEMA_VERSION,
            run_id=run_id,
            semantic_policy_version=SEMANTIC_POLICY_VERSION,
            observations=observations,
            applicability_records=applicability_records,
            bridge_diagnostics={
                "reference_kind": _RC2_REFERENCE_KIND,
                "coverage_channels": list(coverage_channels),
                "unavailable_channels": list(unavailable_channels),
                "adapter_notes": [],
                "coverage_contract_version": PATH_ONLY_COVERAGE_CONTRACT_VERSION,
                "coverage_fields": {key: list(values) for key, values in PATH_ONLY_COVERAGE_FIELDS.items()},
                "missing_fields_not_inferred": True,
            },
        )
        return RC2AdaptResult(
            bundle=bundle,
            coverage_channels=coverage_channels,
            unavailable_channels=unavailable_channels,
            notes=(),
            reference_kind=_RC2_REFERENCE_KIND,
        )


def adapt_result_to_dict(result: RC2AdaptResult) -> dict[str, Any]:
    return {
        "reference_kind": result.reference_kind,
        "coverage_channels": list(result.coverage_channels),
        "unavailable_channels": list(result.unavailable_channels),
        "notes": list(result.notes),
        "bundle": asdict(result.bundle),
    }
