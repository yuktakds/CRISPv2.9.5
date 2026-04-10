from __future__ import annotations

from dataclasses import asdict
from typing import Any

from crisp.v3.contracts import BridgeComparisonResult
from crisp.v3.policy import SEMANTIC_POLICY_VERSION


def comparison_result_to_dict(
    result: BridgeComparisonResult,
    *,
    comparator_contract_version: str,
    final_verdict_fields: set[str],
) -> dict[str, Any]:
    compound_reports = []
    for report in result.compound_reports:
        payload = asdict(report)
        for field_name in final_verdict_fields:
            payload.pop(field_name, None)
        compound_reports.append(payload)
    return {
        "summary": asdict(result.summary),
        "run_drift_report": asdict(result.run_report),
        "compound_drift_reports": compound_reports,
        "drifts": [asdict(drift) for drift in result.drifts],
        "semantic_policy_version": SEMANTIC_POLICY_VERSION,
        "comparator_contract_version": comparator_contract_version,
    }
