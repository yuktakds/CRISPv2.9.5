from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Literal

from crisp.config.models import SUPPORTED_PATH_MODELS, TargetConfig
from crisp.v29.contracts import PathYesState

PathYesMode = Literal['bootstrap', 'pat-backed']


def pathyes_bootstrap_state(
    *,
    config: TargetConfig,
    pathyes_force_false: bool = False,
) -> PathYesState:
    supported = config.pat.path_model in SUPPORTED_PATH_MODELS
    skip_code = 'SKIP_PATHYES_BOOTSTRAP' if pathyes_force_false else None
    diagnostics: dict[str, Any] = {
        'mode': 'bootstrap',
        'reason': 'PAT_RUNTIME_ABSENT',
    }
    if pathyes_force_false:
        diagnostics['pathyes_force_false'] = True
    return PathYesState(
        supported_path_model=supported,
        goal_precheck_passed=None,
        pat_run_diagnostics_json=diagnostics,
        rule1_applicability='PATH_NOT_EVALUABLE',
        skip_code=skip_code,
    )


def pathyes_pat_backed_state(
    *,
    config: TargetConfig,
    pat_diagnostics_path: str | Path,
    pathyes_force_false: bool = False,
) -> PathYesState:
    payload = json.loads(Path(pat_diagnostics_path).read_text(encoding='utf-8'))
    supported = bool(payload.get('supported_path_model', config.pat.path_model in SUPPORTED_PATH_MODELS))
    goal_precheck = payload.get('goal_precheck_passed')
    if goal_precheck is not None:
        goal_precheck = bool(goal_precheck)
    diagnostics = dict(payload.get('pat_run_diagnostics_json') or {})
    diagnostics.setdefault('mode', 'pat-backed')
    diagnostics.setdefault('source', str(Path(pat_diagnostics_path)))
    if pathyes_force_false:
        diagnostics['pathyes_force_false'] = True
        goal_precheck = False
    if not supported:
        applicability = 'PATH_NOT_EVALUABLE'
    elif goal_precheck is True:
        applicability = 'PATH_EVALUABLE'
    else:
        applicability = 'PATH_NOT_EVALUABLE'
    return PathYesState(
        supported_path_model=supported,
        goal_precheck_passed=goal_precheck,
        pat_run_diagnostics_json=diagnostics,
        rule1_applicability=applicability,
        skip_code=None,
    )


def resolve_pathyes_state(
    *,
    config: TargetConfig,
    mode: PathYesMode = 'bootstrap',
    pat_diagnostics_path: str | Path | None = None,
    pathyes_force_false: bool = False,
) -> PathYesState:
    if mode == 'bootstrap':
        return pathyes_bootstrap_state(config=config, pathyes_force_false=pathyes_force_false)
    if pat_diagnostics_path is None:
        raise ValueError('pat_diagnostics_path is required for mode="pat-backed"')
    return pathyes_pat_backed_state(
        config=config,
        pat_diagnostics_path=pat_diagnostics_path,
        pathyes_force_false=pathyes_force_false,
    )
