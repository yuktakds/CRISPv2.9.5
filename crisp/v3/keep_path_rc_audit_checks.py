from __future__ import annotations

from typing import Any, Mapping

from crisp.v3.ci_guards import audit_exploratory_ci_separation, load_repo_workflows, load_workflow_yaml
from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    LAYER0_AUTHORITY_MODE,
    SIDECAR_RUN_RECORD_ROLE,
    VERDICT_RECORD_ROLE,
    extract_sidecar_layer0_authority_mirror,
    sidecar_layer0_authority_artifact,
    sidecar_layer0_authority_mode,
    sidecar_run_record_role,
)
from crisp.v3.public_scope_validator import KEEP_PATH_RC_COMPARABLE_CHANNELS, KEEP_PATH_RC_SCOPE
from crisp.v3.vn06_readiness import collect_verdict_record_dual_write_mismatches


def _is_numeric(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_sha256_digest(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) > len("sha256:")


def _operator_mentions_maintain_boundary(text: str) -> bool:
    lines = [
        line
        for line in text.splitlines()
        if "Cap" in line or "Catalytic" in line or "cap" in line or "catalytic" in line
    ]
    if not lines:
        return True
    return all("[v3-only]" in line or "does not widen" in line for line in lines)


def authority_inventory_checks(
    *,
    verdict_record: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
    output_inventory: Mapping[str, Any],
    generator_manifest: Mapping[str, Any],
    smoke_report: Mapping[str, Any],
    gate_report: Mapping[str, Any],
    history_report: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    mirror = extract_sidecar_layer0_authority_mirror(sidecar_run_record)
    dual_write_mismatches = collect_verdict_record_dual_write_mismatches(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
    )
    generated_outputs = output_inventory.get("generated_outputs", [])
    tracked_hashes = smoke_report.get("tracked_hashes", {})
    checks = {
        "canonical_layer0_authority_active": (
            verdict_record.get("authority_transfer_complete") is True
            and sidecar_layer0_authority_artifact(sidecar_run_record) == CANONICAL_LAYER0_AUTHORITY_ARTIFACT
            and sidecar_layer0_authority_mode(sidecar_run_record) == LAYER0_AUTHORITY_MODE
            and sidecar_run_record.get("bridge_diagnostics", {}).get("verdict_record_role") == VERDICT_RECORD_ROLE
            and sidecar_run_record_role(sidecar_run_record) == SIDECAR_RUN_RECORD_ROLE
        ),
        "sidecar_mirror_matches_verdict_record": not dual_write_mismatches and bool(mirror),
        "output_inventory_unchanged": (
            sidecar_run_record.get("rc2_outputs_unchanged") is True
            and gate_report.get("run_facts", {}).get("output_inventory_unchanged") is True
            and history_report.get("aggregate", {}).get("output_inventory_unchanged_all_runs") is True
            and isinstance(generated_outputs, list)
            and not any(str(item).startswith("v3_sidecar/") for item in generated_outputs)
        ),
        "generator_manifest_replay_contract_maintained": (
            generator_manifest.get("schema_version") == "crisp.v3.generator_manifest/v1"
            and _is_sha256_digest(generator_manifest.get("expected_output_digest"))
            and isinstance(generator_manifest.get("outputs"), list)
            and bool(generator_manifest.get("outputs"))
            and generator_manifest.get("output_root") == verdict_record.get("output_root")
            and smoke_report.get("smoke_passed") is True
            and not smoke_report.get("hash_mismatches")
            and _is_sha256_digest(tracked_hashes.get("release_packet/generator_manifest.json"))
        ),
    }
    if not checks["canonical_layer0_authority_active"]:
        findings.append("KEEP_PATH_RC_AUDIT_CANONICAL_AUTHORITY_INVALID")
    if not checks["sidecar_mirror_matches_verdict_record"]:
        findings.append(
            "KEEP_PATH_RC_AUDIT_DUAL_WRITE_MISMATCH:"
            + (str(dual_write_mismatches[0]) if dual_write_mismatches else "mirror_missing")
        )
    if not checks["output_inventory_unchanged"]:
        findings.append("KEEP_PATH_RC_AUDIT_OUTPUT_INVENTORY_CHANGED")
    if not checks["generator_manifest_replay_contract_maintained"]:
        findings.append("KEEP_PATH_RC_AUDIT_GENERATOR_MANIFEST_REPLAY_CONTRACT_BROKEN")
    return {
        "checks": checks,
        "dual_write_mismatches": list(dual_write_mismatches),
        "generated_outputs": list(generated_outputs) if isinstance(generated_outputs, list) else None,
        "passed": not findings,
    }, findings


def public_scope_safety_checks(
    *,
    verdict_record: Mapping[str, Any],
    sidecar_run_record: Mapping[str, Any],
    operator_summary: str,
    gate_report: Mapping[str, Any],
    campaign_index: Mapping[str, Any],
    public_decision_text: str,
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    mirror = extract_sidecar_layer0_authority_mirror(sidecar_run_record)
    run_facts = gate_report.get("run_facts", {})
    campaign_aggregate = campaign_index.get("aggregate", {})
    comparison_summary = sidecar_run_record.get("bridge_diagnostics", {}).get("bridge_comparison_summary", {})
    component_matches = comparison_summary.get("component_matches", {}) if isinstance(comparison_summary, Mapping) else {}
    channel_comparability = sidecar_run_record.get("channel_comparability", {})
    comparable_channels = list(verdict_record.get("comparable_channels", []))
    checks = {
        "comparator_scope_path_only_partial": (
            verdict_record.get("comparator_scope") == KEEP_PATH_RC_SCOPE
            and sidecar_run_record.get("comparator_scope") == KEEP_PATH_RC_SCOPE
            and run_facts.get("comparator_scope") == KEEP_PATH_RC_SCOPE
            and campaign_aggregate.get("comparator_scope_path_only_partial_all_runs") is True
        ),
        "comparable_channels_locked_to_path": (
            comparable_channels == list(KEEP_PATH_RC_COMPARABLE_CHANNELS)
            and list(sidecar_run_record.get("comparable_channels", [])) == list(KEEP_PATH_RC_COMPARABLE_CHANNELS)
            and list(run_facts.get("comparable_channels", [])) == list(KEEP_PATH_RC_COMPARABLE_CHANNELS)
            and campaign_aggregate.get("comparable_channels_path_only_all_runs") is True
        ),
        "v3_shadow_verdict_inactive": (
            verdict_record.get("v3_shadow_verdict") is None
            and mirror.get("v3_shadow_verdict") is None
            and run_facts.get("v3_shadow_verdict_inactive") is True
            and campaign_aggregate.get("v3_shadow_verdict_inactive_all_runs") is True
        ),
        "numeric_verdict_match_rate_absent": (
            not _is_numeric(verdict_record.get("verdict_match_rate"))
            and not _is_numeric(verdict_record.get("verdict_mismatch_rate"))
            and not _is_numeric(mirror.get("verdict_match_rate"))
            and not _is_numeric(mirror.get("verdict_mismatch_rate"))
            and run_facts.get("numeric_verdict_match_rate_absent") is True
            and campaign_aggregate.get("numeric_verdict_match_rate_absent_all_runs") is True
            and "verdict_match_rate: `N/A`" in operator_summary
        ),
        "operator_surface_exploratory": (
            "[exploratory]" in operator_summary
            and run_facts.get("operator_surface_exploratory") is True
            and run_facts.get("operator_surface_verdict_match_rate_na") is True
        ),
        "cap_catalytic_v3_only_separation_maintained": (
            "cap" not in comparable_channels
            and "catalytic" not in comparable_channels
            and isinstance(component_matches, Mapping)
            and "cap" not in component_matches
            and "catalytic" not in component_matches
            and isinstance(channel_comparability, Mapping)
            and channel_comparability.get("cap") is None
            and channel_comparability.get("catalytic") is None
            and _operator_mentions_maintain_boundary(operator_summary)
        ),
        "public_keep_decision_explicit": (
            "This memo closes the current public inclusion decision as `keep`, not `widen`." in public_decision_text
            and "comparator_scope: keep `path_only_partial`" in public_decision_text
            and "comparable_channels: keep `[\"path\"]`" in public_decision_text
            and "`v3_shadow_verdict`: inactive" in public_decision_text
        ),
    }
    if not checks["comparator_scope_path_only_partial"]:
        findings.append("KEEP_PATH_RC_AUDIT_SCOPE_WIDENED")
    if not checks["comparable_channels_locked_to_path"]:
        findings.append("KEEP_PATH_RC_AUDIT_COMPARABLE_CHANNELS_WIDENED")
    if not checks["v3_shadow_verdict_inactive"]:
        findings.append("KEEP_PATH_RC_AUDIT_V3_SHADOW_VERDICT_ACTIVE")
    if not checks["numeric_verdict_match_rate_absent"]:
        findings.append("KEEP_PATH_RC_AUDIT_NUMERIC_VERDICT_MATCH_RATE_PRESENT")
    if not checks["operator_surface_exploratory"]:
        findings.append("KEEP_PATH_RC_AUDIT_OPERATOR_SURFACE_ACTIVE")
    if not checks["cap_catalytic_v3_only_separation_maintained"]:
        findings.append("KEEP_PATH_RC_AUDIT_V3_ONLY_SEPARATION_BROKEN")
    if not checks["public_keep_decision_explicit"]:
        findings.append("KEEP_PATH_RC_AUDIT_KEEP_DECISION_MISSING")
    return {
        "checks": checks,
        "component_matches": dict(component_matches) if isinstance(component_matches, Mapping) else None,
        "channel_comparability": dict(channel_comparability) if isinstance(channel_comparability, Mapping) else None,
        "passed": not findings,
    }, findings


def ci_separation_checks(
    *,
    repo_root: Any,
    workflow_path: str,
    workflow_text: str,
    history_report: Mapping[str, Any],
    acceptance_text: str,
    release_readme_text: str,
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    workflows = load_repo_workflows(repo_root=repo_root)
    separation_findings = list(audit_exploratory_ci_separation(workflows=workflows))
    workflow = load_workflow_yaml(workflow_path, repo_root=repo_root)
    jobs = workflow.get("jobs", {})
    job_names = [
        str(job_payload.get("name", job_id))
        for job_id, job_payload in jobs.items()
        if isinstance(job_payload, Mapping)
    ]
    history_aggregate = history_report.get("aggregate", {})
    checks = {
        "repo_workflow_separation_intact": not separation_findings,
        "exploratory_lane_stays_non_required": (
            bool(job_names)
            and all(name.startswith("exploratory / ") for name in job_names)
            and "required / " not in workflow_text
            and "required matrix" not in workflow_text.lower()
        ),
        "required_matrix_untouched": (
            history_aggregate.get("required_matrix_untouched_all_runs") is True
            and history_aggregate.get("required_promotion_authorized_any_run") is False
            and history_aggregate.get("public_scope_widening_authorized_any_run") is False
            and "required_promotion_authorized = $false" in workflow_text
            and "public_scope_widening_authorized = $false" in workflow_text
        ),
        "docs_do_not_imply_required_promotion": (
            "required promotion is not authorized" in acceptance_text
            and "it is not part of the required matrix" in release_readme_text
        ),
    }
    findings.extend(f"KEEP_PATH_RC_AUDIT_CI_SEPARATION:{item}" for item in separation_findings)
    if not checks["exploratory_lane_stays_non_required"]:
        findings.append("KEEP_PATH_RC_AUDIT_EXPLORATORY_WORKFLOW_IMPLIED_REQUIRED")
    if not checks["required_matrix_untouched"]:
        findings.append("KEEP_PATH_RC_AUDIT_REQUIRED_MATRIX_TOUCHED")
    if not checks["docs_do_not_imply_required_promotion"]:
        findings.append("KEEP_PATH_RC_AUDIT_DOCS_IMPLY_REQUIRED_PROMOTION")
    return {
        "checks": checks,
        "workflow_job_names": job_names,
        "separation_findings": separation_findings,
        "passed": not findings,
    }, findings


def semantic_delta_watch_checks(
    *,
    readme_text: str,
    acceptance_text: str,
    public_decision_text: str,
    campaign_index: Mapping[str, Any],
    history_report: Mapping[str, Any],
    operator_summary: str,
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    campaign_note = str(campaign_index.get("aggregate", {}).get("metric_contract_note") or "")
    history_note = str(history_report.get("aggregate", {}).get("metric_contract_note") or "")
    checks = {
        "path_metric_not_overclaimed": (
            "not a full verdict proxy" in campaign_note
            and "not a full verdict proxy" in history_note
            and "- path_component_match_rate: `" in operator_summary
            and "verdict_match_rate: `N/A`" in operator_summary
        ),
        "design_only_docs_non_authoritative": (
            "pre-freeze / pre-M-2 fragments are non-authoritative" in readme_text
            and "pre-freeze fragments are superseded and non-authoritative" in public_decision_text
            and "automation alone remains insufficient for widening or requiredization" in acceptance_text
        ),
    }
    if not checks["path_metric_not_overclaimed"]:
        findings.append("KEEP_PATH_RC_AUDIT_PATH_METRIC_OVERCLAIMED")
    if not checks["design_only_docs_non_authoritative"]:
        findings.append("KEEP_PATH_RC_AUDIT_DESIGN_DOCS_OVERAUTHORIZING")
    return {
        "checks": checks,
        "campaign_metric_contract_note": campaign_note,
        "history_metric_contract_note": history_note,
        "passed": not findings,
    }, findings
