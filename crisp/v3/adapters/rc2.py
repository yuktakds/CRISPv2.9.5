from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from crisp.config.models import TargetConfig
from crisp.v29.pathyes import resolve_pathyes_state
from crisp.v3.contracts import RC2AdaptResult, RunApplicabilityRecord, SCVObservation, SCVObservationBundle
from crisp.v3.path_channel import (
    load_pat_diagnostics_payload,
    project_path_payload,
)
from crisp.v3.policy import OBSERVATION_BUNDLE_SCHEMA_VERSION, PATH_CHANNEL_FAMILY, PATH_CHANNEL_NAME, SEMANTIC_POLICY_VERSION

_RC2_REFERENCE_KIND = "rc2_path_diagnostics_input"


def _project_rc2_path_payload(
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
    projected = project_path_payload(
        raw_payload=raw_payload,
        diagnostics_source=diagnostics_source,
        blockage_threshold=float(config.pat.blockage_pass_threshold),
        pathyes_state=pathyes_state,
    )
    applicability_records: list[RunApplicabilityRecord] = []
    if pathyes_state.goal_precheck_passed is False:
        applicability_records.append(
            RunApplicabilityRecord(
                channel_name=PATH_CHANNEL_NAME,
                family=PATH_CHANNEL_FAMILY,
                scope="run",
                applicable=False,
                reason_code="PAT_GOAL_INVALID",
                detail="goal_precheck_passed=false",
                diagnostics_source=diagnostics_source,
                diagnostics_payload={"goal_precheck_passed": False},
            )
        )
    payload = {
        "quantitative_metrics": {
            key: projected[key]
            for key in ("blockage_ratio", "numeric_resolution_limited", "persistence_confidence")
            if key in projected
        },
        "exploration_slice": {
            key: projected[key]
            for key in ("feasible_count", "apo_accessible_goal_voxels", "goal_voxel_count")
            if key in projected and projected.get(key) is not None
        },
        "witness_bundle": {
            "witness_pose_id": projected.get("witness_pose_id"),
            "obstruction_path_ids": projected.get("obstruction_path_ids", []),
            "path_family": PATH_CHANNEL_FAMILY,
        },
        "applicability": {
            key: projected[key]
            for key in (
                "goal_precheck_passed",
                "supported_path_model",
                "pathyes_rule1_applicability",
                "pathyes_mode_resolved",
                "pathyes_diagnostics_status",
                "pathyes_diagnostics_error_code",
            )
            if key in projected
        },
        "source_payload": {
            "pat_run_diagnostics_json": raw_payload.get("pat_run_diagnostics_json", {}),
        },
    }
    return payload, applicability_records


class RC2Adapter:
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
        projected_payload, applicability_records = _project_rc2_path_payload(
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
                    bridge_metrics={"adapter_kind": _RC2_REFERENCE_KIND},
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

