from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crisp.config.models import SUPPORTED_PATH_MODELS, TargetConfig
from crisp.v29.pathyes import resolve_pathyes_state
from crisp.v3.contracts import (
    ChannelEvaluationResult,
    ChannelEvidence,
    EvidenceState,
    RunApplicabilityRecord,
)
from crisp.v3.policy import PATH_CHANNEL_FAMILY, PATH_CHANNEL_NAME

_PAT_PATH_MISSING = "PAT_DIAGNOSTICS_PATH_NOT_PROVIDED"
_PAT_PATH_NOT_FOUND = "PAT_DIAGNOSTICS_FILE_NOT_FOUND"
_PAT_PATH_INVALID = "PAT_DIAGNOSTICS_INVALID"
_PAT_BLOCKAGE_RATIO_INVALID = "PAT_BLOCKAGE_RATIO_INVALID"
_PAT_NUMERIC_RESOLUTION_INVALID = "PAT_NUMERIC_RESOLUTION_INVALID"
_PAT_UNSUPPORTED_PATH_MODEL = "PAT_UNSUPPORTED_PATH_MODEL"
_PAT_GOAL_INVALID = "PAT_GOAL_INVALID"
_PAT_GOAL_PRECHECK_INVALID = "PAT_GOAL_PRECHECK_INVALID"
_PAT_APO_BASELINE_ABSENT = "PAT_APO_BASELINE_ABSENT"


def _applicability_record(
    *,
    reason_code: str,
    detail: str | None,
    diagnostics_source: str | None,
    diagnostics_payload: dict[str, Any],
) -> RunApplicabilityRecord:
    return RunApplicabilityRecord(
        channel_name=PATH_CHANNEL_NAME,
        family=PATH_CHANNEL_FAMILY,
        scope="run",
        applicable=False,
        reason_code=reason_code,
        detail=detail,
        diagnostics_source=diagnostics_source,
        diagnostics_payload=diagnostics_payload,
    )


