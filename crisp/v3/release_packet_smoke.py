from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from crisp.repro.hashing import sha256_file

KEEP_PATH_RC_RELEASE_PACKET_SNAPSHOT_ARTIFACT = "release_packet_smoke_snapshot.json"
KEEP_PATH_RC_RELEASE_PACKET_REPORT_ARTIFACT = "release_packet_smoke_report.json"
_RELEASE_PACKET_FILES = (
    "output_inventory.json",
    "verdict_record.json",
    "sidecar_run_record.json",
    "generator_manifest.json",
    "bridge_operator_summary.md",
)
_EVIDENCE_FILES = (
    "m2_rollback_drill_report.json",
    "m2_rehearsal_report.json",
    "m2_post_cutover_monitoring_report.json",
    "rc_gate_keep_path_report.json",
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


def build_keep_path_release_packet_snapshot(
    *,
    packet_dir: str | Path,
    evidence_dir: str | Path,
) -> dict[str, Any]:
    packet_path = Path(packet_dir)
    evidence_path = Path(evidence_dir)
    tracked_hashes: dict[str, str] = {}
    for relative_path in _RELEASE_PACKET_FILES:
        tracked_hashes[f"release_packet/{relative_path}"] = sha256_file(packet_path / relative_path)
    for relative_path in _EVIDENCE_FILES:
        tracked_hashes[relative_path] = sha256_file(evidence_path / relative_path)

    verdict_record = json.loads((packet_path / "verdict_record.json").read_text(encoding="utf-8"))
    output_inventory = json.loads((packet_path / "output_inventory.json").read_text(encoding="utf-8"))
    return {
        "schema_version": "crisp.v3.keep_path_release_packet_snapshot/v1",
        "packet_dir": str(packet_path.resolve()),
        "evidence_dir": str(evidence_path.resolve()),
        "tracked_hashes": tracked_hashes,
        "required_operator_fragments": [
            "[exploratory]",
            f"semantic_policy_version: `{verdict_record['semantic_policy_version']}`",
            "verdict_match_rate: `N/A`",
            "Cap / Catalytic sidecar materialization does not widen the current Path-only comparability claim.",
        ],
        "forbidden_operator_fragments": [
            "v3_shadow_verdict",
            "verdict_match_rate: `1/",
            "verdict_match_rate: `0/",
        ],
        "expected_keep_scope": {
            "comparator_scope": verdict_record["comparator_scope"],
            "comparable_channels": list(verdict_record["comparable_channels"]),
            "v3_shadow_verdict": verdict_record["v3_shadow_verdict"],
            "verdict_match_rate": verdict_record["verdict_match_rate"],
            "output_inventory_generated_outputs": list(output_inventory.get("generated_outputs", [])),
        },
        "metric_contract_note": (
            "path_component_match_rate remains a Path-only metric. "
            "This release packet snapshot does not authorize numeric verdict_match_rate."
        ),
    }


def evaluate_keep_path_release_packet_smoke(
    *,
    packet_dir: str | Path,
    evidence_dir: str | Path,
    snapshot_path: str | Path,
) -> dict[str, Any]:
    packet_path = Path(packet_dir)
    evidence_path = Path(evidence_dir)
    snapshot_file = Path(snapshot_path)
    findings: list[str] = []

    snapshot, issues = _load_json_object(snapshot_file, label="KEEP_PATH_RELEASE_PACKET_SNAPSHOT")
    findings.extend(issues)
    if snapshot is None:
        return {
            "packet_dir": str(packet_path.resolve()),
            "evidence_dir": str(evidence_path.resolve()),
            "snapshot_path": str(snapshot_file.resolve()),
            "findings": findings,
            "smoke_passed": False,
        }

    current_hashes: dict[str, str] = {}
    for relative_path in _RELEASE_PACKET_FILES:
        path = packet_path / relative_path
        current_hashes[f"release_packet/{relative_path}"] = sha256_file(path)
    for relative_path in _EVIDENCE_FILES:
        path = evidence_path / relative_path
        current_hashes[relative_path] = sha256_file(path)

    expected_hashes = snapshot.get("tracked_hashes", {})
    hash_mismatches = sorted(
        key
        for key, expected in expected_hashes.items()
        if current_hashes.get(key) != expected
    )
    findings.extend(f"KEEP_PATH_RELEASE_PACKET_HASH_MISMATCH:{key}" for key in hash_mismatches)

    verdict_record, issues = _load_json_object(
        packet_path / "verdict_record.json",
        label="KEEP_PATH_RELEASE_PACKET_VERDICT_RECORD",
    )
    findings.extend(issues)
    sidecar_run_record, issues = _load_json_object(
        packet_path / "sidecar_run_record.json",
        label="KEEP_PATH_RELEASE_PACKET_SIDECAR_RUN_RECORD",
    )
    findings.extend(issues)
    output_inventory, issues = _load_json_object(
        packet_path / "output_inventory.json",
        label="KEEP_PATH_RELEASE_PACKET_OUTPUT_INVENTORY",
    )
    findings.extend(issues)
    operator_summary, issues = _load_text(
        packet_path / "bridge_operator_summary.md",
        label="KEEP_PATH_RELEASE_PACKET_OPERATOR_SUMMARY",
    )
    findings.extend(issues)
    gate_report, issues = _load_json_object(
        evidence_path / "rc_gate_keep_path_report.json",
        label="KEEP_PATH_RELEASE_PACKET_GATE_REPORT",
    )
    findings.extend(issues)

    if verdict_record is not None:
        expected_keep_scope = snapshot.get("expected_keep_scope", {})
        if verdict_record.get("comparator_scope") != expected_keep_scope.get("comparator_scope"):
            findings.append("KEEP_PATH_RELEASE_PACKET_SCOPE_MISMATCH")
        if list(verdict_record.get("comparable_channels", [])) != list(
            expected_keep_scope.get("comparable_channels", [])
        ):
            findings.append("KEEP_PATH_RELEASE_PACKET_COMPARABLE_CHANNELS_MISMATCH")
        if verdict_record.get("v3_shadow_verdict") != expected_keep_scope.get("v3_shadow_verdict"):
            findings.append("KEEP_PATH_RELEASE_PACKET_V3_SHADOW_VERDICT_ACTIVE")
        if verdict_record.get("verdict_match_rate") != expected_keep_scope.get("verdict_match_rate"):
            findings.append("KEEP_PATH_RELEASE_PACKET_NUMERIC_VERDICT_MATCH_RATE")

    if output_inventory is not None:
        expected_outputs = list(snapshot.get("expected_keep_scope", {}).get("output_inventory_generated_outputs", []))
        if list(output_inventory.get("generated_outputs", [])) != expected_outputs:
            findings.append("KEEP_PATH_RELEASE_PACKET_OUTPUT_INVENTORY_CHANGED")

    if sidecar_run_record is not None:
        if sidecar_run_record.get("rc2_outputs_unchanged") is not True:
            findings.append("KEEP_PATH_RELEASE_PACKET_RC2_OUTPUTS_CHANGED")

    if operator_summary is not None:
        missing_required = _contains_required_fragments(
            text=operator_summary,
            required_fragments=tuple(snapshot.get("required_operator_fragments", [])),
        )
        findings.extend(
            f"KEEP_PATH_RELEASE_PACKET_OPERATOR_MISSING:{fragment}"
            for fragment in missing_required
        )
        forbidden_hits = [
            fragment
            for fragment in snapshot.get("forbidden_operator_fragments", [])
            if fragment in operator_summary
        ]
        findings.extend(
            f"KEEP_PATH_RELEASE_PACKET_OPERATOR_FORBIDDEN:{fragment}"
            for fragment in forbidden_hits
        )

    if gate_report is not None and gate_report.get("gate_passed") is not True:
        findings.append("KEEP_PATH_RELEASE_PACKET_GATE_REPORT_NOT_GREEN")

    return {
        "schema_version": "crisp.v3.keep_path_release_packet_smoke/v1",
        "packet_dir": str(packet_path.resolve()),
        "evidence_dir": str(evidence_path.resolve()),
        "snapshot_path": str(snapshot_file.resolve()),
        "tracked_hashes": current_hashes,
        "hash_mismatches": hash_mismatches,
        "findings": findings,
        "smoke_passed": not findings,
    }


def write_keep_path_release_packet_snapshot(
    *,
    output_dir: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_path / KEEP_PATH_RC_RELEASE_PACKET_SNAPSHOT_ARTIFACT
    snapshot_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return snapshot_path


def write_keep_path_release_packet_smoke_report(
    *,
    output_dir: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / KEEP_PATH_RC_RELEASE_PACKET_REPORT_ARTIFACT
    report_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report_path
