"""Cap Layer1: Layer0 の幾何学的観測量から kinetics-proxy 特徴量を計算する。

設計書 §Cap-Layer1 に準拠。

責務:
  - LPCS (Ligand-cap Productive Contact Share): rotation あたりの productive hit 割合
  - PCF (Productive Contact Fraction): 極性・ヘテロ成分の寄与割合
  - PAS (Productive Approach Score): LPCS × PCF の積（kinetics-proxy）
  - rotation_graph_metric: 環 + polar の幾何学的密度
  - Layer1 は観測量の計算のみを行う（V29-I01）。
"""
from __future__ import annotations

from typing import Any


def run_layer1(layer0_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Layer0 rows に Layer1 特徴量列を追加して返す。

    Args:
        layer0_rows: run_layer0() の出力。

    Returns:
        Layer0 全列 + LPCS, PCF, PAS, r_nb_deg, largest_productive_component_share,
        preproductive_contact_fraction, rotation_graph_metric を追加した list。
    """
    result_rows: list[dict[str, Any]] = []

    for row in layer0_rows:
        productive_hits = int(row["productive_hits"])
        rotation_index_count = max(1, int(row["rotation_index_count"]))
        heavy_atom_count = max(1, int(row["heavy_atom_count"]))
        hetero_atom_count = max(0, int(row["hetero_atom_count"]))
        comb = float(row["comb"])
        angle_deg = float(row["angle"])
        ring_count = max(0, int(row["ring_count"]))
        cap_polar_count = max(0, int(row["cap_polar_count"]))

        # LPCS: rotation あたりの productive hit 割合（0〜1）
        lpcs = min(1.0, productive_hits / rotation_index_count)

        # PCF: 分子の極性・ヘテロ成分の寄与割合（0〜1）
        pcf = min(1.0, (hetero_atom_count + cap_polar_count + 1.0) / (heavy_atom_count + 1.0))

        # PAS: Productive Approach Score（kinetics-proxy; LPCS × PCF）
        pas = lpcs * pcf

        # largest_productive_component_share: comb と LPCS の上限
        largest_productive_component_share = max(lpcs, min(1.0, comb))

        # preproductive_contact_fraction = PCF（事前 productive 接触割合）
        preproductive_contact_fraction = pcf

        # rotation_graph_metric: 環 + polar の幾何学的密度
        rotation_graph_metric = (ring_count + cap_polar_count + 1.0) / (heavy_atom_count + 1.0)

        result_rows.append(
            {
                **row,
                "LPCS": float(lpcs),
                "PCF": float(pcf),
                "PAS": float(pas),
                "r_nb_deg": float(angle_deg),
                "largest_productive_component_share": float(largest_productive_component_share),
                "preproductive_contact_fraction": float(preproductive_contact_fraction),
                "rotation_graph_metric": float(rotation_graph_metric),
            }
        )

    return result_rows