def _diagnostics_view(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("pat_run_diagnostics_json")
    if isinstance(nested, dict):
        return nested
    return {}


def _lookup(payload: dict[str, Any], key: str) -> Any:
    if key in payload:
        return payload[key]
    diagnostics = _diagnostics_view(payload)
    return diagnostics.get(key)


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


def _normalize_str_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def load_pat_diagnostics_payload(path: str | Path | None) -> tuple[dict[str, Any] | None, RunApplicabilityRecord | None]:
    if path is None:
        return None, _applicability_record(
            reason_code=_PAT_PATH_MISSING,
            detail="pat_diagnostics_path is required for the v3 path sidecar",
            diagnostics_source=None,
            diagnostics_payload={},
        )

    source = str(Path(path))
    pat_path = Path(path)
    if not pat_path.exists():
        return None, _applicability_record(
            reason_code=_PAT_PATH_NOT_FOUND,
            detail=f"{pat_path} not found",
            diagnostics_source=source,
            diagnostics_payload={},
        )

    try:
        raw_text = pat_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, _applicability_record(
            reason_code=_PAT_PATH_INVALID,
            detail=str(exc),
            diagnostics_source=source,
            diagnostics_payload={},
        )

    if not raw_text.strip():
        return None, _applicability_record(
            reason_code=_PAT_PATH_INVALID,
            detail="pat diagnostics file is empty",
            diagnostics_source=source,
            diagnostics_payload={},
        )

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, _applicability_record(
            reason_code=_PAT_PATH_INVALID,
            detail=f"{exc.msg}@line{exc.lineno}:col{exc.colno}",
            diagnostics_source=source,
            diagnostics_payload={},
        )

    if not isinstance(payload, dict):
        return None, _applicability_record(
            reason_code=_PAT_PATH_INVALID,
            detail=f"expected object, got {type(payload).__name__}",
            diagnostics_source=source,
            diagnostics_payload={},
        )

    return payload, None


def project_path_payload(
    *,
    raw_payload: dict[str, Any],
    diagnostics_source: str,
    blockage_threshold: float,
    pathyes_state: Any,
) -> dict[str, Any]:
    # Do not use pathyes_contract_fields() as the source of truth here; it drops
    # continuous PAT quantities that the sidecar needs to preserve.
    numeric_resolution_limited_raw = _lookup(raw_payload, "numeric_resolution_limited")
    blockage_ratio_raw = _lookup(raw_payload, "blockage_ratio")
    persistence_confidence_raw = _lookup(raw_payload, "persistence_confidence")
    witness_pose_id = _lookup(raw_payload, "witness_pose_id")
    obstruction_path_ids = _normalize_str_list(_lookup(raw_payload, "obstruction_path_ids"))
    apo_accessible_goal_voxels = _normalize_int(_lookup(raw_payload, "apo_accessible_goal_voxels"))
    goal_voxel_count = _normalize_int(_lookup(raw_payload, "goal_voxel_count"))
    feasible_count = _normalize_int(_lookup(raw_payload, "feasible_count"))
    numeric_resolution_limited = (
        None
        if numeric_resolution_limited_raw is None
        else bool(numeric_resolution_limited_raw)
    )
    blockage_ratio = _normalize_float(blockage_ratio_raw)
    persistence_confidence = _normalize_float(persistence_confidence_raw)
    quantitative_metrics = {
        "max_blockage_ratio": blockage_ratio,
        "numeric_resolution_limited": numeric_resolution_limited,
        "persistence_confidence": persistence_confidence,
    }
    exploration_slice = {
        "apo_accessible_goal_voxels": apo_accessible_goal_voxels,
        "goal_voxel_count": goal_voxel_count,
        "feasible_count": feasible_count,
    }
    witness_bundle = {
        "witness_pose_id": witness_pose_id,
        "obstruction_path_ids": obstruction_path_ids,
        "path_family": PATH_CHANNEL_FAMILY,
    }
    applicability = {
        "goal_precheck_passed": pathyes_state.goal_precheck_passed,
        "goal_precheck_reason": _lookup(raw_payload, "goal_precheck_reason"),
        "supported_path_model": pathyes_state.supported_path_model,
        "pathyes_rule1_applicability": pathyes_state.rule1_applicability,
        "pathyes_mode_resolved": pathyes_state.mode,
        "pathyes_diagnostics_status": pathyes_state.diagnostics_status,
        "pathyes_diagnostics_error_code": pathyes_state.diagnostics_error_code,
    }

    projected = {
        "quantitative_metrics": quantitative_metrics,
        "exploration_slice": exploration_slice,
        "witness_bundle": witness_bundle,
        "applicability": applicability,
        "max_blockage_ratio": blockage_ratio,
        "blockage_ratio": blockage_ratio,
        "witness_pose_id": witness_pose_id,
        "obstruction_path_ids": obstruction_path_ids,
        "apo_accessible_goal_voxels": apo_accessible_goal_voxels,
        "goal_voxel_count": goal_voxel_count,
        "feasible_count": feasible_count,
        "numeric_resolution_limited": numeric_resolution_limited,
        "persistence_confidence": persistence_confidence,
        "blockage_pass_threshold": blockage_threshold,
        "goal_precheck_passed": applicability["goal_precheck_passed"],
        "goal_precheck_reason": applicability["goal_precheck_reason"],
        "supported_path_model": applicability["supported_path_model"],
        "pathyes_rule1_applicability": pathyes_state.rule1_applicability,
        "pathyes_mode_resolved": pathyes_state.mode,
        "pathyes_state_source": pathyes_state.source,
        "pathyes_diagnostics_status": pathyes_state.diagnostics_status,
        "pathyes_diagnostics_error_code": pathyes_state.diagnostics_error_code,
        "pathyes_diagnostics_source": pathyes_state.diagnostics_source_path,
        "diagnostics_source": diagnostics_source,
    }
    return projected


def resolve_path_evidence_state(
    *,
    blockage_ratio: float,
    blockage_threshold: float,
    numeric_resolution_limited: bool | None,
) -> EvidenceState:
    if numeric_resolution_limited is True:
        return EvidenceState.INSUFFICIENT
    if blockage_ratio >= blockage_threshold:
        return EvidenceState.SUPPORTED
    return EvidenceState.REFUTED


class PathEvidenceChannel:
    def evaluate(
        self,
        *,
        config: TargetConfig,
        pat_diagnostics_path: str | Path | None,
        pathyes_force_false: bool = False,
    ) -> ChannelEvaluationResult:
        payload, load_record = load_pat_diagnostics_payload(pat_diagnostics_path)
        if load_record is not None:
            return ChannelEvaluationResult(evidence=None, applicability_records=[load_record])

        assert payload is not None
        diagnostics_source = str(Path(pat_diagnostics_path))
        supported_path_model = _lookup(
            payload,
            "supported_path_model",
        )
        if supported_path_model is None:
            supported_path_model = config.pat.path_model in SUPPORTED_PATH_MODELS
        if not isinstance(supported_path_model, bool):
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[
                    _applicability_record(
                        reason_code=_PAT_UNSUPPORTED_PATH_MODEL,
                        detail="supported_path_model must be a boolean when present",
                        diagnostics_source=diagnostics_source,
                        diagnostics_payload={},
                    )
                ],
                diagnostics_payload=payload,
            )
        if config.pat.path_model != PATH_CHANNEL_FAMILY or supported_path_model is False:
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[
                    _applicability_record(
                        reason_code=_PAT_UNSUPPORTED_PATH_MODEL,
                        detail=f"formal family is {PATH_CHANNEL_FAMILY}, observed={config.pat.path_model}",
                        diagnostics_source=diagnostics_source,
                        diagnostics_payload={"supported_path_model": supported_path_model},
                    )
                ],
                diagnostics_payload=payload,
            )

        goal_precheck_passed = _lookup(payload, "goal_precheck_passed")
        if not isinstance(goal_precheck_passed, bool):
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[
                    _applicability_record(
                        reason_code=_PAT_GOAL_PRECHECK_INVALID,
                        detail="goal_precheck_passed must be a boolean",
                        diagnostics_source=diagnostics_source,
                        diagnostics_payload={},
                    )
                ],
                diagnostics_payload=payload,
            )
        if pathyes_force_false or not goal_precheck_passed:
            detail = (
                "pathyes_force_false requested"
                if pathyes_force_false
                else "goal_precheck_passed=false"
            )
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[
                    _applicability_record(
                        reason_code=_PAT_GOAL_INVALID,
                        detail=detail,
                        diagnostics_source=diagnostics_source,
                        diagnostics_payload={"goal_precheck_passed": goal_precheck_passed},
                    )
                ],
                diagnostics_payload=payload,
            )

        apo_accessible_goal_voxels = _normalize_int(_lookup(payload, "apo_accessible_goal_voxels"))
        if apo_accessible_goal_voxels is None or apo_accessible_goal_voxels < 1:
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[
                    _applicability_record(
                        reason_code=_PAT_APO_BASELINE_ABSENT,
                        detail="apo_accessible_goal_voxels must be >= 1",
                        diagnostics_source=diagnostics_source,
                        diagnostics_payload={"apo_accessible_goal_voxels": apo_accessible_goal_voxels},
                    )
                ],
                diagnostics_payload=payload,
            )

        blockage_ratio = _normalize_float(_lookup(payload, "blockage_ratio"))
        if blockage_ratio is None:
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[
                    _applicability_record(
                        reason_code=_PAT_BLOCKAGE_RATIO_INVALID,
                        detail="blockage_ratio must be numeric",
                        diagnostics_source=diagnostics_source,
                        diagnostics_payload={"blockage_ratio": _lookup(payload, "blockage_ratio")},
                    )
                ],
                diagnostics_payload=payload,
            )

        numeric_resolution_limited_raw = _lookup(payload, "numeric_resolution_limited")
        if numeric_resolution_limited_raw is not None and not isinstance(numeric_resolution_limited_raw, bool):
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[
                    _applicability_record(
                        reason_code=_PAT_NUMERIC_RESOLUTION_INVALID,
                        detail="numeric_resolution_limited must be a boolean when present",
                        diagnostics_source=diagnostics_source,
                        diagnostics_payload={"numeric_resolution_limited": numeric_resolution_limited_raw},
                    )
                ],
                diagnostics_payload=payload,
            )

        pathyes_state = resolve_pathyes_state(
            config=config,
            mode="pat-backed",
            pat_diagnostics_path=pat_diagnostics_path,
            pathyes_force_false=pathyes_force_false,
        )
        projected_payload = project_path_payload(
            raw_payload=payload,
            diagnostics_source=diagnostics_source,
            blockage_threshold=float(config.pat.blockage_pass_threshold),
            pathyes_state=pathyes_state,
        )
        state = resolve_path_evidence_state(
            blockage_ratio=blockage_ratio,
            blockage_threshold=float(config.pat.blockage_pass_threshold),
            numeric_resolution_limited=projected_payload["quantitative_metrics"]["numeric_resolution_limited"],
        )
        bridge_metrics = {
            "blockage_pass_threshold": float(config.pat.blockage_pass_threshold),
            "pathyes_mode_resolved": pathyes_state.mode,
        }
        persistence_confidence = projected_payload.get("persistence_confidence")
        if persistence_confidence is not None:
            bridge_metrics["persistence_confidence"] = persistence_confidence

        evidence = ChannelEvidence(
            channel_name=PATH_CHANNEL_NAME,
            family=PATH_CHANNEL_FAMILY,
            state=state,
            payload=projected_payload,
            source=diagnostics_source,
            bridge_metrics=bridge_metrics,
        )
        return ChannelEvaluationResult(
            evidence=evidence,
            applicability_records=[],
            diagnostics_payload=payload,
        )
