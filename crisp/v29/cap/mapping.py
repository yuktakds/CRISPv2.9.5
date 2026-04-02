"""Cap mapping_table ビルダー: native pair のみを canonical-link ごとに集約する。

設計書 V29-I08: mapping_table は native-only でなければならない。
"""
from __future__ import annotations

from typing import Any

# functional_score 変換辞書（設計書 §Rule2a より固定）
FUNCTIONAL_SCORE_DICT_V1: dict[str, set[str]] = {
    "direction_negative": {"decrease", "lower_is_better", "inhibitory"},
    "direction_positive": {"increase", "higher_is_better", "activating"},
    "assay_negative": {"ic50", "ec50", "kd", "ki"},
    "assay_positive": {"percent_inhibition", "inhibition", "activity"},
}


def functional_score_from_raw(raw: Any, assay_type: str, direction: str) -> float | None:
    """アッセイ raw 値を方向付きの functional_score に変換する。

    変換できない場合は None を返す（行を除外する）。
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None

    direction_lower = str(direction).lower().strip()
    assay_lower = str(assay_type).lower().strip()

    if direction_lower in FUNCTIONAL_SCORE_DICT_V1["direction_negative"]:
        return -value
    if direction_lower in FUNCTIONAL_SCORE_DICT_V1["direction_positive"]:
        return value
    if assay_lower in FUNCTIONAL_SCORE_DICT_V1["assay_negative"]:
        return -value
    if assay_lower in FUNCTIONAL_SCORE_DICT_V1["assay_positive"]:
        return value
    return None


def _column_mean(rows: list[dict[str, Any]], column: str) -> float:
    """列の平均を返す。rows が空の場合は 0.0 を返す。

    Bug2 修正: 旧実装は「呼び出し元が保証する」としていたが、
    実際には空リストが渡される経路があり ZeroDivisionError が発生していた。
    """
    if not rows:
        return 0.0
    return sum(float(r[column]) for r in rows) / len(rows)


def build_mapping_table(
    pair_features_rows: list[dict[str, Any]],
    assays_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """native pair のみを canonical-link ごとに集約して mapping_table を構築する。

    V29-I08: pairing_role != 'native' の行は除外する。
    """
    assay_by_link = {str(r["canonical_link_id"]): r for r in assays_rows}

    # native 行を canonical_link_id でグループ化
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in pair_features_rows:
        if row.get("pairing_role") != "native":
            continue
        grouped.setdefault(str(row["canonical_link_id"]), []).append(row)

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
                "pairing_role": "native",
                "functional_score_dictionary_id": "functional-score-dict-v1",
            }
        )

    return out
