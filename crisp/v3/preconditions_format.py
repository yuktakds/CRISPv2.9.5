from __future__ import annotations

from typing import Any


def _parse_operator_summary_fields(operator_summary: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "comparable_channels": None,
        "v3_only_evidence_channels": None,
        "v3_only_labels": {},
    }
    for raw_line in operator_summary.splitlines():
        line = raw_line.strip()
        if line.startswith("- comparable_channels: `") and line.endswith("`"):
            value = line[len("- comparable_channels: `") : -1]
            parsed["comparable_channels"] = [] if value == "none" else [item.strip() for item in value.split(",")]
        elif line.startswith("- v3_only_evidence_channels: `") and line.endswith("`"):
            value = line[len("- v3_only_evidence_channels: `") : -1]
            parsed["v3_only_evidence_channels"] = [] if value == "none" else [item.strip() for item in value.split(",")]
        elif line.startswith("- [v3-only] ") and ": `" in line and line.endswith("`"):
            body = line[len("- [v3-only] ") : -1]
            channel_name, lifecycle_state = body.split(": `", 1)
            parsed["v3_only_labels"][channel_name.strip()] = lifecycle_state.strip()
    return parsed
