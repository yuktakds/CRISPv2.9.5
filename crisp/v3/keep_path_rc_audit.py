from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from crisp.repro.hashing import sha256_file
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
from crisp.v3.keep_path_rc_gate import RC_GATE_KEEP_PATH_REPORT_ARTIFACT
from crisp.v3.keep_path_rc_history import KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT
from crisp.v3.public_scope_validator import KEEP_PATH_RC_COMPARABLE_CHANNELS, KEEP_PATH_RC_SCOPE
from crisp.v3.release_packet_smoke import KEEP_PATH_RC_RELEASE_PACKET_REPORT_ARTIFACT
from crisp.v3.vn06_readiness import collect_verdict_record_dual_write_mismatches

KEEP_PATH_RC_HOSTILE_AUDIT_REPORT_ARTIFACT = "keep_path_rc_hostile_audit_report.json"
KEEP_PATH_RC_HOSTILE_AUDIT_SUMMARY_ARTIFACT = "keep_path_rc_hostile_audit_summary.md"
KEEP_PATH_RC_CAMPAIGN_INDEX_ARTIFACT = "campaign_index.json"
KEEP_PATH_RC_EXPLORATORY_WORKFLOW_PATH = ".github/workflows/v3-keep-path-rc-exploratory.yml"
_REQUIRED_EVIDENCE_REPORTS = (
    "m2_rollback_drill_report.json",
    "m2_rehearsal_report.json",
    "m2_post_cutover_monitoring_report.json",
    RC_GATE_KEEP_PATH_REPORT_ARTIFACT,
    KEEP_PATH_RC_CAMPAIGN_INDEX_ARTIFACT,
    KEEP_PATH_RC_RELEASE_PACKET_REPORT_ARTIFACT,
    KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT,
)
_REQUIRED_DOC_FILES = (
    "README.md",
    "v3_keep_path_rc_acceptance_memo.md",
    "v3_keep_path_rc_roadmap.md",
    "wp6_public_inclusion_decision_memo.md",
)


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


