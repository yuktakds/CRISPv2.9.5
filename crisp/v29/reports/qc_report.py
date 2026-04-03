from __future__ import annotations

from typing import Any


def build_qc_report(
    *,
    run_id: str,
    conditions_run: list[str],
    excluded_rows_count: int,
    warnings: list[str],
    result: str,
    comparison_type: str | None = None,
    skip_reason_codes: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        'run_id': run_id,
        'conditions_run': list(conditions_run),
        'excluded_rows_count': int(excluded_rows_count),
        'warnings': list(warnings),
        'result': result,
        'comparison_type': comparison_type,
        'skip_reason_codes': [] if skip_reason_codes is None else list(skip_reason_codes),
    }
    if extra:
        payload.update(extra)
    return payload
