from __future__ import annotations

from numbers import Real
from pathlib import Path
from typing import Any

from crisp.v3.contracts import ChannelEvaluationResult, ChannelEvidence, EvidenceState, RunApplicabilityRecord

OFFTARGET_CHANNEL_NAME = "offtarget"
OFFTARGET_CHANNEL_FAMILY = "OFFTARGET"
_OFFTARGET_INPUT_MISSING = "OFFTARGET_INPUT_MISSING"


def _applicability_record(detail: str | None) -> RunApplicabilityRecord:
    return RunApplicabilityRecord(
        channel_name=OFFTARGET_CHANNEL_NAME,
        family=OFFTARGET_CHANNEL_FAMILY,
        scope="run",
        applicable=False,
        reason_code=_OFFTARGET_INPUT_MISSING,
        detail=detail,
        diagnostics_source=None,
        diagnostics_payload={},
    )


class OffTargetEvidenceChannel:
    def evaluate(
        self,
        *,
        core_compound_rows: list[dict[str, Any]] | None,
        source: str | Path | None = None,
    ) -> ChannelEvaluationResult:
        if not core_compound_rows:
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[_applicability_record("core_compounds rows are required for thin offtarget wrapper")],
            )

        distances = [
            float(row["best_offtarget_distance"])
            for row in core_compound_rows
            if isinstance(row.get("best_offtarget_distance"), Real) and not isinstance(row.get("best_offtarget_distance"), bool)
        ]
        if not distances:
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[_applicability_record("best_offtarget_distance is missing from core_compounds snapshot")],
            )
        best_offtarget_distance = min(distances)
        evidence = ChannelEvidence(
            channel_name=OFFTARGET_CHANNEL_NAME,
            family=OFFTARGET_CHANNEL_FAMILY,
            state=EvidenceState.SUPPORTED,
            payload={
                "quantitative_metrics": {
                    "best_offtarget_distance": best_offtarget_distance,
                    "record_count": len(core_compound_rows),
                },
                "witness_bundle": {
                    "source_kind": "thin_offtarget_channel_wrapper",
                },
            },
            source=None if source is None else str(source),
            bridge_metrics={
                "truth_source_kind": "read_only_core_compounds_snapshot",
                "wrapper_kind": "thin_offtarget_channel_wrapper",
            },
        )
        return ChannelEvaluationResult(
            evidence=evidence,
            applicability_records=[],
            diagnostics_payload={"record_count": len(core_compound_rows)},
        )
