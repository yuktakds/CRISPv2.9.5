from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from crisp.config.loader import load_target_config
from crisp.v29.inputs import normalize_run_mode

_CAP_TRUTH_SOURCE = "cap_batch_eval.json"


class IntegratedCliGuardError(RuntimeError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class IntegratedRunContract:
    run_mode_requested: str
    run_mode_resolved: str
    config_path: str
    config_role: str
    expected_config_role: str | None
    comparison_type: str
    comparison_type_source: str
    truth_source: str
    core_frozen: bool


def load_integrated_options(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise TypeError(f"integrated config must be a mapping, got {type(payload).__name__}")
    return payload


def truth_source_for_run_mode(run_mode: str) -> str:
    normalized = normalize_run_mode(run_mode)
    if normalized in {"core+rule1+cap", "full"}:
        return _CAP_TRUTH_SOURCE
    return "n/a"


def resolve_integrated_run_contract(
    *,
    config_path: str | Path,
    integrated_config_path: str | Path | None,
    run_mode: str,
    expected_config_role: str | None = None,
    comparison_type_override: str | None = None,
    context: str = "run-integrated-v29",
) -> IntegratedRunContract:
    resolved_config_path = Path(config_path).resolve()
    config = load_target_config(resolved_config_path)
    normalized_run_mode = normalize_run_mode(run_mode)

    if expected_config_role is not None and config.config_role != expected_config_role:
        raise IntegratedCliGuardError(
            code="CLI_CONFIG_ROLE_MISMATCH",
            message=(
                f"{context} expected config_role={expected_config_role!r}, "
                f"but {resolved_config_path} is {config.config_role!r}"
            ),
        )

    integrated = load_integrated_options(integrated_config_path)
    requested_comparison_type = comparison_type_override
    if requested_comparison_type is None and integrated.get("comparison_type") is not None:
        requested_comparison_type = str(integrated["comparison_type"])

    if requested_comparison_type is not None:
        comparison_type = config.assert_allows_comparison(
            requested_comparison_type,
            context=context,
            config_path=resolved_config_path,
        ).value
        comparison_type_source = "explicit_override"
    else:
        comparison_type = config.default_comparison_type().value
        comparison_type_source = "config_role_default"

    return IntegratedRunContract(
        run_mode_requested=run_mode,
        run_mode_resolved=normalized_run_mode,
        config_path=str(resolved_config_path),
        config_role=config.config_role,
        expected_config_role=expected_config_role,
        comparison_type=comparison_type,
        comparison_type_source=comparison_type_source,
        truth_source=truth_source_for_run_mode(normalized_run_mode),
        core_frozen=config.frozen_for_regression,
    )
