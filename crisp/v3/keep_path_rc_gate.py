from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from crisp.repro.hashing import sha256_file
from crisp.v3.public_scope_validator import validate_keep_path_rc_run_directory

RC_GATE_KEEP_PATH_REPORT_ARTIFACT = "rc_gate_keep_path_report.json"
_REQUIRED_DOC_FILES = (
    "README.md",
    "v3_keep_path_rc_acceptance_memo.md",
    "v3_keep_path_rc_roadmap.md",
)
_REQUIRED_EVIDENCE_REPORTS = (
    "m2_rollback_drill_report.json",
    "m2_rehearsal_report.json",
    "m2_post_cutover_monitoring_report.json",
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


def _contains_required_fragments(*, text: str, required_fragments: Sequence[str]) -> list[str]:
    return [fragment for fragment in required_fragments if fragment not in text]


def _display_relative_path(path: Path, *, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _extract_operator_summary_value(*, text: str, label: str) -> str | None:
    prefix = f"- {label}: `"
    for line in text.splitlines():
        if line.startswith(prefix) and line.endswith("`"):
            return line[len(prefix):-1]
    return None


def _is_numeric(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _load_keep_path_rc_run_bundle(
    run_dir: str | Path,
    *,
    sidecar_dirname: str = "v3_sidecar",
) -> tuple[dict[str, Any], list[str]]:
    run_path = Path(run_dir)
    sidecar_root = run_path / sidecar_dirname
    findings: list[str] = []

    output_inventory, issues = _load_json_object(
        run_path / "output_inventory.json",
        label="KEEP_PATH_RC_OUTPUT_INVENTORY",
    )
    findings.extend(issues)
    sidecar_run_record, issues = _load_json_object(
        sidecar_root / "sidecar_run_record.json",
        label="KEEP_PATH_RC_SIDECAR_RUN_RECORD",
    )
    findings.extend(issues)
    verdict_record, issues = _load_json_object(
        sidecar_root / "verdict_record.json",
        label="KEEP_PATH_RC_VERDICT_RECORD",
    )
    findings.extend(issues)

    bridge_summary = None
    bridge_summary_path = sidecar_root / "bridge_comparison_summary.json"
    if bridge_summary_path.exists():
        bridge_summary, issues = _load_json_object(
            bridge_summary_path,
            label="KEEP_PATH_RC_BRIDGE_SUMMARY",
        )
        findings.extend(issues)

    operator_summary = None
    operator_summary_path = sidecar_root / "bridge_operator_summary.md"
    if operator_summary_path.exists():
        operator_summary, issues = _load_text(
            operator_summary_path,
            label="KEEP_PATH_RC_OPERATOR_SUMMARY",
        )
        findings.extend(issues)

    return {
        "run_path": run_path,
        "sidecar_root": sidecar_root,
        "output_inventory": output_inventory,
        "sidecar_run_record": sidecar_run_record,
        "verdict_record": verdict_record,
        "bridge_summary": bridge_summary,
        "operator_summary": operator_summary,
    }, findings


def collect_keep_path_rc_run_facts(
    run_dir: str | Path,
    *,
    sidecar_dirname: str = "v3_sidecar",
) -> tuple[dict[str, Any], list[str]]:
    bundle, findings = _load_keep_path_rc_run_bundle(
        run_dir,
        sidecar_dirname=sidecar_dirname,
    )
    run_path = bundle["run_path"]
    sidecar_root = bundle["sidecar_root"]
    output_inventory = bundle.get("output_inventory") or {}
    sidecar_run_record = bundle.get("sidecar_run_record") or {}
    verdict_record = bundle.get("verdict_record") or {}
    bridge_summary = bundle.get("bridge_summary") or {}
    operator_summary = bundle.get("operator_summary") or ""

    run_drift_report = bridge_summary.get("run_drift_report", {}) if isinstance(bridge_summary, Mapping) else {}
    generated_outputs = output_inventory.get("generated_outputs", []) if isinstance(output_inventory, Mapping) else []
    semantic_policy_version = str(
        verdict_record.get("semantic_policy_version")
        or bridge_summary.get("semantic_policy_version")
        or ""
    )
    operator_summary_semantic_policy_version = _extract_operator_summary_value(
        text=operator_summary,
        label="semantic_policy_version",
    )
    operator_summary_verdict_match_rate = _extract_operator_summary_value(
        text=operator_summary,
        label="verdict_match_rate",
    )

    facts = {
        "run_dir": str(run_path.resolve()),
        "sidecar_root": str(sidecar_root.resolve()),
        "semantic_policy_version": semantic_policy_version,
        "comparator_scope": str(verdict_record.get("comparator_scope") or sidecar_run_record.get("comparator_scope") or ""),
        "comparable_channels": [
            str(item)
            for item in (
                verdict_record.get("comparable_channels")
                or sidecar_run_record.get("comparable_channels")
                or ()
            )
        ],
        "path_component_match_rate": run_drift_report.get("path_component_match_rate"),
        "coverage_drift_count": run_drift_report.get("coverage_drift_count"),
        "applicability_drift_count": run_drift_report.get("applicability_drift_count"),
        "metrics_drift_count": run_drift_report.get("metrics_drift_count"),
        "output_inventory_generated_outputs": list(generated_outputs) if isinstance(generated_outputs, list) else [],
        "output_inventory_unchanged": bool(sidecar_run_record.get("rc2_outputs_unchanged")),
        "v3_shadow_verdict_inactive": verdict_record.get("v3_shadow_verdict") is None,
        "numeric_verdict_match_rate_absent": not _is_numeric(verdict_record.get("verdict_match_rate")),
        "numeric_verdict_mismatch_rate_absent": not _is_numeric(verdict_record.get("verdict_mismatch_rate")),
        "operator_surface_exploratory": "[exploratory]" in operator_summary,
        "operator_surface_semantic_policy_version_present": bool(semantic_policy_version)
        and operator_summary_semantic_policy_version == semantic_policy_version,
        "operator_surface_verdict_match_rate_label": operator_summary_verdict_match_rate,
        "operator_surface_verdict_match_rate_na": operator_summary_verdict_match_rate == "N/A",
    }
    return facts, findings


def _ops_report_checks(
    *,
    evidence_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    report_hashes: dict[str, str] = {}
    report_payloads: dict[str, dict[str, Any]] = {}
    for report_name in _REQUIRED_EVIDENCE_REPORTS:
        report_path = evidence_dir / report_name
        payload, issues = _load_json_object(report_path, label=f"RC_GATE_{report_name}")
        findings.extend(issues)
        if payload is not None:
            report_hashes[report_name] = sha256_file(report_path)
            report_payloads[report_name] = payload

    rollback = report_payloads.get("m2_rollback_drill_report.json", {})
    if rollback:
        if rollback.get("drill_passed") is not True:
            findings.append("RC_GATE_ROLLBACK_DRILL_NOT_GREEN")
        if rollback.get("injected_fault_detected") is not True:
            findings.append("RC_GATE_ROLLBACK_DRILL_FAULT_NOT_DETECTED")
        if rollback.get("output_inventory_unchanged") is not True:
            findings.append("RC_GATE_ROLLBACK_DRILL_OUTPUT_INVENTORY_MUTATED")
        if int(rollback.get("dual_write_mismatch_count", 1)) != 0:
            findings.append("RC_GATE_ROLLBACK_DRILL_DUAL_WRITE_MISMATCH")

    rehearsal = report_payloads.get("m2_rehearsal_report.json", {})
    if rehearsal:
        if rehearsal.get("rehearsal_passed") is not True:
            findings.append("RC_GATE_REHEARSAL_NOT_GREEN")
        if rehearsal.get("round_trip_integrity") is not True:
            findings.append("RC_GATE_REHEARSAL_ROUND_TRIP_INTEGRITY_FAILED")
        if rehearsal.get("primary_operator_surface_inactive") is not True:
            findings.append("RC_GATE_REHEARSAL_PRIMARY_OPERATOR_ACTIVE")
        if rehearsal.get("rerun_operator_surface_inactive") is not True:
            findings.append("RC_GATE_REHEARSAL_RERUN_OPERATOR_ACTIVE")

    monitoring = report_payloads.get("m2_post_cutover_monitoring_report.json", {})
    if monitoring:
        if monitoring.get("window_passed") is not True:
            findings.append("RC_GATE_MONITORING_WINDOW_NOT_GREEN")
        if monitoring.get("authority_phase_m2_streak") is not True:
            findings.append("RC_GATE_MONITORING_NOT_M2")
        if monitoring.get("dual_write_mismatch_zero_streak") is not True:
            findings.append("RC_GATE_MONITORING_DUAL_WRITE_MISMATCH")
        if monitoring.get("operator_surface_inactive_streak") is not True:
            findings.append("RC_GATE_MONITORING_OPERATOR_ACTIVE")
        if monitoring.get("manifest_registration_complete_streak") is not True:
            findings.append("RC_GATE_MONITORING_MANIFEST_INCOMPLETE")
        if monitoring.get("schema_complete_streak") is not True:
            findings.append("RC_GATE_MONITORING_SCHEMA_INCOMPLETE")

    return {
        "report_hashes": report_hashes,
        "rollback": rollback,
        "rehearsal": rehearsal,
        "monitoring": monitoring,
        "all_required_reports_present": len(report_payloads) == len(_REQUIRED_EVIDENCE_REPORTS),
    }, findings


def _docs_bundle_checks(
    *,
    docs_root: Path,
    evidence_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    file_hashes: dict[str, str] = {}
    file_texts: dict[str, str] = {}
    for relative_path in _REQUIRED_DOC_FILES:
        path = docs_root / relative_path
        text, issues = _load_text(path, label=f"RC_GATE_{relative_path}")
        findings.extend(issues)
        if text is not None:
            file_hashes[relative_path] = sha256_file(path)
            file_texts[relative_path] = text
    evidence_index_path = evidence_dir / "README.md"
    evidence_text, issues = _load_text(evidence_index_path, label="RC_GATE_EVIDENCE_INDEX")
    findings.extend(issues)
    if evidence_text is not None:
        evidence_key = _display_relative_path(evidence_index_path, root=docs_root)
        file_hashes[evidence_key] = sha256_file(evidence_index_path)
        file_texts[evidence_key] = evidence_text

    readme_text = file_texts.get("README.md", "")
    missing_readme_fragments = _contains_required_fragments(
        text=readme_text,
        required_fragments=(
            "Current public-scope decision:",
            "Current keep-path RC definition:",
            "v3_keep_path_rc_acceptance_memo.md",
        ),
    )
    findings.extend(f"RC_GATE_README_MISSING:{fragment}" for fragment in missing_readme_fragments)

    acceptance_text = file_texts.get("v3_keep_path_rc_acceptance_memo.md", "")
    missing_acceptance_fragments = _contains_required_fragments(
        text=acceptance_text,
        required_fragments=(
            "keep-path RC is accepted as the current public-scope release candidate",
            "no widening is authorized",
            "no operator activation is authorized",
            "m2_rollback_drill_report.json",
            "m2_rehearsal_report.json",
            "m2_post_cutover_monitoring_report.json",
        ),
    )
    findings.extend(
        f"RC_GATE_ACCEPTANCE_MEMO_MISSING:{fragment}"
        for fragment in missing_acceptance_fragments
    )

    roadmap_text = file_texts.get("v3_keep_path_rc_roadmap.md", "")
    missing_roadmap_fragments = _contains_required_fragments(
        text=roadmap_text,
        required_fragments=(
            "current public-scope release candidate",
            "`comparator_scope = path_only_partial`",
            "`comparable_channels = [\"path\"]`",
        ),
    )
    findings.extend(f"RC_GATE_ROADMAP_MISSING:{fragment}" for fragment in missing_roadmap_fragments)

    if evidence_text is not None:
        missing_evidence_fragments = _contains_required_fragments(
            text=evidence_text,
            required_fragments=(
                "m2_rollback_drill_report.json",
                "m2_rehearsal_report.json",
                "m2_post_cutover_monitoring_report.json",
                "run-01",
                "run-30",
            ),
        )
        findings.extend(
            f"RC_GATE_EVIDENCE_INDEX_MISSING:{fragment}"
            for fragment in missing_evidence_fragments
        )

    return {
        "file_hashes": file_hashes,
        "required_doc_files_present": len(
            [relative_path for relative_path in _REQUIRED_DOC_FILES if relative_path in file_texts]
        )
        == len(_REQUIRED_DOC_FILES),
        "evidence_index_present": evidence_text is not None,
    }, findings


def evaluate_keep_path_rc_gate(
    *,
    run_dir: str | Path,
    docs_root: str | Path,
    evidence_dir: str | Path,
) -> dict[str, Any]:
    run_path = Path(run_dir)
    docs_path = Path(docs_root)
    evidence_path = Path(evidence_dir)

    validator_errors, validator_warnings, validator_diagnostics = validate_keep_path_rc_run_directory(run_path)
    run_facts, run_fact_findings = collect_keep_path_rc_run_facts(run_path)
    docs_bundle, docs_findings = _docs_bundle_checks(
        docs_root=docs_path,
        evidence_dir=evidence_path,
    )
    ops_bundle, ops_findings = _ops_report_checks(evidence_dir=evidence_path)

    findings = [
        *validator_errors,
        *run_fact_findings,
        *docs_findings,
        *ops_findings,
    ]
    payload = {
        "artifact_name": RC_GATE_KEEP_PATH_REPORT_ARTIFACT,
        "run_dir": str(run_path.resolve()),
        "docs_root": str(docs_path.resolve()),
        "evidence_dir": str(evidence_path.resolve()),
        "validator": {
            "errors": validator_errors,
            "warnings": validator_warnings,
            "diagnostics": validator_diagnostics,
            "passed": not validator_errors,
        },
        "run_facts": run_facts,
        "docs_bundle": {
            **docs_bundle,
            "passed": not docs_findings,
            "findings": docs_findings,
        },
        "ops_bundle": {
            **ops_bundle,
            "passed": not ops_findings,
            "findings": ops_findings,
        },
        "findings": findings,
        "gate_passed": not findings,
    }
    payload["gate_checks"] = {
        "validator_passed": payload["validator"]["passed"],
        "docs_bundle_passed": payload["docs_bundle"]["passed"],
        "ops_bundle_passed": payload["ops_bundle"]["passed"],
    }
    return payload


def write_keep_path_rc_gate_report(
    *,
    output_dir: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / RC_GATE_KEEP_PATH_REPORT_ARTIFACT
    report_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report_path
