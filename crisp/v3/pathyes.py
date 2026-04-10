"""PathYes 状態管理 (v3 自己完結版)。

crisp.v29 に依存しない。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from crisp.config.models import SUPPORTED_PATH_MODELS, TargetConfig

PathYesMode = Literal["bootstrap", "pat-backed"]

PAT_DIAGNOSTICS_MISSING_SKIP_CODE = "SKIP_PATHYES_PAT_DIAGNOSTICS_MISSING"
PAT_DIAGNOSTICS_INVALID_SKIP_CODE = "SKIP_PATHYES_PAT_DIAGNOSTICS_INVALID"
PAT_GOAL_PRECHECK_SOURCE = "pat_diagnostics.goal_precheck_passed"
_PAT_STATE_SOURCE = "pat_diagnostics_json"
_BOOTSTRAP_STATE_SOURCE = "bootstrap_stub"
_FORBIDDEN_PAT_DIAGNOSTIC_FIELDS = frozenset({
    "pat_verdict",
    "pat_reason",
    "pat_reason_code",
    "core_verdict",
    "core_reason",
    "core_reason_code",
    "legacy_core_final_verdict",
})


@dataclass(frozen=True, slots=True)
class PathYesState:
    supported_path_model: bool
    goal_precheck_passed: bool | None
    pat_run_diagnostics_json: dict[str, Any]
    rule1_applicability: str
    skip_code: str | None = None
    mode: str | None = None
    source: str | None = None
    diagnostics_status: str | None = None
    diagnostics_error_code: str | None = None
    diagnostics_source_path: str | None = None
    sanitized_fields_removed: list[str] = field(default_factory=list)


def pathyes_contract_fields(state: PathYesState) -> dict[str, Any]:
    return {
        "pathyes_mode_resolved": state.mode,
        "pathyes_state_source": state.source,
        "pathyes_diagnostics_status": state.diagnostics_status,
        "pathyes_diagnostics_error_code": state.diagnostics_error_code,
        "pathyes_diagnostics_source": state.diagnostics_source_path,
        "pathyes_goal_precheck_passed": state.goal_precheck_passed,
        "pathyes_rule1_applicability": state.rule1_applicability,
        "pathyes_skip_code": state.skip_code,
    }


def _pathyes_state(
    *,
    supported_path_model: bool,
    goal_precheck_passed: bool | None,
    pat_run_diagnostics_json: dict[str, Any],
    rule1_applicability: str,
    skip_code: str | None,
    mode: str,
    source: str,
    diagnostics_status: str,
    diagnostics_error_code: str | None = None,
    diagnostics_source_path: str | None = None,
    sanitized_fields_removed: list[str] | None = None,
) -> PathYesState:
    return PathYesState(
        supported_path_model=supported_path_model,
        goal_precheck_passed=goal_precheck_passed,
        pat_run_diagnostics_json=pat_run_diagnostics_json,
        rule1_applicability=rule1_applicability,
        skip_code=skip_code,
        mode=mode,
        source=source,
        diagnostics_status=diagnostics_status,
        diagnostics_error_code=diagnostics_error_code,
        diagnostics_source_path=diagnostics_source_path,
        sanitized_fields_removed=[] if sanitized_fields_removed is None else list(sanitized_fields_removed),
    )


def _bootstrap_diagnostics(*, pathyes_force_false: bool) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "mode": "bootstrap",
        "reason": "PAT_RUNTIME_ABSENT",
        "diagnostics_status": "bootstrap",
        "goal_precheck_source": None,
    }
    if pathyes_force_false:
        diagnostics["pathyes_force_false"] = True
    return diagnostics


def _pathyes_pat_skip_state(
    *,
    config: TargetConfig,
    pat_diagnostics_path: str | Path | None,
    diagnostics_status: str,
    diagnostics_error_code: str,
    skip_code: str,
    message: str,
) -> PathYesState:
    source_path = None if pat_diagnostics_path is None else str(Path(pat_diagnostics_path))
    diagnostics: dict[str, Any] = {
        "mode": "pat-backed",
        "source": source_path,
        "diagnostics_status": diagnostics_status,
        "diagnostics_error_code": diagnostics_error_code,
        "goal_precheck_source": PAT_GOAL_PRECHECK_SOURCE,
        "message": message,
    }
    return _pathyes_state(
        supported_path_model=config.pat.path_model in SUPPORTED_PATH_MODELS,
        goal_precheck_passed=None,
        pat_run_diagnostics_json=diagnostics,
        rule1_applicability="PATH_NOT_EVALUABLE",
        skip_code=skip_code,
        mode="pat-backed",
        source=_PAT_STATE_SOURCE,
        diagnostics_status=diagnostics_status,
        diagnostics_error_code=diagnostics_error_code,
        diagnostics_source_path=source_path,
    )


def _sanitize_pat_diagnostics(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    raw_diagnostics_payload = payload.get("pat_run_diagnostics_json")
    diagnostics_payload = {} if raw_diagnostics_payload is None else raw_diagnostics_payload
    if not isinstance(diagnostics_payload, dict):
        raise TypeError("pat_run_diagnostics_json must be an object when present")

    removed_fields = sorted(
        {str(key) for key in payload if key in _FORBIDDEN_PAT_DIAGNOSTIC_FIELDS}
        | {str(key) for key in diagnostics_payload if key in _FORBIDDEN_PAT_DIAGNOSTIC_FIELDS}
    )
    diagnostics = {
        str(key): value
        for key, value in diagnostics_payload.items()
        if key not in _FORBIDDEN_PAT_DIAGNOSTIC_FIELDS
    }
    return diagnostics, removed_fields


def _loaded_pat_diagnostics(
    *,
    payload: dict[str, Any],
    pat_diagnostics_path: str | Path,
    supported_path_model: bool,
    goal_precheck_passed: bool,
    pathyes_force_false: bool,
    sanitized_fields_removed: list[str],
) -> dict[str, Any]:
    diagnostics, removed_fields = _sanitize_pat_diagnostics(payload)
    if removed_fields:
        sanitized_fields_removed.extend(removed_fields)
    diagnostics.update({
        "mode": "pat-backed",
        "source": str(Path(pat_diagnostics_path)),
        "diagnostics_status": "loaded",
        "goal_precheck_source": PAT_GOAL_PRECHECK_SOURCE,
        "supported_path_model": supported_path_model,
        "goal_precheck_passed_observed": goal_precheck_passed,
    })
    if sanitized_fields_removed:
        diagnostics["sanitized_fields_removed"] = sorted(set(sanitized_fields_removed))
    if pathyes_force_false:
        diagnostics["pathyes_force_false"] = True
    return diagnostics


def pathyes_bootstrap_state(
    *,
    config: TargetConfig,
    pathyes_force_false: bool = False,
) -> PathYesState:
    supported = config.pat.path_model in SUPPORTED_PATH_MODELS
    skip_code = "SKIP_PATHYES_BOOTSTRAP" if pathyes_force_false else None
    return _pathyes_state(
        supported_path_model=supported,
        goal_precheck_passed=None,
        pat_run_diagnostics_json=_bootstrap_diagnostics(pathyes_force_false=pathyes_force_false),
        rule1_applicability="PATH_NOT_EVALUABLE",
        skip_code=skip_code,
        mode="bootstrap",
        source=_BOOTSTRAP_STATE_SOURCE,
        diagnostics_status="bootstrap",
    )


def pathyes_pat_backed_state(
    *,
    config: TargetConfig,
    pat_diagnostics_path: str | Path,
    pathyes_force_false: bool = False,
) -> PathYesState:
    path = Path(pat_diagnostics_path)
    if not path.exists():
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=path,
            diagnostics_status="missing",
            diagnostics_error_code="PAT_DIAGNOSTICS_FILE_NOT_FOUND",
            skip_code=PAT_DIAGNOSTICS_MISSING_SKIP_CODE,
            message=f"{path} not found",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=path,
            diagnostics_status="invalid",
            diagnostics_error_code="PAT_DIAGNOSTICS_READ_ERROR",
            skip_code=PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
            message=str(exc),
        )
    if not text.strip():
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=path,
            diagnostics_status="invalid",
            diagnostics_error_code="PAT_DIAGNOSTICS_EMPTY_FILE",
            skip_code=PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
            message="pat diagnostics file is empty",
        )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=path,
            diagnostics_status="invalid",
            diagnostics_error_code="PAT_DIAGNOSTICS_JSON_DECODE_ERROR",
            skip_code=PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
            message=f"{exc.msg}@line{exc.lineno}:col{exc.colno}",
        )
    if not isinstance(payload, dict):
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=path,
            diagnostics_status="invalid",
            diagnostics_error_code="PAT_DIAGNOSTICS_NOT_OBJECT",
            skip_code=PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
            message=type(payload).__name__,
        )

    goal_precheck_raw = payload.get("goal_precheck_passed")
    if not isinstance(goal_precheck_raw, bool):
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=path,
            diagnostics_status="invalid",
            diagnostics_error_code="PAT_DIAGNOSTICS_GOAL_PRECHECK_INVALID",
            skip_code=PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
            message="goal_precheck_passed must be a boolean",
        )
    supported_raw = payload.get("supported_path_model", config.pat.path_model in SUPPORTED_PATH_MODELS)
    if not isinstance(supported_raw, bool):
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=path,
            diagnostics_status="invalid",
            diagnostics_error_code="PAT_DIAGNOSTICS_SUPPORTED_PATH_MODEL_INVALID",
            skip_code=PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
            message="supported_path_model must be a boolean when present",
        )

    sanitized_fields_removed: list[str] = []
    try:
        diagnostics = _loaded_pat_diagnostics(
            payload=payload,
            pat_diagnostics_path=path,
            supported_path_model=supported_raw,
            goal_precheck_passed=goal_precheck_raw,
            pathyes_force_false=pathyes_force_false,
            sanitized_fields_removed=sanitized_fields_removed,
        )
    except TypeError as exc:
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=path,
            diagnostics_status="invalid",
            diagnostics_error_code="PAT_DIAGNOSTICS_SCHEMA_INVALID",
            skip_code=PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
            message=str(exc),
        )

    goal_precheck = False if pathyes_force_false else goal_precheck_raw
    applicability = "PATH_EVALUABLE" if supported_raw and goal_precheck else "PATH_NOT_EVALUABLE"
    return _pathyes_state(
        supported_path_model=supported_raw,
        goal_precheck_passed=goal_precheck,
        pat_run_diagnostics_json=diagnostics,
        rule1_applicability=applicability,
        skip_code=None,
        mode="pat-backed",
        source=_PAT_STATE_SOURCE,
        diagnostics_status="loaded",
        diagnostics_source_path=str(path),
        sanitized_fields_removed=sanitized_fields_removed,
    )


def resolve_pathyes_state(
    *,
    config: TargetConfig,
    mode: PathYesMode = "bootstrap",
    pat_diagnostics_path: str | Path | None = None,
    pathyes_force_false: bool = False,
) -> PathYesState:
    if mode == "bootstrap":
        return pathyes_bootstrap_state(config=config, pathyes_force_false=pathyes_force_false)
    if pat_diagnostics_path is None:
        return _pathyes_pat_skip_state(
            config=config,
            pat_diagnostics_path=None,
            diagnostics_status="missing",
            diagnostics_error_code="PAT_DIAGNOSTICS_PATH_NOT_PROVIDED",
            skip_code=PAT_DIAGNOSTICS_MISSING_SKIP_CODE,
            message='pat_diagnostics_path is required for mode="pat-backed"',
        )
    return pathyes_pat_backed_state(
        config=config,
        pat_diagnostics_path=pat_diagnostics_path,
        pathyes_force_false=pathyes_force_false,
    )
