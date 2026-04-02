"""Rule1: 最小剛直体積ルール（Path-Yes domain 限定）。

設計書 §4A-2, §B3, V29-I02, V29-I05 に準拠。

FAIL-1 修正 (境界分離):
  旧実装では Sensor 測定コードと SCV 判定コードが
  compute_rule1_assessment という単一関数に混在していた。
  本修正で Rule1RigiditySensor（測定のみ）と Rule1SCV（判定のみ）を
  明示的に分離し、Rule1Assessment はその合成結果として返す。

  pat-backed mode 移行時の再監査注意事項:
    bootstrap mode では rule1_applicability = PATH_NOT_EVALUABLE のため
    rule1_verdict = None（公開判定なし）。
    pat-backed mode に切り替えた後、Rule1Assessment の verdict が
    Core/Cap verdict と交差しないかを再監査すること（V29-I02 の境界確認）。

禁止:
  - Rule1 を MEF hard filter として使う（V29-I05）
  - PATH_NOT_EVALUABLE 時に verdict を公開する
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import Lipinski

from crisp.config.models import TargetConfig
from crisp.v29.contracts import PathYesState, Rule1Assessment, TableWriteResult
from crisp.v29.pathyes import resolve_pathyes_state
from crisp.v29.tableio import read_records_table, write_records_table

_log = logging.getLogger(__name__)

DEFAULT_THETA_RULE1: float = 1.0


# ---------------------------------------------------------------------------
# theta_rule1 ローダー
# ---------------------------------------------------------------------------

def load_theta_rule1_table(path: str | Path | None) -> tuple[dict[str, float], str]:
    """theta_rule1 の calibration テーブルを読み込む。

    Returns:
        (lookup_table, table_id) のタプル。
        path が None の場合は空テーブルと 'builtin:none' を返す。
    """
    if path is None:
        return {}, "builtin:none"

    p = Path(path)
    if p.suffix.lower() == ".json":
        import json
        payload = json.loads(p.read_text(encoding="utf-8"))
        table = {str(k): float(v) for k, v in payload.items()}
        return table, f"json:{p.resolve()}"

    rows = read_records_table(p)
    table: dict[str, float] = {}
    for row in rows:
        key = str(
            row.get("target_family")
            or row.get("target_name")
            or row.get("theta_rule1_table_id")
            or "default"
        )
        table[key] = float(row["theta_rule1"])
    return table, f"table:{p.resolve()}"


def resolve_theta_rule1(theta_table: dict[str, float], *, config: TargetConfig) -> float:
    """config から theta_rule1 を解決する。優先順: target_name > pathway > default。"""
    for key in (config.target_name, config.pathway, "default"):
        if key and key in theta_table:
            return float(theta_table[key])
    return DEFAULT_THETA_RULE1


# ---------------------------------------------------------------------------
# Rule1RigiditySensor: 観測量の計算のみ（V29-I01 準拠）
# ---------------------------------------------------------------------------

class Rule1RigiditySensor:
    """Rule1 のために必要な観測量（剛直性指標）を分子から計算する。

    FAIL-1 修正:
    旧実装では観測量と SCV 判定が compute_rule1_assessment で混在していた。
    本クラスは観測量の計算のみを担う（V29-I01: Sensor は観測量だけを返す）。
    PASS/FAIL/UNCLEAR の判定は Rule1SCV が行う（V29-I02）。
    """

    @staticmethod
    def ring_lock_present(mol: Chem.Mol) -> bool:
        """縮合環（2つ以上の原子を共有する環）の存在を検出する。"""
        rings = [set(r) for r in mol.GetRingInfo().AtomRings()]
        for i in range(len(rings)):
            for j in range(i + 1, len(rings)):
                if len(rings[i] & rings[j]) >= 1:
                    return True
        return False

    @staticmethod
    def largest_rigid_block_heavy_atom_count(mol: Chem.Mol) -> int:
        """回転可能結合で分割した最大剛直ブロックの重原子数を返す。"""
        heavy_atom_indices = {a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() > 1}
        if not heavy_atom_indices:
            return 0

        rotatable_bond_indices: set[int] = set()
        for bond in mol.GetBonds():
            if (
                bond.GetBondTypeAsDouble() == 1.0
                and not bond.IsInRing()
                and bond.GetBeginAtom().GetAtomicNum() > 1
                and bond.GetEndAtom().GetAtomicNum() > 1
            ):
                rotatable_bond_indices.add(bond.GetIdx())

        # 隣接リスト（回転可能結合を除く）
        adjacency: dict[int, set[int]] = {idx: set() for idx in heavy_atom_indices}
        for bond in mol.GetBonds():
            if bond.GetIdx() in rotatable_bond_indices:
                continue
            a1, a2 = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            if a1 in heavy_atom_indices and a2 in heavy_atom_indices:
                adjacency[a1].add(a2)
                adjacency[a2].add(a1)

        # 連結成分の最大サイズを BFS/DFS で求める
        visited: set[int] = set()
        max_component_size = 0
        for start in adjacency:
            if start in visited:
                continue
            stack = [start]
            component_size = 0
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                component_size += 1
                stack.extend(adjacency[node] - visited)
            max_component_size = max(max_component_size, component_size)

        return max_component_size

    @classmethod
    def measure(
        cls,
        smiles: str,
    ) -> tuple[int, int, float, bool, bool, bool, float]:
        """分子から観測量を計算して返す。

        Returns:
            (rotatable_bonds, largest_rigid_block_heavy_atoms,
             rigid_fraction, ring_lock_present,
             shape_proxy_evaluable, within_calibration_domain,
             rigid_volume_proxy)
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return 0, 0, 0.0, False, False, False, 0.0

        rotatable_bonds = int(Lipinski.NumRotatableBonds(mol))
        heavy_atom_count = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)
        largest_rigid = cls.largest_rigid_block_heavy_atom_count(mol)
        ring_lock = cls.ring_lock_present(mol)
        shape_proxy_evaluable = heavy_atom_count > 0
        within_calibration_domain = heavy_atom_count > 0
        rigid_fraction = float(largest_rigid) / float(heavy_atom_count) if heavy_atom_count else 0.0
        rigid_volume_proxy = float(largest_rigid) / float(1 + rotatable_bonds)

        return (
            rotatable_bonds,
            largest_rigid,
            rigid_fraction,
            ring_lock,
            shape_proxy_evaluable,
            within_calibration_domain,
            rigid_volume_proxy,
        )


