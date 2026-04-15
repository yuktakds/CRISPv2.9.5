from __future__ import annotations

from pathlib import Path
from typing import Any

from crisp.utils.jsonx import canonical_json_bytes


def write_evidence_artifact(path: str | Path, evidence: dict[str, Any]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical_json_bytes(evidence))
    return out
