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
    docs_bundle, docs_findings = _docs_bundle_checks(
        docs_root=docs_path,
        evidence_dir=evidence_path,
    )
    ops_bundle, ops_findings = _ops_report_checks(evidence_dir=evidence_path)

    findings = [
        *validator_errors,
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