# ---------------------------------------------------------------------------
# Rule1SCV: 判定のみ（V29-I02 準拠）
# ---------------------------------------------------------------------------

class Rule1SCV:
    """Rule1RigiditySensor の観測量から verdict と reason_code を決定する。

    V29-I02: SCV 以外は PASS/FAIL/UNCLEAR と理由コードを返さない。
    本クラスがその唯一の担当である。

    FAIL-1 修正:
    旧実装では _rule1_scv という非公開関数が rule1.py 内に存在し、
    Sensor 測定コードと同一ファイルに混在していた。
    本クラスはその責務を明示的に引き受ける。

    再監査注意事項 (pat-backed mode 移行時):
    - rule1_applicability = PATH_NOT_EVALUABLE の場合は (None, None) を返す。
    - pat-backed mode で PATH_EVALUABLE になった場合、verdict が有効になる。
      その時点で Core/Cap verdict との交差を確認する必要がある（V29-I02）。
    """

    @staticmethod
    def decide(
        *,
        ring_lock_present: bool,
        shape_proxy_evaluable: bool,
        within_calibration_domain: bool,
        rigid_volume_proxy: float,
        theta_rule1: float,
        pathyes_state: PathYesState,
    ) -> tuple[str | None, str | None]:
        """(verdict, reason_code) のタプルを返す。

        PATH_NOT_EVALUABLE の場合は (None, None) を返す（公開判定なし）。
        """
        if pathyes_state.rule1_applicability != "PATH_EVALUABLE":
            # bootstrap mode では常にここに入る
            _log.debug(
                "Rule1SCV.decide: suppressed (rule1_applicability=%s, skip_code=%s)",
                pathyes_state.rule1_applicability,
                pathyes_state.skip_code,
            )
            return None, None

        if not ring_lock_present:
            return "FAIL", "FAIL_R1_NO_RING_LOCK"
        if not shape_proxy_evaluable:
            return "UNCLEAR", "UNCLEAR_R1_NOT_EVALUABLE"
        if not within_calibration_domain:
            return "UNCLEAR", "UNCLEAR_R1_OUT_OF_DOMAIN"
        if rigid_volume_proxy >= float(theta_rule1):
            return "PASS", None
        return "FAIL", "FAIL_R1_TOO_FLEXIBLE"


# ---------------------------------------------------------------------------
# 公開 API: compute_rule1_assessment
# ---------------------------------------------------------------------------

