"""MEF: 分子適格性フィルタ (§6)。

責務: 入力妥当性・探索空間有限性の保証。座標系依存の判定は行わない (§4.1)。
改修:
  DEV-04: PDB 残基存在チェック (MEF-06) を軽量化。
          全蛋白質原子の load を回避し、対象残基の存在のみを確認する。
"""
from __future__ import annotations

from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from crisp.config.models import TargetConfig
from crisp.cpg.structure import check_target_residue_exists
from crisp.mef.warheads import match_warheads
from crisp.models.runtime import MefResult


def run_mef(
    smiles: str,
    config: TargetConfig,
    repo_root: Path,
    *,
    skip_pdb_check: bool = False,
) -> MefResult:
    """§6.1: MEF 判定基準に従い化合物を検査する。

    skip_pdb_check=True: library 実行時に MEF-06 を初回のみ検証し、
    以降の化合物ではスキップする (PERF-01 最適化)。
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return MefResult(False, "FAIL_PARSE", smiles, None, None)

    heavy_atom_count = int(rdMolDescriptors.CalcNumHeavyAtoms(mol))
    rotatable_bonds = int(rdMolDescriptors.CalcNumRotatableBonds(mol))

    # MEF-02: 重原子数範囲チェック
    if heavy_atom_count < 5:
        return MefResult(False, "FAIL_TOO_SMALL", smiles, heavy_atom_count, rotatable_bonds)
    if heavy_atom_count > 80:
        return MefResult(False, "FAIL_TOO_LARGE", smiles, heavy_atom_count, rotatable_bonds)

    # MEF-03: 回転可能結合数チェック
    if rotatable_bonds > 10:
        return MefResult(False, "FAIL_TOO_FLEXIBLE", smiles, heavy_atom_count, rotatable_bonds)

    # MEF-04: ワーヘッド存在チェック (covalent のみ)
    matched_smarts: tuple = ()
    warhead_atoms_union: tuple = ()
    if config.pathway == "covalent":
        matched_smarts, warhead_atoms_union = match_warheads(mol)
        if not warhead_atoms_union:
            return MefResult(
                False, "FAIL_NO_WARHEAD", smiles, heavy_atom_count, rotatable_bonds,
                matched_smarts=matched_smarts, warhead_atoms_union=warhead_atoms_union,
            )

    # MEF-06: PDB 残基存在チェック (DEV-04 改修: 軽量化)
    if not skip_pdb_check:
        try:
            check_target_residue_exists(repo_root, config)
        except Exception as exc:
            raise RuntimeError(f"MEF-06: PDB/CIF target residue check failed: {exc}") from exc

    return MefResult(
        True, None, smiles, heavy_atom_count, rotatable_bonds,
        matched_smarts=matched_smarts, warhead_atoms_union=warhead_atoms_union,
    )
