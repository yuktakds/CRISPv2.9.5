from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crisp.v3.channels.cap import CapEvidenceChannel
from crisp.v3.channels.catalytic import CatalyticEvidenceChannel
from crisp.v3.channels.offtarget import OffTargetEvidenceChannel
from crisp.v3.contracts import (
    ChannelEvaluationResult,
    ChannelEvidence,
    RunApplicabilityRecord,
    SidecarOptions,
    SidecarSnapshot,
)
from crisp.v3.io.tableio import read_records_table
from crisp.v3.path_channel import PathEvidenceChannel
from crisp.v3.policy import CAP_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME
from crisp.v3.preconditions import ChannelState
from crisp.v3.source_provenance import _resolve_catalytic_evidence_core_path


@dataclass(frozen=True, slots=True)
class ChannelExecutionState:
    path_result: ChannelEvaluationResult
    cap_result: ChannelEvaluationResult | None
    catalytic_result: ChannelEvaluationResult | None
    offtarget_result: ChannelEvaluationResult | None
    path_evidences: list[ChannelEvidence]
    cap_evidences: list[ChannelEvidence]
    catalytic_evidences: list[ChannelEvidence]
    evidences: list[ChannelEvidence]
    applicability_records: list[RunApplicabilityRecord]


def derive_channel_states(
    *,
    options: SidecarOptions,
    execution: ChannelExecutionState,
) -> tuple[ChannelState, ChannelState, ChannelState]:
    path_state = (
        ChannelState.OBSERVATION_MATERIALIZED
        if execution.path_result.evidence is not None
        else ChannelState.APPLICABILITY_ONLY
    )
    cap_state = (
        ChannelState.DISABLED
        if not options.cap_enabled
        else ChannelState.APPLICABILITY_ONLY
        if execution.cap_result is not None and execution.cap_result.evidence is None
        else ChannelState.OBSERVATION_MATERIALIZED
    )
    catalytic_state = (
        ChannelState.DISABLED
        if not options.catalytic_enabled
        else ChannelState.APPLICABILITY_ONLY
        if execution.catalytic_result is not None and execution.catalytic_result.evidence is None
        else ChannelState.OBSERVATION_MATERIALIZED
    )
    return path_state, cap_state, catalytic_state


def execute_channels(
    *,
    snapshot: SidecarSnapshot,
    options: SidecarOptions,
) -> ChannelExecutionState:
    path_result = PathEvidenceChannel().evaluate(
        config=snapshot.config,
        pat_diagnostics_path=snapshot.pat_diagnostics_path,
        pathyes_force_false=snapshot.pathyes_force_false_requested,
    )
    path_evidences = [] if path_result.evidence is None else [path_result.evidence]

    cap_result: ChannelEvaluationResult | None = None
    catalytic_result: ChannelEvaluationResult | None = None
    offtarget_result: ChannelEvaluationResult | None = None
    cap_evidences: list[ChannelEvidence] = []
    catalytic_evidences: list[ChannelEvidence] = []

    if options.cap_enabled:
        cap_result = _run_cap_channel(snapshot)
        cap_evidences = [] if cap_result.evidence is None else [cap_result.evidence]
    if options.catalytic_enabled:
        catalytic_result = _run_catalytic_channel(snapshot)
        catalytic_evidences = [] if catalytic_result.evidence is None else [catalytic_result.evidence]
        offtarget_result = _run_offtarget_channel(snapshot)

    applicability_records = list(path_result.applicability_records)
    if cap_result is not None:
        applicability_records.extend(cap_result.applicability_records)
    if catalytic_result is not None:
        applicability_records.extend(catalytic_result.applicability_records)

    evidences = [*path_evidences, *cap_evidences, *catalytic_evidences]
    return ChannelExecutionState(
        path_result=path_result,
        cap_result=cap_result,
        catalytic_result=catalytic_result,
        offtarget_result=offtarget_result,
        path_evidences=path_evidences,
        cap_evidences=cap_evidences,
        catalytic_evidences=catalytic_evidences,
        evidences=evidences,
        applicability_records=applicability_records,
    )


def _cap_input_missing_result(detail: str) -> ChannelEvaluationResult:
    return ChannelEvaluationResult(
        evidence=None,
        applicability_records=[
            RunApplicabilityRecord(
                channel_name=CAP_CHANNEL_NAME,
                family="CAP",
                scope="run",
                applicable=False,
                reason_code="CAP_INPUT_MISSING",
                detail=detail,
                diagnostics_source=None,
                diagnostics_payload={},
            )
        ],
    )


def _run_cap_channel(snapshot: SidecarSnapshot) -> ChannelEvaluationResult:
    source_path = snapshot.cap_pair_features_path
    if source_path is None:
        return _cap_input_missing_result("cap pair_features artifact is not available in this snapshot")

    pair_features_path = Path(source_path)
    if not pair_features_path.exists():
        return _cap_input_missing_result(f"{pair_features_path} not found")

    try:
        pair_features_rows = read_records_table(pair_features_path)
    except Exception as exc:
        return _cap_input_missing_result(f"{pair_features_path}: {exc}")

    return CapEvidenceChannel().evaluate(
        pair_features_rows=pair_features_rows,
        source=pair_features_path,
    )


def _catalytic_input_missing_result(detail: str) -> ChannelEvaluationResult:
    return ChannelEvaluationResult(
        evidence=None,
        applicability_records=[
            RunApplicabilityRecord(
                channel_name=CATALYTIC_CHANNEL_NAME,
                family="CATALYTIC",
                scope="run",
                applicable=False,
                reason_code="CATALYTIC_INPUT_MISSING",
                detail=detail,
                diagnostics_source=None,
                diagnostics_payload={},
            )
        ],
    )


def _run_catalytic_channel(snapshot: SidecarSnapshot) -> ChannelEvaluationResult:
    source_path = _resolve_catalytic_evidence_core_path(snapshot)
    if source_path is None:
        return _catalytic_input_missing_result("evidence_core artifact is not available in this snapshot")

    evidence_core_path = Path(source_path)
    try:
        evidence_core_rows = read_records_table(evidence_core_path)
    except Exception as exc:
        return _catalytic_input_missing_result(f"{evidence_core_path}: {exc}")

    core_compounds_path = snapshot.core_compounds_path
    if core_compounds_path is not None and Path(core_compounds_path).exists():
        core_compound_rows = read_records_table(core_compounds_path)
        compound_index = {
            str(row.get("molecule_id")): row
            for row in core_compound_rows
            if row.get("molecule_id") is not None
        }
        enriched_rows = []
        for row in evidence_core_rows:
            enriched_row = dict(row)
            core_row = compound_index.get(str(row.get("molecule_id")))
            if core_row is not None and "best_target_distance" in core_row:
                enriched_row["best_target_distance"] = core_row.get("best_target_distance")
            enriched_rows.append(enriched_row)
        evidence_core_rows = enriched_rows

    return CatalyticEvidenceChannel().evaluate(
        evidence_core_rows=evidence_core_rows,
        source=evidence_core_path,
    )


def _run_offtarget_channel(snapshot: SidecarSnapshot) -> ChannelEvaluationResult:
    core_compounds_path = snapshot.core_compounds_path
    if core_compounds_path is None or not Path(core_compounds_path).exists():
        return OffTargetEvidenceChannel().evaluate(
            core_compound_rows=None,
            source=core_compounds_path,
        )
    return OffTargetEvidenceChannel().evaluate(
        core_compound_rows=read_records_table(core_compounds_path),
        source=core_compounds_path,
    )
