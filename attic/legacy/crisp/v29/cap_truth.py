from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any
import json

from crisp.repro.hashing import sha256_file
from crisp.utils.jsonx import canonical_json_bytes

CAP_TRUTH_SOURCE_REQUIRED_FIELDS = (
    "cap_truth_source_path",
    "cap_truth_source_digest",
    "cap_truth_source_run_id",
    "cap_truth_source_keys",
    "cap_truth_source_layer_consistency",
    "cap_truth_source_status",
)


def _load_json_object(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return source
    payload = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected object payload, got {type(payload).__name__}")
    return payload


def build_cap_truth_source_provenance(
    source: str | Path | dict[str, Any],
    *,
    logical_path: str | None = None,
) -> dict[str, Any]:
    payload = _load_json_object(source)
    if isinstance(source, dict):
        digest = "sha256:" + sha256(canonical_json_bytes(payload)).hexdigest()
        path_label = logical_path or "cap_batch_eval.json"
    else:
        source_path = Path(source)
        digest = sha256_file(source_path)
        path_label = logical_path or source_path.name
    layer_consistency = payload.get("verdict_final") == payload.get("cap_batch_verdict")
    status = "verified" if payload.get("source_of_truth") is True else "invalid"
    return {
        "cap_truth_source_path": path_label,
        "cap_truth_source_digest": digest,
        "cap_truth_source_run_id": payload.get("run_id"),
        "cap_truth_source_keys": sorted(str(key) for key in payload.keys()),
        "cap_truth_source_layer_consistency": bool(layer_consistency),
        "cap_truth_source_status": status,
    }
