from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    SIDECAR_RUN_RECORD_ROLE,
    sidecar_layer0_authority_artifact,
    sidecar_run_record_role,
)
from crisp.v3.migration_scope import get_mapping_status
from crisp.v3.policy import CAP_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME, PATH_CHANNEL_NAME
from crisp.v3.report_guards import ReportGuardError, enforce_channel_semantics
from crisp.v3.rp3_activation import (
    ActivationDecisionState,
    ActivationUnit,
    RuntimeActivationContext,
    VNGateState,
    check_forbidden_surfaces,
    may_render_numeric_verdict_rates,
    may_render_v3_shadow_verdict,
)
from crisp.v3.vn06_readiness import collect_verdict_record_dual_write_mismatches

KEEP_PATH_RC_SCOPE = "path_only_partial"
KEEP_PATH_RC_COMPARABLE_CHANNELS = (PATH_CHANNEL_NAME,)
KEEP_PATH_RC_V3_ONLY_CHANNELS = (CAP_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME)


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


def _is_numeric(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _has_rendered_verdict_rate(value: Any) -> bool:
    return value not in (None, "N/A")


def _build_runtime_activation_context(
    *,
    sidecar_run_record: Mapping[str, Any],
    verdict_record: Mapping[str, Any],
    bridge_summary: Mapping[str, Any] | None,
) -> RuntimeActivationContext:
    bridge_diagnostics = sidecar_run_record.get("bridge_diagnostics", {})
    if not isinstance(bridge_diagnostics, Mapping):
        bridge_diagnostics = {}
    activation_decisions = bridge_diagnostics.get(
        "activation_decisions",
        sidecar_run_record.get("activation_decisions", {}),
    )
    if not isinstance(activation_decisions, Mapping):
        activation_decisions = {}
    vn_gate_state = bridge_diagnostics.get(
        "vn_gate_state",
        sidecar_run_record.get("vn_gate_state", {}),
    )
    if not isinstance(vn_gate_state, Mapping):
        vn_gate_state = {}
    vn_gates = bridge_diagnostics.get(
        "vn_gates",
        sidecar_run_record.get("vn_gates", {}),
    )
    if not isinstance(vn_gates, Mapping):
        vn_gates = {}

    def _vn_flag(flat_key: str, legacy_key: str) -> bool:
        if flat_key in vn_gate_state:
            return bool(vn_gate_state.get(flat_key))
        legacy_gate = vn_gates.get(legacy_key)
        if isinstance(legacy_gate, Mapping):
            return bool(legacy_gate.get("passed", False))
        return False

    summary_payload = bridge_summary if isinstance(bridge_summary, Mapping) else {}
    verdict_comparability = summary_payload.get("verdict_comparability")
    if verdict_comparability is None:
        embedded_summary = bridge_diagnostics.get("bridge_comparison_summary", {})
        if isinstance(embedded_summary, Mapping):
            verdict_comparability = embedded_summary.get("verdict_comparability")

    return RuntimeActivationContext(
        decision=ActivationDecisionState(
            v3_shadow_verdict_accepted=bool(
                activation_decisions.get(ActivationUnit.V3_SHADOW_VERDICT.value, False)
            ),
            numeric_verdict_rates_accepted=bool(
                activation_decisions.get(ActivationUnit.NUMERIC_VERDICT_RATES.value, False)
            ),
        ),
        vn_gate=VNGateState(
            vn_01=_vn_flag("vn_01", "VN-01"),
            vn_02=_vn_flag("vn_02", "VN-02"),
            vn_03=_vn_flag("vn_03", "VN-03"),
            vn_04=_vn_flag("vn_04", "VN-04"),
            vn_05=_vn_flag("vn_05", "VN-05"),
            vn_06=_vn_flag("vn_06", "VN-06"),
        ),
        full_verdict_computable=bool(verdict_record.get("full_verdict_computable", False)),
        denominator_contract_satisfied=bool(
            bridge_diagnostics.get(
                "denominator_contract_satisfied",
                verdict_comparability == "fully_comparable",
            )
        ),
    )


def validate_keep_path_rc_bundle(
    *,
    sidecar_run_record: Mapping[str, Any],
    verdict_record: Mapping[str, Any],
    output_inventory: Mapping[str, Any],
    bridge_summary: Mapping[str, Any] | None = None,
    operator_summary: str | None = None,
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    diagnostics: dict[str, Any] = {
        "required_scope": KEEP_PATH_RC_SCOPE,
        "required_comparable_channels": list(KEEP_PATH_RC_COMPARABLE_CHANNELS),
        "forbidden_public_channels": list(KEEP_PATH_RC_V3_ONLY_CHANNELS),
        "canonical_layer0_authority_artifact": sidecar_layer0_authority_artifact(sidecar_run_record),
        "sidecar_run_record_role": sidecar_run_record_role(sidecar_run_record),
        "path_mapping_status": get_mapping_status("scv_pat"),
    }

    run_record_scope = str(sidecar_run_record.get("comparator_scope"))
    verdict_scope = str(verdict_record.get("comparator_scope"))
    diagnostics["run_record_scope"] = run_record_scope
    diagnostics["verdict_record_scope"] = verdict_scope
    if run_record_scope != KEEP_PATH_RC_SCOPE:
        errors.append(f"KEEP_PATH_RC_SCOPE_MISMATCH:sidecar_run_record:{run_record_scope}")
    if verdict_scope != KEEP_PATH_RC_SCOPE:
        errors.append(f"KEEP_PATH_RC_SCOPE_MISMATCH:verdict_record:{verdict_scope}")

    run_record_channels = tuple(str(item) for item in sidecar_run_record.get("comparable_channels", ()))
    verdict_channels = tuple(str(item) for item in verdict_record.get("comparable_channels", ()))
    diagnostics["run_record_comparable_channels"] = list(run_record_channels)
    diagnostics["verdict_record_comparable_channels"] = list(verdict_channels)
    if run_record_channels != KEEP_PATH_RC_COMPARABLE_CHANNELS:
        errors.append(
            f"KEEP_PATH_RC_COMPARABLE_CHANNELS_INVALID:sidecar_run_record:{list(run_record_channels)}"
        )
    if verdict_channels != KEEP_PATH_RC_COMPARABLE_CHANNELS:
        errors.append(
            f"KEEP_PATH_RC_COMPARABLE_CHANNELS_INVALID:verdict_record:{list(verdict_channels)}"
        )
    try:
        enforce_channel_semantics(
            comparable_channels=run_record_channels,
            v3_only_evidence_channels=sidecar_run_record.get("v3_only_evidence_channels", ()),
            component_matches=(bridge_summary or {}).get("component_matches"),
            channel_lifecycle_states=sidecar_run_record.get("channel_lifecycle_states"),
        )
    except ReportGuardError as exc:
        errors.append(f"KEEP_PATH_RC_CHANNEL_SEMANTICS:{exc}")

    if get_mapping_status("scv_pat") != "FROZEN":
        errors.append("KEEP_PATH_RC_PATH_MAPPING_NOT_FROZEN")

    ctx = _build_runtime_activation_context(
        sidecar_run_record=sidecar_run_record,
        verdict_record=verdict_record,
        bridge_summary=bridge_summary,
    )
    shadow_renderable = may_render_v3_shadow_verdict(ctx)
    numeric_rates_renderable = may_render_numeric_verdict_rates(ctx)

    if verdict_record.get("v3_shadow_verdict") is not None:
        if not shadow_renderable:
            errors.append("KEEP_PATH_RC_V3_SHADOW_VERDICT_ACTIVE:verdict_record")
    mirror = (
        sidecar_run_record.get("bridge_diagnostics", {})
        .get("layer0_authority_mirror", {})
    )
    if isinstance(mirror, Mapping) and mirror.get("v3_shadow_verdict") is not None:
        if not shadow_renderable:
            errors.append("KEEP_PATH_RC_V3_SHADOW_VERDICT_ACTIVE:sidecar_mirror")

    for source_label, payload in (
        ("verdict_record", verdict_record),
        ("sidecar_mirror", mirror if isinstance(mirror, Mapping) else {}),
    ):
        match_rate = payload.get("verdict_match_rate")
        mismatch_rate = payload.get("verdict_mismatch_rate")
        if _is_numeric(match_rate) and not numeric_rates_renderable:
            errors.append(f"KEEP_PATH_RC_NUMERIC_VERDICT_MATCH_RATE_FORBIDDEN:{source_label}")
        if _is_numeric(mismatch_rate) and not numeric_rates_renderable:
            errors.append(f"KEEP_PATH_RC_NUMERIC_VERDICT_MISMATCH_RATE_FORBIDDEN:{source_label}")

    summary_component_matches = (bridge_summary or {}).get("component_matches", {})
    operator_summary_has_numeric_rates = bool(
        operator_summary is not None
        and (
            "verdict_match_rate: `1/" in operator_summary
            or "verdict_match_rate: `0/" in operator_summary
        )
    )
    forbidden_surface_errors = check_forbidden_surfaces(
        ctx=ctx,
        comparable_channels=list(run_record_channels),
        component_match_keys=(
            [str(key) for key in summary_component_matches.keys()]
            if isinstance(summary_component_matches, Mapping)
            else []
        ),
        mixed_summary_requested=bool(
            operator_summary is not None
            and "mixed summary" in operator_summary.lower()
        ),
        numeric_rates_present=bool(
            operator_summary_has_numeric_rates
            or any(
                _has_rendered_verdict_rate(payload.get("verdict_match_rate"))
                or _has_rendered_verdict_rate(payload.get("verdict_mismatch_rate"))
                for payload in (
                    verdict_record,
                    mirror if isinstance(mirror, Mapping) else {},
                )
            )
        ),
    )
    for forbidden_error in forbidden_surface_errors:
        if forbidden_error == "cap must not appear in comparable_channels":
            if "KEEP_PATH_RC_V3_ONLY_CHANNEL_BECAME_COMPARABLE" not in errors:
                errors.append("KEEP_PATH_RC_V3_ONLY_CHANNEL_BECAME_COMPARABLE")
        elif forbidden_error == "catalytic_rule3b must not appear in component_matches":
            errors.append("KEEP_PATH_RC_COMPONENT_MATCH_LEAK:catalytic_rule3b")
        elif forbidden_error == "mixed rc2/v3 aggregate summaries are forbidden":
            errors.append("KEEP_PATH_RC_OPERATOR_MIXED_SUMMARY_FORBIDDEN")
        elif (
            forbidden_error
            == "numeric verdict rates present while runtime activation conditions are unmet"
            and operator_summary_has_numeric_rates
        ):
            errors.append("KEEP_PATH_RC_OPERATOR_VERDICT_MATCH_RATE_NUMERIC")

    if verdict_record.get("authority_transfer_complete") is not True:
        errors.append("KEEP_PATH_RC_M2_AUTHORITY_TRANSFER_INCOMPLETE")
    if sidecar_layer0_authority_artifact(sidecar_run_record) != CANONICAL_LAYER0_AUTHORITY_ARTIFACT:
        errors.append("KEEP_PATH_RC_CANONICAL_AUTHORITY_POINTER_INVALID")
    if sidecar_run_record_role(sidecar_run_record) != SIDECAR_RUN_RECORD_ROLE:
        errors.append("KEEP_PATH_RC_SIDECAR_ROLE_INVALID")

    dual_write_mismatches = collect_verdict_record_dual_write_mismatches(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
    )
    diagnostics["dual_write_mismatches"] = list(dual_write_mismatches)
    if dual_write_mismatches:
        errors.append(f"KEEP_PATH_RC_DUAL_WRITE_MISMATCH:{dual_write_mismatches[0]}")

    run_record_v3_only = {str(item) for item in sidecar_run_record.get("v3_only_evidence_channels", ())}
    diagnostics["run_record_v3_only_evidence_channels"] = sorted(run_record_v3_only)
    if "path" in run_record_v3_only:
        errors.append("KEEP_PATH_RC_PATH_MARKED_V3_ONLY")
    if any(channel_name in set(run_record_channels) for channel_name in KEEP_PATH_RC_V3_ONLY_CHANNELS):
        errors.append("KEEP_PATH_RC_V3_ONLY_CHANNEL_BECAME_COMPARABLE")

    channel_comparability = sidecar_run_record.get("channel_comparability", {})
    if isinstance(channel_comparability, Mapping):
        for channel_name in KEEP_PATH_RC_V3_ONLY_CHANNELS:
            if channel_comparability.get(channel_name) is not None:
                errors.append(f"KEEP_PATH_RC_V3_ONLY_COMPARABILITY_LEAK:{channel_name}")

    if isinstance(summary_component_matches, Mapping):
        for channel_name in KEEP_PATH_RC_V3_ONLY_CHANNELS:
            if channel_name in summary_component_matches:
                errors.append(f"KEEP_PATH_RC_COMPONENT_MATCH_LEAK:{channel_name}")

    generated_outputs = output_inventory.get("generated_outputs", [])
    if not isinstance(generated_outputs, list):
        errors.append("KEEP_PATH_RC_OUTPUT_INVENTORY_NOT_LIST")
    else:
        diagnostics["output_inventory_generated_outputs"] = list(generated_outputs)
        for relative_path in generated_outputs:
            if str(relative_path).startswith("v3_sidecar/"):
                errors.append(f"KEEP_PATH_RC_OUTPUT_INVENTORY_MUTATED:{relative_path}")

    if operator_summary is not None:
        diagnostics["operator_summary_checked"] = True
        if "[exploratory]" not in operator_summary:
            errors.append("KEEP_PATH_RC_OPERATOR_SURFACE_NOT_EXPLORATORY")
        if operator_summary_has_numeric_rates and not numeric_rates_renderable:
            errors.append("KEEP_PATH_RC_OPERATOR_VERDICT_MATCH_RATE_NUMERIC")
        if "v3_shadow_verdict" in operator_summary and not shadow_renderable:
            errors.append("KEEP_PATH_RC_OPERATOR_V3_SHADOW_VERDICT_ACTIVE")
    else:
        diagnostics["operator_summary_checked"] = False

    diagnostics["validation_passed"] = not errors
    return sorted(set(errors)), sorted(set(warnings)), diagnostics


def validate_keep_path_rc_run_directory(
    run_dir: str | Path,
    *,
    sidecar_dirname: str = "v3_sidecar",
) -> tuple[list[str], list[str], dict[str, Any]]:
    run_path = Path(run_dir)
    sidecar_root = run_path / sidecar_dirname
    diagnostics: dict[str, Any] = {
        "run_dir": str(run_path.resolve()),
        "sidecar_root": str(sidecar_root.resolve()),
    }
    errors: list[str] = []
    warnings: list[str] = []

    output_inventory, issues = _load_json_object(
        run_path / "output_inventory.json",
        label="KEEP_PATH_RC_OUTPUT_INVENTORY",
    )
    errors.extend(issues)
    sidecar_run_record, issues = _load_json_object(
        sidecar_root / "sidecar_run_record.json",
        label="KEEP_PATH_RC_SIDECAR_RUN_RECORD",
    )
    errors.extend(issues)
    verdict_record, issues = _load_json_object(
        sidecar_root / "verdict_record.json",
        label="KEEP_PATH_RC_VERDICT_RECORD",
    )
    errors.extend(issues)
    bridge_summary_path = sidecar_root / "bridge_comparison_summary.json"
    bridge_summary = None
    if bridge_summary_path.exists():
        bridge_summary, issues = _load_json_object(
            bridge_summary_path,
            label="KEEP_PATH_RC_BRIDGE_SUMMARY",
        )
        errors.extend(issues)
    operator_summary_path = sidecar_root / "bridge_operator_summary.md"
    operator_summary = None
    if operator_summary_path.exists():
        try:
            operator_summary = operator_summary_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"KEEP_PATH_RC_OPERATOR_SUMMARY_READ_ERROR:{exc}")

    if errors:
        diagnostics["validation_passed"] = False
        return sorted(set(errors)), sorted(set(warnings)), diagnostics

    bundle_errors, bundle_warnings, bundle_diagnostics = validate_keep_path_rc_bundle(
        sidecar_run_record=sidecar_run_record or {},
        verdict_record=verdict_record or {},
        output_inventory=output_inventory or {},
        bridge_summary=bridge_summary,
        operator_summary=operator_summary,
    )
    diagnostics.update(bundle_diagnostics)
    errors.extend(bundle_errors)
    warnings.extend(bundle_warnings)
    diagnostics["validation_passed"] = not errors
    return sorted(set(errors)), sorted(set(warnings)), diagnostics
