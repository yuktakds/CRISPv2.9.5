from __future__ import annotations

from pathlib import Path
from typing import Any

from crisp.v3.contracts import ChannelEvaluationResult, ChannelEvidence, EvidenceState, RunApplicabilityRecord
from crisp.v3.contracts.cap import CapPartitionCandidate, CapValidationDecision, CapValidationState
from crisp.v3.projectors.cap import project_cap_payload

CAP_CHANNEL_NAME = "cap"
CAP_CHANNEL_FAMILY = "CAP"
_SUPPORTED_PAIRING_ROLES = {"native", "matched_falsification"}
_PAIRING_ROLE_ORDER = {"native": 0, "matched_falsification": 1}
_CAP_INPUT_MISSING = "CAP_INPUT_MISSING"


def _normalize_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _mean(values: list[float | None]) -> float | None:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def _candidate_score(candidate: CapPartitionCandidate) -> float:
    return float(candidate.comb or 0.0) + float(candidate.pas or 0.0)


def _witness_candidate_id(candidates: list[CapPartitionCandidate]) -> str | None:
    if not candidates:
        return None
    ordered = sorted(
        candidates,
        key=lambda candidate: (-_candidate_score(candidate), candidate.candidate_id),
    )
    return ordered[0].candidate_id


def build_cap_partition_candidates(
    pair_features_rows: list[dict[str, Any]],
) -> tuple[CapPartitionCandidate, ...]:
    candidates: list[CapPartitionCandidate] = []
    for index, row in enumerate(pair_features_rows):
        pairing_role = str(row.get("pairing_role", "")).strip()
        if pairing_role not in _SUPPORTED_PAIRING_ROLES:
            continue
        canonical_link_id = str(row.get("canonical_link_id", row.get("link_id", f"link-{index}")))
        molecule_id = str(row.get("molecule_id", row.get("compound_id", f"molecule-{index}")))
        cap_id = str(row.get("cap_id", f"cap-{index}"))
        candidate_id = "::".join((canonical_link_id, pairing_role, molecule_id, cap_id))
        candidates.append(
            CapPartitionCandidate(
                candidate_id=candidate_id,
                pairing_role=pairing_role,
                canonical_link_id=canonical_link_id,
                molecule_id=molecule_id,
                cap_id=cap_id,
                comb=_normalize_float(row.get("comb")),
                pas=_normalize_float(row.get("PAS", row.get("pas"))),
                diagnostics={"source_index": index},
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate.canonical_link_id,
            _PAIRING_ROLE_ORDER[candidate.pairing_role],
            candidate.molecule_id,
            candidate.cap_id,
        )
    )
    return tuple(candidates)


