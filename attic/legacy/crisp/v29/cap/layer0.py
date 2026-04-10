"""Cap Layer0: pair (molecule, cap) ごとの幾何学的観測量を計算する。

設計書 §Cap-Layer0 に準拠。

責務:
  - 分子の化学プロパティ（重原子数、ヘテロ原子数、環数、回転可能結合数）を計算する
  - cap の軸ベクトル・極座標から幾何学的スコア (P_hit, comb) を推定する
  - Layer0 は観測量の計算のみを行う。PASS/FAIL/UNCLEAR は返さない（V29-I01）。

出力列:
  dist, angle, productive_hits, P_hit, comb,
  rotation_index_count, heavy_atom_count, hetero_atom_count, ring_count,
  rotatable_bonds, cap_motion_class, cap_axis_norm, cap_polar_count
"""
from __future__ import annotations

import json
import math
from typing import Any

from rdkit import Chem
from rdkit.Chem import Lipinski


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _to_float(value: Any, default: float = 0.0) -> float:
    """任意の値を float に変換する。変換不能な場合は default を返す。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sigmoid(x: float) -> float:
    """ロジスティックシグモイド関数。"""
    return 1.0 / (1.0 + math.exp(-x))


def _parse_polar_coords(raw: Any) -> list[Any]:
    """polar_coords_json を list に解析する。解析不能な場合は空リスト。"""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


# ---------------------------------------------------------------------------
# Layer0 メイン
# ---------------------------------------------------------------------------

def run_layer0(
    pair_plan_rows: list[dict[str, Any]],
    caps_rows: list[dict[str, Any]],
    n_rotations: int,
) -> list[dict[str, Any]]:
    """pair ごとに Layer0 観測量を計算して返す。

    Args:
        pair_plan_rows: build_pair_plan() の出力。
        caps_rows: cap メタデータ（axis, polar_coords_json 等を含む）。
        n_rotations: rotation 試行数（resource_profile から決まる）。

    Returns:
        pair_plan_rows の各行に Layer0 観測量列を追加した list。
    """
    cap_by_id = {str(r["cap_id"]): r for r in caps_rows}
    result_rows: list[dict[str, Any]] = []

    for pair in pair_plan_rows:
        smiles = str(pair["smiles"])
        mol = Chem.MolFromSmiles(smiles)

        # --- 分子プロパティ ---
        if mol is None:
            heavy_atom_count = hetero_atom_count = ring_count = rotatable_bonds = 0
        else:
            heavy_atom_count = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)
            hetero_atom_count = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() not in (1, 6))
            ring_count = mol.GetRingInfo().NumRings()
            rotatable_bonds = int(Lipinski.NumRotatableBonds(mol))

        # --- cap 幾何学プロパティ ---
        cap = cap_by_id[str(pair["cap_id"])]
        axis = [
            _to_float(cap.get("axis_x")),
            _to_float(cap.get("axis_y")),
            _to_float(cap.get("axis_z")),
        ]
        axis_norm = math.sqrt(sum(v * v for v in axis))
        polar_coords = _parse_polar_coords(cap.get("polar_coords_json"))
        polar_count = len(polar_coords)

        # --- 幾何学スコアの計算 ---
        # ligand_index: ヘテロ原子 + 環の密度（分子の極性・剛直性のプロキシ）
        ligand_index = (hetero_atom_count + ring_count + 1.0) / max(heavy_atom_count + rotatable_bonds + 1.0, 1.0)
        # dist: cap 軸と分子 ligand_index のずれ
        dist = abs(axis_norm - ligand_index)
        # angle_score: cap 軸の z 成分（0〜1）
        angle_score = 0.0 if axis_norm == 0 else abs(axis[2]) / axis_norm
        angle_deg = 180.0 * angle_score

        # P_hit: sigmoid による hit 確率推定
        p_hit = _sigmoid(
            1.5 * angle_score
            + 0.4 * hetero_atom_count
            + 0.2 * ring_count
            + 0.1 * polar_count
            - 0.3 * dist
            - 0.2 * rotatable_bonds
        )

        # productive_hits: rotation 試行数に対する推定 hit 数（1〜16 にクランプ）
        productive_hits = int(round(p_hit * max(1, min(n_rotations, 16))))

        # comb: P_hit と角度スコアの複合指標
        comb = p_hit * (0.5 + 0.5 * angle_score)

        result_rows.append(
            {
                **pair,
                "dist": float(dist),
                "angle": float(angle_deg),
                "productive_hits": int(productive_hits),
                "P_hit": float(p_hit),
                "comb": float(comb),
                "rotation_index_count": int(n_rotations),
                "heavy_atom_count": int(heavy_atom_count),
                "hetero_atom_count": int(hetero_atom_count),
                "ring_count": int(ring_count),
                "rotatable_bonds": int(rotatable_bonds),
                "cap_motion_class": cap.get("motion_class"),
                "cap_axis_norm": float(axis_norm),
                "cap_polar_count": int(polar_count),
            }
        )

    return result_rows
