from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.release_packet_smoke import (
    KEEP_PATH_RC_RELEASE_PACKET_SNAPSHOT_ARTIFACT,
    build_keep_path_release_packet_snapshot,
    evaluate_keep_path_release_packet_smoke,
    write_keep_path_release_packet_snapshot,
)
from tests.v3.test_keep_path_rc_gate import (
    _output_inventory,
    _sidecar_run_record,
    _verdict_record,
    _write_json,
)


def _build_release_packet(tmp_path: Path) -> tuple[Path, Path]:
    packet_dir = tmp_path / "release_packet"
    evidence_dir = tmp_path / "evidence"
    packet_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    _write_json(packet_dir / "output_inventory.json", _output_inventory())
    _write_json(packet_dir / "verdict_record.json", _verdict_record())
    _write_json(packet_dir / "sidecar_run_record.json", _sidecar_run_record() | {"rc2_outputs_unchanged": True})
    _write_json(
        packet_dir / "generator_manifest.json",
        {
            "schema_version": "crisp.v3.generator_manifest/v1",
            "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
            "outputs": [],
        },
    )
    (packet_dir / "bridge_operator_summary.md").write_text(
        "# [exploratory] Bridge Operator Summary\n\n"
        "- semantic_policy_version: `crisp.v3.semantic_policy/rev3-sidecar-first`\n"
        "- verdict_match_rate: `N/A`\n\n"
        "Cap / Catalytic sidecar materialization does not widen the current Path-only comparability claim.\n",
        encoding="utf-8",
    )
    _write_json(evidence_dir / "m2_rollback_drill_report.json", {"drill_passed": True})
    _write_json(evidence_dir / "m2_rehearsal_report.json", {"rehearsal_passed": True})
    _write_json(evidence_dir / "m2_post_cutover_monitoring_report.json", {"window_passed": True})
    _write_json(evidence_dir / "rc_gate_keep_path_report.json", {"gate_passed": True})
    return packet_dir, evidence_dir


def test_release_packet_smoke_passes_against_snapshot(tmp_path: Path) -> None:
    packet_dir, evidence_dir = _build_release_packet(tmp_path)
    snapshot = build_keep_path_release_packet_snapshot(
        packet_dir=packet_dir,
        evidence_dir=evidence_dir,
    )
    snapshot_path = write_keep_path_release_packet_snapshot(
        output_dir=evidence_dir,
        payload=snapshot,
    )

    payload = evaluate_keep_path_release_packet_smoke(
        packet_dir=packet_dir,
        evidence_dir=evidence_dir,
        snapshot_path=snapshot_path,
    )

    assert snapshot_path.name == KEEP_PATH_RC_RELEASE_PACKET_SNAPSHOT_ARTIFACT
    assert payload["hash_mismatches"] == []
    assert payload["smoke_passed"] is True


def test_release_packet_smoke_fails_when_operator_surface_loses_exploratory_label(tmp_path: Path) -> None:
    packet_dir, evidence_dir = _build_release_packet(tmp_path)
    snapshot = build_keep_path_release_packet_snapshot(
        packet_dir=packet_dir,
        evidence_dir=evidence_dir,
    )
    snapshot_path = write_keep_path_release_packet_snapshot(
        output_dir=evidence_dir,
        payload=snapshot,
    )
    (packet_dir / "bridge_operator_summary.md").write_text(
        "# Bridge Operator Summary\n\n"
        "- semantic_policy_version: `crisp.v3.semantic_policy/rev3-sidecar-first`\n"
        "- verdict_match_rate: `N/A`\n",
        encoding="utf-8",
    )

    payload = evaluate_keep_path_release_packet_smoke(
        packet_dir=packet_dir,
        evidence_dir=evidence_dir,
        snapshot_path=snapshot_path,
    )

    assert payload["smoke_passed"] is False
    assert any(
        finding.startswith("KEEP_PATH_RELEASE_PACKET_OPERATOR_MISSING:[exploratory]")
        or finding == "KEEP_PATH_RELEASE_PACKET_HASH_MISMATCH:release_packet/bridge_operator_summary.md"
        for finding in payload["findings"]
    )
