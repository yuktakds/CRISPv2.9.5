from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CapValidationState(StrEnum):
    VALIDATED = "VALIDATED"
    PROVISIONAL = "PROVISIONAL"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class CapPartitionCandidate:
    candidate_id: str
    pairing_role: str
    canonical_link_id: str
    molecule_id: str
    cap_id: str
    comb: float | None
    pas: float | None
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CapValidationDecision:
    state: CapValidationState
    reason_code: str
    native_candidate_count: int
    falsification_candidate_count: int
    native_mean_comb: float | None
    falsification_mean_comb: float | None
    native_mean_pas: float | None
    falsification_mean_pas: float | None
    validation_margin: float | None
    threshold_margin: float | None
    candidates: tuple[CapPartitionCandidate, ...]
    native_witness_candidate_id: str | None = None
    falsification_witness_candidate_id: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
