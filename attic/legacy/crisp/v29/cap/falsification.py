"""Cap falsification_table ビルダー: matched_falsification のみを集約する。

設計書 V29-I08: falsification_table は matched_falsification-only でなければならない。
"""
from __future__ import annotations

from typing import Any

from crisp.v29.cap.mapping import _column_mean, functional_score_from_raw


def build_falsification_table(
    pair_features_rows: list[dict[str, Any]],
    assays_rows: list[dict[str, Any]],
    donor_plan: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """matched_falsification pair を canonical-link ごとに集約して falsification_table を構築する。

    V29-I08: pairing_role != 'matched_falsification' の行は除外する。
    """
    assay_by_link = {str(r["canonical_link_id"]): r for r in assays_rows}

    # matched_falsification 行を canonical_link_id でグループ化
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in pair_features_rows:
        if row.get("pairing_role") != "matched_falsification":
            continue
        grouped.setdefault(str(row["canonical_link_id"]), []).append(row)

    shuffle_donor_pool_hash = None if donor_plan is None else donor_plan.get("shuffle_donor_pool_hash")
    donor_plan_hash = None if donor_plan is None else donor_plan.get("donor_plan_hash")

    out: list[dict[str, Any]] = []
    for canonical_link_id, rows in grouped.items():
        assay = assay_by_link.get(canonical_link_id)
        if assay is None:
            continue

        functional_score = functional_score_from_raw(
            assay.get("functional_score_raw"),
            str(assay.get("assay_type", "")),
            str(assay.get("direction", "")),
        )
        if functional_score is None:
            continue

        exemplar = rows[0]
        out.append(
            {
                "canonical_link_id": canonical_link_id,
                "molecule_id": exemplar["molecule_id"],
                "target_id": exemplar["target_id"],
                "condition_hash": assay["condition_hash"],
                "functional_score_raw": assay["functional_score_raw"],
                "assay_type": assay["assay_type"],
                "direction": assay["direction"],
                "unit": assay.get("unit"),
                "functional_score": functional_score,
                "comb": _column_mean(rows, "comb"),
                "P_hit": _column_mean(rows, "P_hit"),
                "PAS": _column_mean(rows, "PAS"),
                "dist": _column_mean(rows, "dist"),
                "LPCS": _column_mean(rows, "LPCS"),
                "PCF": _column_mean(rows, "PCF"),
                "pairing_role": "matched_falsification",
                "shuffle_donor_pool_hash": shuffle_donor_pool_hash,
                "donor_plan_hash": donor_plan_hash,
                "functional_score_dictionary_id": "functional-score-dict-v1",
            }
        )

    return out
