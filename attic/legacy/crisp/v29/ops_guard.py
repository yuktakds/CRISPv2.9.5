from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crisp.v29.inputs import normalize_run_mode

IGNORED_GENERATED_OUTPUTS = {"replay_audit.json"}


class OpsGuardError(RuntimeError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _load_json_object(path: Path, *, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [f"{label}_READ_ERROR:{exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"{label}_JSON_DECODE_ERROR:{exc.msg}@line{exc.lineno}:col{exc.colno}"]
    if not isinstance(payload, dict):
        return None, [f"{label}_NOT_OBJECT:{type(payload).__name__}"]
    return payload, []


def resolve_theta_runtime_policy(
    *,
    run_mode: str,
    pathyes_mode: str,
    theta_rule1_table_path: str | Path | None,
) -> str:
    normalized_run_mode = normalize_run_mode(run_mode)
    if normalized_run_mode in {"core+rule1", "core+rule1+cap", "full"} and pathyes_mode != "bootstrap":
        return "required"
    if theta_rule1_table_path is not None:
        return "warn"
    return "ignore"


def evaluate_manifest_artifact_state(
    run_dir: str | Path,
    manifest_payload: dict[str, Any],
) -> dict[str, Any]:
    run_path = Path(run_dir)
    completion_basis = manifest_payload.get("completion_basis_json", {})
    if not isinstance(completion_basis, dict):
        completion_basis = {}
    required_outputs_by_mode = completion_basis.get("required_outputs_by_mode", {})
    if not isinstance(required_outputs_by_mode, dict):
        required_outputs_by_mode = {}

    run_mode = str(manifest_payload.get("run_mode", "core-only"))
    required_outputs = required_outputs_by_mode.get(run_mode, [])
    if not isinstance(required_outputs, list):
        required_outputs = []

    required_output_names = [Path(name).name for name in required_outputs]
    missing_required_outputs = [
        name for name in required_output_names
        if not (run_path / name).exists()
    ]

    generated_outputs = manifest_payload.get("generated_outputs", [])
    if not isinstance(generated_outputs, list):
        generated_outputs = []
    generated_output_names = [Path(name).name for name in generated_outputs]
    missing_generated_outputs = [
        name for name in generated_output_names
        if name not in IGNORED_GENERATED_OUTPUTS and not (run_path / name).exists()
    ]

    return {
        "manifest_run_mode": run_mode,
        "required_outputs": required_output_names,
        "generated_outputs": generated_output_names,
        "missing_required_outputs": missing_required_outputs,
        "missing_generated_outputs": missing_generated_outputs,
        "stale_manifest_detected": bool(missing_required_outputs or missing_generated_outputs),
    }


def validate_preexisting_run_artifacts(
    out_dir: str | Path,
    *,
    expected_config_role: str,
    expected_run_mode: str,
) -> tuple[list[str], list[str], dict[str, Any]]:
    run_path = Path(out_dir)
    errors: list[str] = []
    warnings: list[str] = []
    diagnostics: dict[str, Any] = {
        "out_dir": str(run_path.resolve()),
        "expected_config_role": expected_config_role,
        "expected_run_mode": normalize_run_mode(expected_run_mode),
        "manifest_present": False,
    }

    if normalize_run_mode(expected_run_mode) == "full":
        warnings.append(
            "LOCAL_HEAVY_RUN_NOT_CI_REQUIRED: full runs are operator-only local checks and require the heavy-run checklist"
        )

    manifest_path = run_path / "run_manifest.json"
    if not manifest_path.exists():
        return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings)), diagnostics

    diagnostics["manifest_present"] = True
    manifest_payload, manifest_issues = _load_json_object(
        manifest_path,
        label="STALE_MANIFEST",
    )
    if manifest_payload is None:
        errors.extend(manifest_issues)
        return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings)), diagnostics

    observed_role = manifest_payload.get("target_config_role")
    observed_run_mode = manifest_payload.get("run_mode")
    diagnostics["observed_manifest_role"] = observed_role
    diagnostics["observed_manifest_run_mode"] = observed_run_mode

    if observed_role is not None and str(observed_role) != expected_config_role:
        errors.append(
            "STALE_MANIFEST_ROLE_MISMATCH:"
            f"expected={expected_config_role!r} observed={str(observed_role)!r}"
        )
    normalized_run_mode = normalize_run_mode(expected_run_mode)
    if observed_run_mode is not None and str(observed_run_mode) != normalized_run_mode:
        errors.append(
            "STALE_MANIFEST_RUN_MODE_MISMATCH:"
            f"expected={normalized_run_mode!r} observed={str(observed_run_mode)!r}"
        )

    artifact_state = evaluate_manifest_artifact_state(run_path, manifest_payload)
    diagnostics["artifact_state"] = artifact_state
    missing_required_outputs = artifact_state["missing_required_outputs"]
    missing_generated_outputs = artifact_state["missing_generated_outputs"]
    if missing_required_outputs:
        errors.append(
            f"STALE_MANIFEST_MISSING_REQUIRED_ARTIFACTS:{missing_required_outputs}"
        )
    if missing_generated_outputs:
        errors.append(
            f"STALE_MANIFEST_MISSING_GENERATED_ARTIFACTS:{missing_generated_outputs}"
        )
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings)), diagnostics
