from __future__ import annotations

from typing import Any


def build_qc_report(*, run_id: str, conditions_run: list[str], excluded_rows_count: int, warnings: list[str], result: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        'run_id': run_id,
        'conditions_run': list(conditions_run),
        'excluded_rows_count': int(excluded_rows_count),
        'warnings': list(warnings),
        'result': result,
    }
    if extra:
        payload.update(extra)
    return payload
