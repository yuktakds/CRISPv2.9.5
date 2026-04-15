"""Anchor candidate proposal policy（trace-only noop）。

設計書 §B3: Rule3 = AnchorCandidateProposalPolicy。
current snapshot では trace-only noop であり outcome collapse を期待しない。
"""
from __future__ import annotations

from typing import Any

# core_bridge.py の PROPOSAL_POLICY_VERSION と一致させること
PROPOSAL_POLICY_VERSION = "v29.trace-only.noop"

# 候補ソースの優先順位（struct_conn > smarts_union > near_band）
_SOURCE_PRIORITY: dict[str, int] = {
    "struct_conn": 0,
    "smarts_union": 1,
    "near_band": 2,
}


def order_anchor_candidates(candidate_rows: list[dict[str, Any]]) -> tuple[int, ...]:
    """候補原子を source 優先度 → atom_index で昇順ソートした tuple を返す。

    §B3.3: CONTINUE / FINALIZE の判定をしない。
           Anchoring predicate を再定義しない。
    """
    sorted_rows = sorted(
        candidate_rows,
        key=lambda r: (
            _SOURCE_PRIORITY.get(str(r.get("source", "")), 99),
            int(r.get("atom_index", -1)),
        ),
    )
    return tuple(int(r["atom_index"]) for r in sorted_rows)
