from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from crisp.repro.hashing import sha256_file


def load_json_object(path: Path, *, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [f"{label}_READ_ERROR:{exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"{label}_JSON_DECODE_ERROR:{exc.msg}@line{exc.lineno}:col{exc.colno}"]
    if not isinstance(payload, dict):
        return None, [f"{label}_NOT_OBJECT:{type(payload).__name__}"]
    return payload, []


def load_text(path: Path, *, label: str) -> tuple[str | None, list[str]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except OSError as exc:
        return None, [f"{label}_READ_ERROR:{exc}"]


def _display_relative_path(path: Path, *, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def hash_loaded_files(paths: Sequence[Path], *, repo_root: Path) -> dict[str, str]:
    return {
        _display_relative_path(path, root=repo_root): sha256_file(path)
        for path in paths
        if path.exists()
    }


def load_required_docs(
    *,
    docs_root: Path,
    evidence_dir: Path,
    required_doc_files: Sequence[str],
) -> tuple[dict[str, str], list[Path], list[str]]:
    findings: list[str] = []
    texts: dict[str, str] = {}
    loaded_paths: list[Path] = []
    for relative_path in required_doc_files:
        path = docs_root / relative_path
        text, issues = load_text(path, label=f"KEEP_PATH_RC_AUDIT_{relative_path}")
        findings.extend(issues)
        if text is not None:
            texts[relative_path] = text
            loaded_paths.append(path)
    evidence_index_path = evidence_dir / "README.md"
    text, issues = load_text(evidence_index_path, label="KEEP_PATH_RC_AUDIT_EVIDENCE_INDEX")
    findings.extend(issues)
    if text is not None:
        texts["release/evidence/keep_path_rc/README.md"] = text
        loaded_paths.append(evidence_index_path)
    return texts, loaded_paths, findings


def load_required_jsons(
    *,
    evidence_dir: Path,
    history_report_path: Path,
    required_evidence_reports: Sequence[str],
) -> tuple[dict[str, dict[str, Any]], list[Path], list[str]]:
    findings: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}
    loaded_paths: list[Path] = []
    for relative_path in required_evidence_reports:
        path = history_report_path if relative_path == history_report_path.name else evidence_dir / relative_path
        payload, issues = load_json_object(path, label=f"KEEP_PATH_RC_AUDIT_{relative_path}")
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
        payload, issues = load_json_object(path, label=f"KEEP_PATH_RC_AUDIT_{path.name}")
        findings.extend(issues)
        if payload is not None:
            payloads[f"release_packet/{path.name}"] = payload
            loaded_paths.append(path)
    return payloads, loaded_paths, findings


def load_operator_summary(packet_dir: Path) -> tuple[str | None, Path, list[str]]:
    path = packet_dir / "bridge_operator_summary.md"
    text, issues = load_text(path, label="KEEP_PATH_RC_AUDIT_bridge_operator_summary.md")
    return text, path, issues


def load_release_readme(repo_root: Path) -> tuple[str, Path, list[str]]:
    path = repo_root / "docs" / "release" / "README.md"
    text, issues = load_text(path, label="KEEP_PATH_RC_AUDIT_RELEASE_README")
    return text or "", path, issues
