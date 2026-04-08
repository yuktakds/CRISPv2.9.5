from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CatalyticConstraintState(StrEnum):
    SATISFIED = "SATISFIED"
    PARTIAL = "PARTIAL"
    VIOLATED = "VIOLATED"


@dataclass(frozen=True, slots=True)
class CatalyticConstraintObservation:
    state: CatalyticConstraintState
    reason_code: str
    record_count: int
    rows_with_proposal_trace: int
    rows_with_candidate_order_hash: int
    rows_with_stage_history: int
    rows_with_trace_only_policy: int
    rows_with_trace_only_semantic_mode: int
    near_band_triggered_count: int
    max_anchor_candidate_count: int
    observed_policy_versions: tuple[str, ...]
    observed_semantic_modes: tuple[str, ...]
    sample_molecule_ids: tuple[str, ...]
    struct_conn_status_counts: dict[str, int] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