def validate_cap_partition(
    candidates: tuple[CapPartitionCandidate, ...],
    *,
    min_native_count: int = 3,
    accept_margin: float = 0.05,
    provisional_band: float = 0.02,
) -> CapValidationDecision:
    native_candidates = [candidate for candidate in candidates if candidate.pairing_role == "native"]
    falsification_candidates = [candidate for candidate in candidates if candidate.pairing_role == "matched_falsification"]

    native_mean_comb = _mean([candidate.comb for candidate in native_candidates])
    falsification_mean_comb = _mean([candidate.comb for candidate in falsification_candidates])
    native_mean_pas = _mean([candidate.pas for candidate in native_candidates])
    falsification_mean_pas = _mean([candidate.pas for candidate in falsification_candidates])

    validation_margin: float | None = None
    if (
        native_mean_comb is not None
        and falsification_mean_comb is not None
        and native_mean_pas is not None
        and falsification_mean_pas is not None
    ):
        validation_margin = (
            (native_mean_comb - falsification_mean_comb)
            + (native_mean_pas - falsification_mean_pas)
        ) / 2.0
    threshold_margin = None if validation_margin is None else validation_margin - accept_margin

    if not native_candidates:
        state = CapValidationState.REJECTED
        reason_code = "CAP_PARTITION_NATIVE_ABSENT"
    elif not falsification_candidates:
        state = CapValidationState.PROVISIONAL
        reason_code = "CAP_FALSIFICATION_BASELINE_ABSENT"
    elif len(native_candidates) < min_native_count:
        state = CapValidationState.PROVISIONAL
        reason_code = "CAP_SAMPLE_SIZE_LIMITED"
    elif validation_margin is None:
        state = CapValidationState.PROVISIONAL
        reason_code = "CAP_VALIDATION_METRICS_INCOMPLETE"
    elif validation_margin < 0.0:
        state = CapValidationState.REJECTED
        reason_code = "CAP_VALIDATION_REJECTED"
    elif abs(validation_margin - accept_margin) <= provisional_band:
        state = CapValidationState.PROVISIONAL
        reason_code = "CAP_THRESHOLD_NEAR_FLIP"
    elif validation_margin < accept_margin:
        state = CapValidationState.PROVISIONAL
        reason_code = "CAP_MARGIN_BELOW_VALIDATED"
    else:
        state = CapValidationState.VALIDATED
        reason_code = "CAP_VALIDATION_CONFIRMED"

    return CapValidationDecision(
        state=state,
        reason_code=reason_code,
        native_candidate_count=len(native_candidates),
        falsification_candidate_count=len(falsification_candidates),
        native_mean_comb=native_mean_comb,
        falsification_mean_comb=falsification_mean_comb,
        native_mean_pas=native_mean_pas,
        falsification_mean_pas=falsification_mean_pas,
        validation_margin=validation_margin,
        threshold_margin=threshold_margin,
        candidates=candidates,
        native_witness_candidate_id=_witness_candidate_id(native_candidates),
        falsification_witness_candidate_id=_witness_candidate_id(falsification_candidates),
        diagnostics={
            "accept_margin": accept_margin,
            "provisional_band": provisional_band,
            "min_native_count": min_native_count,
        },
    )


def _evidence_state(validation_state: CapValidationState) -> EvidenceState:
    if validation_state is CapValidationState.VALIDATED:
        return EvidenceState.SUPPORTED
    if validation_state is CapValidationState.PROVISIONAL:
        return EvidenceState.INSUFFICIENT
    return EvidenceState.REFUTED


def _applicability_record(detail: str | None) -> RunApplicabilityRecord:
    return RunApplicabilityRecord(
        channel_name=CAP_CHANNEL_NAME,
        family=CAP_CHANNEL_FAMILY,
        scope="run",
        applicable=False,
        reason_code=_CAP_INPUT_MISSING,
        detail=detail,
        diagnostics_source=None,
        diagnostics_payload={},
    )


class CapEvidenceChannel:
    def evaluate(
        self,
        *,
        pair_features_rows: list[dict[str, Any]] | None,
        source: str | Path | None = None,
        min_native_count: int = 3,
        accept_margin: float = 0.05,
        provisional_band: float = 0.02,
    ) -> ChannelEvaluationResult:
        if not pair_features_rows:
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[_applicability_record("pair_features_rows are required for the cap sidecar scaffold")],
            )

        candidates = build_cap_partition_candidates(pair_features_rows)
        if not candidates:
            return ChannelEvaluationResult(
                evidence=None,
                applicability_records=[_applicability_record("no supported pairing_role rows were found")],
            )

        decision = validate_cap_partition(
            candidates,
            min_native_count=min_native_count,
            accept_margin=accept_margin,
            provisional_band=provisional_band,
        )
        evidence = ChannelEvidence(
            channel_name=CAP_CHANNEL_NAME,
            family=CAP_CHANNEL_FAMILY,
            state=_evidence_state(decision.state),
            payload=project_cap_payload(decision),
            source=None if source is None else str(source),
            bridge_metrics={
                "validation_state": decision.state.value,
                "candidate_count": len(decision.candidates),
                "missing_fields_not_inferred": True,
                "truth_source_kind": "read_only_pair_features_snapshot",
            },
        )
        return ChannelEvaluationResult(
            evidence=evidence,
            applicability_records=[],
            diagnostics_payload={"candidate_count": len(decision.candidates)},
        )
