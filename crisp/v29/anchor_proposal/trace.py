"""Anchor proposal trace ビルダー（trace-only noop）。

設計書 §B3.5: proposal trace の最低フィールドを満たす。
current snapshot では semantic_mode = 'trace-only-noop' であり
候補列順序のみを記録する（outcome collapse を主張しない）。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .policy import PROPOSAL_POLICY_VERSION


def _stable_hash_of_int_list(values: list[int] | tuple[int, ...]) -> str:
    """整数リストの決定論的 SHA256 ハッシュを返す。"""
    payload = json.dumps(list(values), separators=(",", ":"), sort_keys=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_proposal_trace(
    *,
    ordered_tuple: tuple[int, ...],
    candidate_rows: list[dict[str, Any]],
    legacy_tuple: list[int] | tuple[int, ...],
) -> dict[str, Any]:
    """§B3.5 の必須フィールドを含む proposal trace dict を返す。

    変数名変更（品質改善）:
      旧: by_candidate → source_count_by_type
    """
    source_count_by_type: dict[str, int] = {}
    for row in candidate_rows:
        source = str(row.get("source", "unknown"))
        source_count_by_type[source] = source_count_by_type.get(source, 0) + 1

    struct_conn_present = any(str(r.get("source")) == "struct_conn" for r in candidate_rows)
    near_band_present = any(str(r.get("source")) == "near_band" for r in candidate_rows)

    return {
        # §B3.5 必須フィールド
        "anchor_candidate_atoms": list(ordered_tuple),
        "anchor_candidate_sources": candidate_rows,
        "candidate_order_hash": _stable_hash_of_int_list(ordered_tuple),
        "struct_conn_status": "present" if struct_conn_present else "absent",
        "near_band_triggered": near_band_present,
        "near_band_basis": "candidate_sources" if near_band_present else None,
        "proposal_policy_version": PROPOSAL_POLICY_VERSION,
        "anchor_trials_by_candidate": source_count_by_type,
        # 追加フィールド
        "legacy_union_hash": _stable_hash_of_int_list(legacy_tuple),
        "semantic_mode": "trace-only-noop",
    }
