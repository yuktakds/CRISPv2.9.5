from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from crisp.repro.hashing import sha256_file, sha256_json
from crisp.v3.public_scope_validator import validate_keep_path_rc_run_directory

M2_ROLLBACK_DRILL_REPORT_ARTIFACT = "m2_rollback_drill_report.json"
M2_REHEARSAL_REPORT_ARTIFACT = "m2_rehearsal_report.json"
M2_POST_CUTOVER_MONITORING_ARTIFACT = "m2_post_cutover_monitoring_report.json"
_DEFAULT_HASH_ARTIFACTS = (
    "output_inventory.json",
    "v3_sidecar/verdict_record.json",
    "v3_sidecar/sidecar_run_record.json",
    "v3_sidecar/generator_manifest.json",
    "v3_sidecar/vn06_readiness.json",
)
_ROUND_TRIP_ARTIFACTS = (
    "output_inventory.json",
    "v3_sidecar/verdict_record.json",
    "v3_sidecar/sidecar_run_record.json",
    "v3_sidecar/bridge_comparison_summary.json",
    "v3_sidecar/vn06_readiness.json",
)


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected object payload at {path}, got {type(payload).__name__}")
    return payload


def _normalize_value(value: Any, *, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        normalized = value
        for raw, token in replacements.items():
            normalized = normalized.replace(raw, token)
        return normalized
    if isinstance(value, list):
        return [_normalize_value(item, replacements=replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: _normalize_value(item, replacements=replacements)
            for key, item in value.items()
        }
    return value


def collect_m2_authority_hashes(
    run_dir: str | Path,
    *,
    relative_paths: Sequence[str] = _DEFAULT_HASH_ARTIFACTS,
) -> dict[str, str]:
    run_path = Path(run_dir)
    hashes: dict[str, str] = {}
    for relative_path in relative_paths:
        path = run_path / relative_path
        if path.exists():
            hashes[relative_path] = sha256_file(path)
    return hashes


def _normalized_artifact_digest(
    *,
    run_dir: Path,
    relative_path: str,
    peer_run_dir: Path,
) -> str | None:
    path = run_dir / relative_path
    if not path.exists():
        return None
    replacements = {
        str(run_dir): "<RUN_DIR>",
        run_dir.as_posix(): "<RUN_DIR>",
        str(peer_run_dir): "<PEER_RUN_DIR>",
        peer_run_dir.as_posix(): "<PEER_RUN_DIR>",
    }
    if path.suffix == ".json":
        return sha256_json(
            _normalize_value(_load_json_object(path), replacements=replacements)
        )
    if path.suffix == ".md":
        return sha256_json(
            {"text": _normalize_value(path.read_text(encoding="utf-8"), replacements=replacements)}
        )
    return sha256_json(
        {"text": _normalize_value(path.read_text(encoding="utf-8"), replacements=replacements)}
    )


def execute_m2_rollback_drill(run_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir)
    baseline_hashes = collect_m2_authority_hashes(run_path)
    verdict_record = _load_json_object(run_path / "v3_sidecar" / "verdict_record.json")
    sidecar_run_record = _load_json_object(run_path / "v3_sidecar" / "sidecar_run_record.json")
    readiness = _load_json_object(run_path / "v3_sidecar" / "vn06_readiness.json")
    validator_errors, validator_warnings, validator_diagnostics = validate_keep_path_rc_run_directory(run_path)

    injected_fault_verdict = deepcopy(verdict_record)
    injected_fault_verdict["comparator_scope"] = "INJECTED_FAULT"
    injected_mismatches = validator_diagnostics.get("dual_write_mismatches", [])
    if not injected_mismatches:
        from crisp.v3.vn06_readiness import collect_verdict_record_dual_write_mismatches

        injected_mismatches = list(
            collect_verdict_record_dual_write_mismatches(
                verdict_record=injected_fault_verdict,
                sidecar_run_record=sidecar_run_record,
            )
        )

    post_hashes = collect_m2_authority_hashes(run_path)
    hashes_unchanged = baseline_hashes == post_hashes
    output_inventory_unchanged = baseline_hashes.get("output_inventory.json") == post_hashes.get("output_inventory.json")
    rollback_projection = {
        "canonical_layer0_authority_artifact": "sidecar_run_record.json",
        "verdict_record_authority_transfer_complete": False,
        "sidecar_run_record_role": "canonical_layer0_authority",
    }
    return {
        "run_dir": str(run_path.resolve()),
        "baseline_hashes": baseline_hashes,
        "post_hashes": post_hashes,
        "hashes_unchanged": hashes_unchanged,
        "validator_errors": validator_errors,
        "validator_warnings": validator_warnings,
        "operator_surface_inactive": bool(readiness.get("current_run_operator_surface_inactive")),
        "dual_write_mismatch_count": int(readiness.get("dual_write_mismatch_count", 1)),
        "injected_fault_field": "comparator_scope",
        "injected_fault_value": "INJECTED_FAULT",
        "injected_fault_mismatches": injected_mismatches,
        "injected_fault_detected": "comparator_scope" in injected_mismatches,
        "output_inventory_unchanged": output_inventory_unchanged,
        "rollback_projection": rollback_projection,
        "drill_passed": (
            not validator_errors
            and bool(readiness.get("current_run_operator_surface_inactive"))
            and int(readiness.get("dual_write_mismatch_count", 1)) == 0
            and "comparator_scope" in injected_mismatches
            and output_inventory_unchanged
            and hashes_unchanged
        ),
    }


def execute_m2_rehearsal(
    primary_run_dir: str | Path,
    rerun_run_dir: str | Path,
) -> dict[str, Any]:
    primary_path = Path(primary_run_dir)
    rerun_path = Path(rerun_run_dir)
    primary_readiness = _load_json_object(primary_path / "v3_sidecar" / "vn06_readiness.json")
    rerun_readiness = _load_json_object(rerun_path / "v3_sidecar" / "vn06_readiness.json")
    primary_errors, primary_warnings, primary_diagnostics = validate_keep_path_rc_run_directory(primary_path)
    rerun_errors, rerun_warnings, rerun_diagnostics = validate_keep_path_rc_run_directory(rerun_path)
    primary_hashes = collect_m2_authority_hashes(primary_path)
    rerun_hashes = collect_m2_authority_hashes(rerun_path)

    normalized_primary: dict[str, str | None] = {}
    normalized_rerun: dict[str, str | None] = {}
    for relative_path in _ROUND_TRIP_ARTIFACTS:
        normalized_primary[relative_path] = _normalized_artifact_digest(
            run_dir=primary_path,
            relative_path=relative_path,
            peer_run_dir=rerun_path,
        )
        normalized_rerun[relative_path] = _normalized_artifact_digest(
            run_dir=rerun_path,
            relative_path=relative_path,
            peer_run_dir=primary_path,
        )
    round_trip_mismatches = sorted(
        relative_path
        for relative_path in _ROUND_TRIP_ARTIFACTS
        if normalized_primary.get(relative_path) != normalized_rerun.get(relative_path)
    )
    return {
        "primary_run_dir": str(primary_path.resolve()),
        "rerun_run_dir": str(rerun_path.resolve()),
        "primary_hashes": primary_hashes,
        "rerun_hashes": rerun_hashes,
        "normalized_primary_digests": normalized_primary,
        "normalized_rerun_digests": normalized_rerun,
        "round_trip_mismatches": round_trip_mismatches,
        "round_trip_integrity": not round_trip_mismatches,
        "primary_validator_errors": primary_errors,
        "primary_validator_warnings": primary_warnings,
        "rerun_validator_errors": rerun_errors,
        "rerun_validator_warnings": rerun_warnings,
        "primary_operator_surface_inactive": bool(primary_readiness.get("current_run_operator_surface_inactive")),
        "rerun_operator_surface_inactive": bool(rerun_readiness.get("current_run_operator_surface_inactive")),
        "rehearsal_passed": (
            not primary_errors
            and not rerun_errors
            and not round_trip_mismatches
            and bool(primary_readiness.get("current_run_operator_surface_inactive"))
            and bool(rerun_readiness.get("current_run_operator_surface_inactive"))
        ),
    }


def evaluate_post_cutover_monitoring_window(
    readiness_payloads: Sequence[Mapping[str, Any]],
    *,
    required_window_size: int = 30,
) -> dict[str, Any]:
    window = list(readiness_payloads)[-required_window_size:]
    authority_phase_m2 = (
        len(window) >= required_window_size
        and all(str(item.get("authority_phase")) == "M2" for item in window)
    )
    dual_write_mismatch_zero = (
        len(window) >= required_window_size
        and all(int(item.get("dual_write_mismatch_count", 1)) == 0 for item in window)
    )
    operator_surface_inactive = (
        len(window) >= required_window_size
        and all(bool(item.get("current_run_operator_surface_inactive")) for item in window)
    )
    manifest_complete = (
        len(window) >= required_window_size
        and all(bool(item.get("manifest_registration_complete")) for item in window)
    )
    schema_complete = (
        len(window) >= required_window_size
        and all(bool(item.get("schema_complete")) for item in window)
    )
    return {
        "required_window_size": required_window_size,
        "observed_window_size": len(window),
        "authority_phase_m2_streak": authority_phase_m2,
        "dual_write_mismatch_zero_streak": dual_write_mismatch_zero,
        "operator_surface_inactive_streak": operator_surface_inactive,
        "manifest_registration_complete_streak": manifest_complete,
        "schema_complete_streak": schema_complete,
        "window_passed": (
            authority_phase_m2
            and dual_write_mismatch_zero
            and operator_surface_inactive
            and manifest_complete
            and schema_complete
        ),
    }
