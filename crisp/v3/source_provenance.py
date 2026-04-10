from __future__ import annotations

from pathlib import Path
from typing import Any

from crisp.repro.hashing import sha256_file, sha256_json
from crisp.v29.tableio import read_records_table
from crisp.v3.contracts import SidecarSnapshot


def _source_label(path_value: str | None, *, snapshot: SidecarSnapshot) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    out_dir = Path(snapshot.out_dir)
    repo_root = Path(snapshot.repo_root)
    for base in (out_dir, repo_root):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name


def _source_location_kind(path_value: str | None, *, snapshot: SidecarSnapshot) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    out_dir = Path(snapshot.out_dir)
    repo_root = Path(snapshot.repo_root)
    try:
        path.relative_to(out_dir)
        return "run_output_snapshot"
    except ValueError:
        pass
    try:
        path.relative_to(repo_root)
        return "repo_input_snapshot"
    except ValueError:
        pass
    return "external_input_snapshot"


def _source_descriptor(
    path_value: str | None,
    *,
    kind: str,
    snapshot: SidecarSnapshot,
    digest_override: str | None = None,
) -> dict[str, Any]:
    digest = None
    if digest_override is not None:
        digest = digest_override
    elif path_value is not None and Path(path_value).exists():
        digest = sha256_file(path_value)
    return {
        "kind": kind,
        "source_label": _source_label(path_value, snapshot=snapshot),
        "source_location_kind": _source_location_kind(path_value, snapshot=snapshot),
        "source_digest": digest,
    }


def _cap_pair_features_semantic_digest(path_value: str | None) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    rows = read_records_table(path)
    normalized_rows = []
    for row in rows:
        normalized_row = {
            str(key): value
            for key, value in dict(row).items()
            if key != "run_id"
        }
        normalized_rows.append(normalized_row)
    return sha256_json(normalized_rows)


def _catalytic_evidence_core_semantic_digest(path_value: str | None) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    if not path.exists():
        return None

    def _json_ready(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): _json_ready(subvalue) for key, subvalue in value.items()}
        if isinstance(value, list):
            return [_json_ready(item) for item in value]
        if isinstance(value, tuple):
            return [_json_ready(item) for item in value]
        if hasattr(value, "tolist") and not isinstance(value, (str, bytes, bytearray)):
            return _json_ready(value.tolist())
        return value

    rows = read_records_table(path)
    normalized_rows = []
    for row in rows:
        normalized_row = {
            str(key): _json_ready(value)
            for key, value in dict(row).items()
            if key not in {"run_id", "evidence_path"}
        }
        normalized_rows.append(normalized_row)
    normalized_rows.sort(
        key=lambda row: (
            str(row.get("molecule_id", "")),
            str(row.get("target_id", "")),
            str(row.get("candidate_order_hash", "")),
        )
    )
    return sha256_json(normalized_rows)


def _path_truth_source_chain(snapshot: SidecarSnapshot) -> list[dict[str, Any]]:
    return [
        {
            "stage": "input_snapshot",
            **_source_descriptor(
                snapshot.pat_diagnostics_path,
                kind="pat_diagnostics_json",
                snapshot=snapshot,
            ),
        },
        {
            "stage": "channel_builder",
            "builder": "crisp.v3.path_channel.PathEvidenceChannel.evaluate",
            "projector": "crisp.v3.path_channel.project_path_payload",
            "channel_evidence_artifact": "channel_evidence_path.jsonl",
        },
        {
            "stage": "bridge_route",
            "bridge": "crisp.v3.scv_bridge.SCVBridge.route",
            "observation_artifact": "observation_bundle.json",
        },
    ]


def _cap_truth_source_chain(snapshot: SidecarSnapshot, *, enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return [
            {
                "stage": "channel_toggle",
                "kind": "cap_sidecar_opt_in",
                "status": "disabled",
            }
        ]
    return [
        {
            "stage": "input_snapshot",
            **_source_descriptor(
                snapshot.cap_pair_features_path,
                kind="pair_features_snapshot",
                snapshot=snapshot,
                digest_override=_cap_pair_features_semantic_digest(snapshot.cap_pair_features_path),
            ),
        },
        {
            "stage": "channel_builder",
            "builder": "crisp.v3.channels.cap.CapEvidenceChannel.evaluate",
            "projector": "crisp.v3.projectors.cap.project_cap_payload",
            "channel_evidence_artifact": "channel_evidence_cap.jsonl",
        },
        {
            "stage": "bridge_route",
            "bridge": "crisp.v3.scv_bridge.SCVBridge.route",
            "observation_artifact": "observation_bundle.json",
        },
    ]


def _resolve_catalytic_evidence_core_path(snapshot: SidecarSnapshot) -> str | None:
    run_dir = Path(snapshot.out_dir)
    for candidate in (run_dir / "evidence_core.parquet", run_dir / "evidence_core.jsonl"):
        if candidate.exists():
            return str(candidate)
    return None


def _catalytic_truth_source_chain(snapshot: SidecarSnapshot, *, enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return [
            {
                "stage": "channel_toggle",
                "kind": "catalytic_sidecar_opt_in",
                "status": "disabled",
            }
        ]
    source_path = _resolve_catalytic_evidence_core_path(snapshot)
    return [
        {
            "stage": "input_snapshot",
            **_source_descriptor(
                source_path,
                kind="evidence_core_snapshot",
                snapshot=snapshot,
                digest_override=_catalytic_evidence_core_semantic_digest(source_path),
            ),
        },
        {
            "stage": "channel_builder",
            "builder": "crisp.v3.channels.catalytic.CatalyticEvidenceChannel.evaluate",
            "projector": "crisp.v3.projectors.catalytic.project_catalytic_payload",
            "channel_evidence_artifact": "channel_evidence_catalytic.jsonl",
        },
        {
            "stage": "bridge_route",
            "bridge": "crisp.v3.scv_bridge.SCVBridge.route",
            "observation_artifact": "observation_bundle.json",
        },
    ]