def _load_text(path: Path, *, label: str) -> tuple[str | None, list[str]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except OSError as exc:
        return None, [f"{label}_READ_ERROR:{exc}"]


def _display_relative_path(path: Path, *, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _contains_required_fragments(*, text: str, required_fragments: Sequence[str]) -> list[str]:
    return [fragment for fragment in required_fragments if fragment not in text]


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


def _hash_loaded_files(paths: Sequence[Path], *, repo_root: Path) -> dict[str, str]:
    return {
        _display_relative_path(path, root=repo_root): sha256_file(path)
        for path in paths
        if path.exists()
    }


def _load_required_docs(
    *,
    docs_root: Path,
    evidence_dir: Path,
) -> tuple[dict[str, str], list[Path], list[str]]:
    findings: list[str] = []
    texts: dict[str, str] = {}
    loaded_paths: list[Path] = []
    for relative_path in _REQUIRED_DOC_FILES:
        path = docs_root / relative_path
        text, issues = _load_text(path, label=f"KEEP_PATH_RC_AUDIT_{relative_path}")
        findings.extend(issues)
        if text is not None:
            texts[relative_path] = text
            loaded_paths.append(path)
    evidence_index_path = evidence_dir / "README.md"
    text, issues = _load_text(evidence_index_path, label="KEEP_PATH_RC_AUDIT_EVIDENCE_INDEX")
    findings.extend(issues)
    if text is not None:
        texts["release/evidence/keep_path_rc/README.md"] = text
        loaded_paths.append(evidence_index_path)
    return texts, loaded_paths, findings


def _load_required_jsons(
    *,
    evidence_dir: Path,
    history_report_path: Path,
) -> tuple[dict[str, dict[str, Any]], list[Path], list[str]]:
    findings: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}
    loaded_paths: list[Path] = []
    for relative_path in _REQUIRED_EVIDENCE_REPORTS:
        path = history_report_path if relative_path == KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT else evidence_dir / relative_path
        payload, issues = _load_json_object(path, label=f"KEEP_PATH_RC_AUDIT_{relative_path}")
        findings.extend(issues)
        if payload is not None:
            payloads[relative_path] = payload
            loaded_paths.append(path)
    packet_dir = evidence_dir / "release_packet"
    packet_paths = (
        packet_dir / "output_inventory.json",
        packet_dir / "verdict_record.json",
        packet_dir / "sidecar_run_record.json",
        packet_dir / "generator_manifest.json",
    )
    for path in packet_paths:
        payload, issues = _load_json_object(path, label=f"KEEP_PATH_RC_AUDIT_{path.name}")
        findings.extend(issues)
        if payload is not None:
            payloads[f"release_packet/{path.name}"] = payload
            loaded_paths.append(path)
    return payloads, loaded_paths, findings


def _load_operator_summary(packet_dir: Path) -> tuple[str | None, Path, list[str]]:
    path = packet_dir / "bridge_operator_summary.md"
    text, issues = _load_text(path, label="KEEP_PATH_RC_AUDIT_bridge_operator_summary.md")
    return text, path, issues


def _authority_inventory_checks(
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


def _public_scope_safety_checks(
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


def _load_release_readme(repo_root: Path) -> tuple[str, Path, list[str]]:
    path = repo_root / "docs" / "release" / "README.md"
    text, issues = _load_text(path, label="KEEP_PATH_RC_AUDIT_RELEASE_README")
    return text or "", path, issues


def _ci_separation_checks(
    *,
    repo_root: Path,
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


def _semantic_delta_watch_checks(
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


def evaluate_keep_path_rc_hostile_audit(
    *,
    docs_root: str | Path,
    evidence_dir: str | Path,
    repo_root: str | Path | None = None,
    history_report_path: str | Path | None = None,
    workflow_path: str = KEEP_PATH_RC_EXPLORATORY_WORKFLOW_PATH,
) -> dict[str, Any]:
    docs_path = Path(docs_root)
    evidence_path = Path(evidence_dir)
    repo_path = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    history_path = (
        Path(history_report_path)
        if history_report_path is not None
        else evidence_path / KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT
    )
    packet_dir = evidence_path / "release_packet"

    doc_texts, doc_paths, doc_findings = _load_required_docs(
        docs_root=docs_path,
        evidence_dir=evidence_path,
    )
    json_payloads, json_paths, json_findings = _load_required_jsons(
        evidence_dir=evidence_path,
        history_report_path=history_path,
    )
    operator_summary, operator_summary_path, operator_issues = _load_operator_summary(packet_dir)
    workflow_abs_path = repo_path / workflow_path
    workflow_text, workflow_issues = _load_text(
        workflow_abs_path,
        label="KEEP_PATH_RC_AUDIT_EXPLORATORY_WORKFLOW",
    )
    release_readme_text, release_readme_path, release_readme_issues = _load_release_readme(repo_path)

    findings: list[str] = [
        *doc_findings,
        *json_findings,
        *operator_issues,
        *workflow_issues,
        *release_readme_issues,
    ]
    if findings:
        return {
            "schema_version": "crisp.v3.keep_path_rc_hostile_audit/v1",
            "docs_root": str(docs_path.resolve()),
            "evidence_dir": str(evidence_path.resolve()),
            "repo_root": str(repo_path.resolve()),
            "workflow_path": workflow_path,
            "history_report_path": str(history_path.resolve()),
            "findings": findings,
            "audit_passed": False,
        }

    verdict_record = json_payloads["release_packet/verdict_record.json"]
    sidecar_run_record = json_payloads["release_packet/sidecar_run_record.json"]
    output_inventory = json_payloads["release_packet/output_inventory.json"]
    generator_manifest = json_payloads["release_packet/generator_manifest.json"]
    smoke_report = json_payloads[KEEP_PATH_RC_RELEASE_PACKET_REPORT_ARTIFACT]
    gate_report = json_payloads[RC_GATE_KEEP_PATH_REPORT_ARTIFACT]
    campaign_index = json_payloads[KEEP_PATH_RC_CAMPAIGN_INDEX_ARTIFACT]
    history_report = json_payloads[KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT]

    authority_inventory, authority_findings = _authority_inventory_checks(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
        output_inventory=output_inventory,
        generator_manifest=generator_manifest,
        smoke_report=smoke_report,
        gate_report=gate_report,
        history_report=history_report,
    )
    public_scope_safety, public_findings = _public_scope_safety_checks(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
        operator_summary=operator_summary or "",
        gate_report=gate_report,
        campaign_index=campaign_index,
        public_decision_text=doc_texts.get("wp6_public_inclusion_decision_memo.md", ""),
    )
    ci_separation, ci_findings = _ci_separation_checks(
        repo_root=repo_path,
        workflow_path=workflow_path,
        workflow_text=workflow_text or "",
        history_report=history_report,
        acceptance_text=doc_texts.get("v3_keep_path_rc_acceptance_memo.md", ""),
        release_readme_text=release_readme_text,
    )
    semantic_delta_watch, semantic_findings = _semantic_delta_watch_checks(
        readme_text=doc_texts.get("README.md", ""),
        acceptance_text=doc_texts.get("v3_keep_path_rc_acceptance_memo.md", ""),
        public_decision_text=doc_texts.get("wp6_public_inclusion_decision_memo.md", ""),
        campaign_index=campaign_index,
        history_report=history_report,
        operator_summary=operator_summary or "",
    )
    findings.extend(authority_findings)
    findings.extend(public_findings)
    findings.extend(ci_findings)
    findings.extend(semantic_findings)

    audit_checks = {
        "authorization_boundary_ok": (
            authority_inventory["checks"]["canonical_layer0_authority_active"]
            and authority_inventory["checks"]["sidecar_mirror_matches_verdict_record"]
            and semantic_delta_watch["checks"]["design_only_docs_non_authoritative"]
            and public_scope_safety["checks"]["public_keep_decision_explicit"]
        ),
        "keep_scope_unchanged": (
            public_scope_safety["checks"]["comparator_scope_path_only_partial"]
            and public_scope_safety["checks"]["comparable_channels_locked_to_path"]
            and public_scope_safety["checks"]["cap_catalytic_v3_only_separation_maintained"]
        ),
        "operator_surface_inactive": (
            public_scope_safety["checks"]["v3_shadow_verdict_inactive"]
            and public_scope_safety["checks"]["numeric_verdict_match_rate_absent"]
            and public_scope_safety["checks"]["operator_surface_exploratory"]
        ),
        "ci_promotion_not_implied": (
            ci_separation["checks"]["repo_workflow_separation_intact"]
            and ci_separation["checks"]["exploratory_lane_stays_non_required"]
            and ci_separation["checks"]["required_matrix_untouched"]
            and ci_separation["checks"]["docs_do_not_imply_required_promotion"]
        ),
        "path_metric_not_overclaimed": semantic_delta_watch["checks"]["path_metric_not_overclaimed"],
    }
    audit_passed = all(audit_checks.values()) and not findings
    loaded_paths = [*doc_paths, *json_paths, operator_summary_path, workflow_abs_path, release_readme_path]

    payload = {
        "schema_version": "crisp.v3.keep_path_rc_hostile_audit/v1",
        "docs_root": str(docs_path.resolve()),
        "evidence_dir": str(evidence_path.resolve()),
        "repo_root": str(repo_path.resolve()),
        "workflow_path": workflow_path,
        "history_report_path": str(history_path.resolve()),
        "input_hashes": _hash_loaded_files(loaded_paths, repo_root=repo_path),
        "authority_inventory": {
            **authority_inventory,
            "findings": authority_findings,
        },
        "public_scope_safety": {
            **public_scope_safety,
            "findings": public_findings,
        },
        "ci_separation": {
            **ci_separation,
            "findings": ci_findings,
        },
        "semantic_delta_watch": {
            **semantic_delta_watch,
            "findings": semantic_findings,
        },
        "audit_checks": audit_checks,
        "findings": findings,
        "audit_passed": audit_passed,
    }
    return payload


def render_keep_path_rc_hostile_audit_summary(payload: Mapping[str, Any]) -> str:
    audit_checks = payload.get("audit_checks", {})
    lines = [
        "# Keep-Path RC Hostile Audit Summary",
        "",
        f"- audit_passed: `{str(bool(payload.get('audit_passed'))).lower()}`",
        f"- authorization_boundary_ok: `{str(bool(audit_checks.get('authorization_boundary_ok'))).lower()}`",
        f"- keep_scope_unchanged: `{str(bool(audit_checks.get('keep_scope_unchanged'))).lower()}`",
        f"- operator_surface_inactive: `{str(bool(audit_checks.get('operator_surface_inactive'))).lower()}`",
        f"- ci_promotion_not_implied: `{str(bool(audit_checks.get('ci_promotion_not_implied'))).lower()}`",
        f"- path_metric_not_overclaimed: `{str(bool(audit_checks.get('path_metric_not_overclaimed'))).lower()}`",
        "",
        "Authority / inventory re-checks `verdict_record.json` as canonical Layer 0 authority and `sidecar_run_record.json` as the backward-compatible mirror.",
        "Public scope remains locked to `path_only_partial` with `comparable_channels = [\"path\"]`, `v3_shadow_verdict = None`, and `verdict_match_rate = N/A`.",
        "Hosted CI remains `[exploratory]` only and does not authorize required promotion or scope widening.",
        "path_component_match_rate remains a Path-only component metric and is not a full verdict proxy.",
    ]
    return "\n".join(lines) + "\n"


def write_keep_path_rc_hostile_audit_report(
    *,
    output_dir: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / KEEP_PATH_RC_HOSTILE_AUDIT_REPORT_ARTIFACT
    report_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report_path


def write_keep_path_rc_hostile_audit_summary(
    *,
    output_dir: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary_path = output_path / KEEP_PATH_RC_HOSTILE_AUDIT_SUMMARY_ARTIFACT
    summary_path.write_text(
        render_keep_path_rc_hostile_audit_summary(payload),
        encoding="utf-8",
    )
    return summary_path
