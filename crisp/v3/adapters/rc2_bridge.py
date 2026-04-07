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
    for key in ("blockage_ratio", "numeric_resolution_limited", "persistence_confidence"):
        present, raw_value = _lookup_present(raw_payload, key)
        if not present:
            continue
        if key == "numeric_resolution_limited":
            if isinstance(raw_value, bool):
                quantitative_metrics[key] = raw_value
            continue
        normalized = _normalize_float(raw_value)
        if normalized is not None:
            quantitative_metrics[key] = normalized

    exploration_slice: dict[str, Any] = {}
    for key in ("apo_accessible_goal_voxels", "goal_voxel_count", "feasible_count"):
        present, raw_value = _lookup_present(raw_payload, key)
        if not present:
            continue
        normalized = _normalize_int(raw_value)
        if normalized is not None:
            exploration_slice[key] = normalized

    witness_bundle: dict[str, Any] = {"path_family": PATH_CHANNEL_FAMILY}
    for key in ("witness_pose_id",):
        present, raw_value = _lookup_present(raw_payload, key)
        if present and raw_value is not None:
            witness_bundle[key] = raw_value
    present, raw_value = _lookup_present(raw_payload, "obstruction_path_ids")
    obstruction_path_ids = _normalize_str_list(raw_value) if present else None
    if obstruction_path_ids is not None:
        witness_bundle["obstruction_path_ids"] = obstruction_path_ids

    applicability: dict[str, Any] = {
        "pathyes_rule1_applicability": pathyes_state.rule1_applicability,
        "pathyes_mode_resolved": pathyes_state.mode,
        "pathyes_diagnostics_status": pathyes_state.diagnostics_status,
        "pathyes_diagnostics_error_code": pathyes_state.diagnostics_error_code,
    }
    for key in ("goal_precheck_passed", "goal_precheck_reason", "supported_path_model"):
        present, raw_value = _lookup_present(raw_payload, key)
        if present:
            applicability[key] = raw_value

    payload = {
        "quantitative_metrics": quantitative_metrics,
        "exploration_slice": exploration_slice,
        "witness_bundle": witness_bundle,
        "applicability": applicability,
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