def compute_rule1_assessment(
    *,
    molecule_id: str,
    smiles: str,
    pathyes_state: PathYesState,
    theta_rule1: float = DEFAULT_THETA_RULE1,
    run_id: str | None = None,
) -> Rule1Assessment:
    """分子 1 件の Rule1Assessment を計算して返す。

    Rule1RigiditySensor（観測量）と Rule1SCV（判定）を組み合わせた
    公開エントリーポイント。FAIL-1 修正により責務境界が明示されている。
    """
    (
        rotatable_bonds,
        largest_rigid_heavy,
        rigid_fraction,
        ring_lock,
        shape_proxy_evaluable,
        within_calibration_domain,
        rigid_volume_proxy,
    ) = Rule1RigiditySensor.measure(smiles)

    verdict, reason = Rule1SCV.decide(
        ring_lock_present=ring_lock,
        shape_proxy_evaluable=shape_proxy_evaluable,
        within_calibration_domain=within_calibration_domain,
        rigid_volume_proxy=rigid_volume_proxy,
        theta_rule1=theta_rule1,
        pathyes_state=pathyes_state,
    )

    return Rule1Assessment(
        run_id=run_id,
        molecule_id=molecule_id,
        smiles=smiles,
        rotatable_bonds=rotatable_bonds,
        largest_rigid_block_heavy_atoms=largest_rigid_heavy,
        rigid_fraction=rigid_fraction,
        ring_lock_present=ring_lock,
        shape_proxy_evaluable=shape_proxy_evaluable,
        within_calibration_domain=within_calibration_domain,
        rigid_volume_proxy=rigid_volume_proxy,
        rule1_applicability=pathyes_state.rule1_applicability,
        pathyes_state_json=asdict(pathyes_state),
        theta_rule1=theta_rule1,
        rule1_verdict=verdict,
        rule1_reason_code=reason,
    )


# ---------------------------------------------------------------------------
# バッチ実行
# ---------------------------------------------------------------------------

def run_rule1_assessments(
    *,
    entries: list[tuple[str, str]],
    config: TargetConfig,
    out_path: str | Path,
    theta_rule1: float,
    pathyes_mode: str = "bootstrap",
    pat_diagnostics_path: str | Path | None = None,
    pathyes_force_false: bool = False,
    run_id: str | None = None,
) -> tuple[TableWriteResult, dict[str, Any]]:
    """entries の全分子に対して Rule1Assessment を計算し、テーブルに書き出す。

    Returns:
        (TableWriteResult, diagnostics_dict) のタプル。
    """
    pathyes_state = resolve_pathyes_state(
        config=config,
        mode="bootstrap" if pathyes_mode == "bootstrap" else "pat-backed",
        pat_diagnostics_path=pat_diagnostics_path,
        pathyes_force_false=pathyes_force_false,
    )

    _log.info(
        "run_rule1_assessments: %d entries, mode=%s, applicability=%s, skip_code=%s",
        len(entries), pathyes_mode,
        pathyes_state.rule1_applicability, pathyes_state.skip_code,
    )

    rows: list[dict[str, Any]] = []
    for smiles, molecule_id in entries:
        assessment = compute_rule1_assessment(
            molecule_id=molecule_id,
            smiles=smiles,
            pathyes_state=pathyes_state,
            theta_rule1=theta_rule1,
            run_id=run_id,
        )
        rows.append(asdict(assessment))

    table = write_records_table(out_path, rows)

    diagnostics: dict[str, Any] = {
        "mode": pathyes_mode,
        "row_count": len(rows),
        "rule1_applicability": pathyes_state.rule1_applicability,
        "skip_code": pathyes_state.skip_code,
        "pat_run_diagnostics_json": pathyes_state.pat_run_diagnostics_json,
        "theta_rule1": theta_rule1,
        "published_verdicts": pathyes_state.rule1_applicability == "PATH_EVALUABLE",
    }

    _log.info(
        "run_rule1_assessments complete: %d rows written to %s, published=%s",
        len(rows), table.path, diagnostics["published_verdicts"],
    )

    return table, diagnostics


def run_rule1_bootstrap_assessments(**kwargs: Any) -> tuple[TableWriteResult, dict[str, Any]]:
    """bootstrap mode でのバッチ実行ショートカット。"""
    return run_rule1_assessments(
        pathyes_mode="bootstrap", theta_rule1=DEFAULT_THETA_RULE1, **kwargs
    )
