from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from crisp.v3.keep_path_rc_audit_checks import (
    authority_inventory_checks,
    ci_separation_checks,
    public_scope_safety_checks,
    semantic_delta_watch_checks,
)
from crisp.v3.keep_path_rc_audit_io import (
    hash_loaded_files,
    load_operator_summary,
    load_release_readme,
    load_required_docs,
    load_required_jsons,
    load_text,
)
from crisp.v3.keep_path_rc_gate import RC_GATE_KEEP_PATH_REPORT_ARTIFACT
from crisp.v3.keep_path_rc_history import KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT
from crisp.v3.release_packet_smoke import KEEP_PATH_RC_RELEASE_PACKET_REPORT_ARTIFACT

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


def evaluate_keep_path_rc_hostile_audit(
    *,
    docs_root: str | Path,
    evidence_dir: str | Path,
    repo_root: str | Path | None = None,
    history_report_path: str | Path | None = None,
    workflow_path: str = KEEP_PATH_RC_EXPLORATORY_WORKFLOW_PATH,
) -> dict[str, object]:
    docs_path = Path(docs_root)
    evidence_path = Path(evidence_dir)
    repo_path = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    history_path = (
        Path(history_report_path)
        if history_report_path is not None
        else evidence_path / KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT
    )
    packet_dir = evidence_path / "release_packet"

    doc_texts, doc_paths, doc_findings = load_required_docs(
        docs_root=docs_path,
        evidence_dir=evidence_path,
        required_doc_files=_REQUIRED_DOC_FILES,
    )
    json_payloads, json_paths, json_findings = load_required_jsons(
        evidence_dir=evidence_path,
        history_report_path=history_path,
        required_evidence_reports=_REQUIRED_EVIDENCE_REPORTS,
    )
    operator_summary, operator_summary_path, operator_issues = load_operator_summary(packet_dir)
    workflow_abs_path = repo_path / workflow_path
    workflow_text, workflow_issues = load_text(
        workflow_abs_path,
        label="KEEP_PATH_RC_AUDIT_EXPLORATORY_WORKFLOW",
    )
    release_readme_text, release_readme_path, release_readme_issues = load_release_readme(repo_path)

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

    authority_inventory, authority_findings = authority_inventory_checks(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
        output_inventory=output_inventory,
        generator_manifest=generator_manifest,
        smoke_report=smoke_report,
        gate_report=gate_report,
        history_report=history_report,
    )
    public_scope_safety, public_findings = public_scope_safety_checks(
        verdict_record=verdict_record,
        sidecar_run_record=sidecar_run_record,
        operator_summary=operator_summary or "",
        gate_report=gate_report,
        campaign_index=campaign_index,
        public_decision_text=doc_texts.get("wp6_public_inclusion_decision_memo.md", ""),
    )
    ci_separation, ci_findings = ci_separation_checks(
        repo_root=repo_path,
        workflow_path=workflow_path,
        workflow_text=workflow_text or "",
        history_report=history_report,
        acceptance_text=doc_texts.get("v3_keep_path_rc_acceptance_memo.md", ""),
        release_readme_text=release_readme_text,
    )
    semantic_delta_watch, semantic_findings = semantic_delta_watch_checks(
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

    return {
        "schema_version": "crisp.v3.keep_path_rc_hostile_audit/v1",
        "docs_root": str(docs_path.resolve()),
        "evidence_dir": str(evidence_path.resolve()),
        "repo_root": str(repo_path.resolve()),
        "workflow_path": workflow_path,
        "history_report_path": str(history_path.resolve()),
        "input_hashes": hash_loaded_files(loaded_paths, repo_root=repo_path),
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


def render_keep_path_rc_hostile_audit_summary(payload: Mapping[str, object]) -> str:
    audit_checks = payload.get("audit_checks", {})
    if not isinstance(audit_checks, Mapping):
        audit_checks = {}
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
    payload: Mapping[str, object],
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
    payload: Mapping[str, object],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary_path = output_path / KEEP_PATH_RC_HOSTILE_AUDIT_SUMMARY_ARTIFACT
    summary_path.write_text(
        render_keep_path_rc_hostile_audit_summary(payload),
        encoding="utf-8",
    )
    return summary_path
