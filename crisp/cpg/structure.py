"""蛋白質構造の読み込みと幾何情報の構築。

§5.3 ActiveSiteAnchor 導出ルール:
  covalent:    target_cysteine 指定原子の座標
  noncovalent: centroid(anchor_atom_set の全原子座標)

蛋白質構造は 1 run につき 1 回だけ parse し、以降はキャッシュする (PERF-01)。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from Bio.PDB import MMCIFParser, PDBParser

from crisp.config.models import AtomSpec, TargetConfig
from crisp.models.runtime import AnchorSourceAtom, ProteinAtom, ProteinGeometry

# Bondi vdW 半径テーブル (§7.3 C1 制約で使用)
BONDI_VDW: dict[str, float] = {
    "H": 1.20, "C": 1.70, "N": 1.55, "O": 1.52, "F": 1.47,
    "P": 1.80, "S": 1.80, "CL": 1.75, "BR": 1.85, "I": 1.98,
}
DEFAULT_VDW: float = 1.70


def _load_structure(path: Path):
    """CIF / PDB ファイルを Biopython で parse する。"""
    parser = MMCIFParser(QUIET=True) if path.suffix.lower() == ".cif" else PDBParser(QUIET=True)
    return parser.get_structure("target", str(path))


def _normalize_atom_name(atom_name: str) -> str:
    return atom_name.strip().upper()


def _match_residue(residue, spec: AtomSpec) -> bool:
    hetflag, resseq, icode = residue.id
    return (
        hetflag == " "
        and residue.get_parent().id == spec.chain
        and int(resseq) == int(spec.residue_number)
        and (icode.strip() if isinstance(icode, str) else "") == spec.insertion_code
    )


def _find_atom(model, spec: AtomSpec, altloc_policy: str):
    """指定 AtomSpec に該当する Biopython Atom を返す。"""
    for chain in model:
        if chain.id != spec.chain:
            continue
        for residue in chain:
            if not _match_residue(residue, spec):
                continue
            for atom in residue:
                if _normalize_atom_name(atom.get_name()) != _normalize_atom_name(spec.atom_name):
                    continue
                altloc = (atom.get_altloc() or "").strip()
                if altloc_policy == "A" and altloc not in ("", "A"):
                    continue
                if altloc_policy and altloc_policy != "A" and altloc not in ("", altloc_policy):
                    continue
                return atom
    raise KeyError(f"Atom not found: {spec.chain}:{spec.residue_number}:{spec.atom_name}")


def _protein_atom_from_biopy(atom, residue) -> ProteinAtom:
    element = (atom.element or atom.get_name()[0]).strip().upper()
    return ProteinAtom(
        serial=int(atom.serial_number),
        chain=str(residue.get_parent().id),
        residue_number=int(residue.id[1]),
        insertion_code=(residue.id[2].strip() if isinstance(residue.id[2], str) else ""),
        residue_name=str(residue.resname).strip(),
        atom_name=str(atom.get_name()).strip(),
        element=element,
        xyz=np.asarray(atom.coord, dtype=np.float64),
        vdw_radius=float(BONDI_VDW.get(element, DEFAULT_VDW)),
    )


def _derive_active_site_anchor(
    model, config: TargetConfig
) -> tuple[np.ndarray, str, tuple[AnchorSourceAtom, ...]]:
    """§5.3: pathway に応じた ActiveSiteAnchor の導出 (DEV-01 修正)。"""
    if config.pathway == "covalent":
        # covalent: target_cysteine 指定原子の座標
        target_atom = _find_atom(model, config.target_cysteine, config.pdb.altloc_policy)
        xyz = np.asarray(target_atom.coord, dtype=np.float64)
        source = AnchorSourceAtom(
            atom=f"{config.target_cysteine.chain}:{config.target_cysteine.residue_number}:{config.target_cysteine.atom_name}",
            xyz=(float(xyz[0]), float(xyz[1]), float(xyz[2])),
        )
        return xyz, "target_cysteine.SG", (source,)

    # noncovalent: centroid(anchor_atom_set の全原子座標) — §5.3
    coords_list: list[np.ndarray] = []
    sources: list[AnchorSourceAtom] = []
    for spec in config.anchor_atom_set:
        atom = _find_atom(model, spec, config.pdb.altloc_policy)
        xyz = np.asarray(atom.coord, dtype=np.float64)
        coords_list.append(xyz)
        sources.append(AnchorSourceAtom(
            atom=f"{spec.chain}:{spec.residue_number}:{spec.atom_name}",
            xyz=(float(xyz[0]), float(xyz[1]), float(xyz[2])),
        ))
    # 均等重み算術平均
    centroid = np.mean(np.array(coords_list, dtype=np.float64), axis=0)
    return centroid, "anchor_atom_set.centroid", tuple(sources)


def check_target_residue_exists(repo_root: Path, config: TargetConfig) -> None:
    """MEF-06 用: 対象残基の存在のみを軽量に検証する (DEV-04 修正)。

    蛋白質の全原子を読まず、対象残基の原子だけを探す。
    """
    structure_path = config.resolve_structure_path(repo_root)
    structure = _load_structure(structure_path)
    models = list(structure.get_models())
    if config.pdb.model_id >= len(models):
        raise IndexError(f"model_id {config.pdb.model_id} out of range for {structure_path}")
    model = models[config.pdb.model_id]
    # target_cysteine の存在確認
    _find_atom(model, config.target_cysteine, config.pdb.altloc_policy)
    # offtarget_cysteines の存在確認
    for spec in config.offtarget_cysteines:
        _find_atom(model, spec, config.pdb.altloc_policy)


def load_protein_geometry(repo_root: Path, config: TargetConfig) -> ProteinGeometry:
    """蛋白質幾何情報を構築する。1 run につき 1 回だけ呼ぶ想定 (PERF-01)。"""
    structure_path = config.resolve_structure_path(repo_root)
    structure = _load_structure(structure_path)
    models = list(structure.get_models())
    if config.pdb.model_id >= len(models):
        raise IndexError(f"model_id {config.pdb.model_id} out of range for {structure_path}")
    model = models[config.pdb.model_id]

    # §5.3: ActiveSiteAnchor 導出 (DEV-01)
    anchor_xyz, derivation, anchor_sources = _derive_active_site_anchor(model, config)

    # target atom 座標 (Sensor 計算用)
    target_atom = _find_atom(model, config.target_cysteine, config.pdb.altloc_policy)
    target_xyz = np.asarray(target_atom.coord, dtype=np.float64)

    # offtarget 座標
    offtarget_atoms: list[tuple[str, np.ndarray]] = []
    for spec in config.offtarget_cysteines:
        atom = _find_atom(model, spec, config.pdb.altloc_policy)
        label = f"{spec.chain}:{spec.residue_number}:{spec.atom_name}"
        offtarget_atoms.append((label, np.asarray(atom.coord, dtype=np.float64)))

    # 蛋白質重原子 (水素除外、altloc フィルタ済み)
    protein_heavy_atoms: list[ProteinAtom] = []
    for chain in model:
        for residue in chain:
            if residue.id[0] != " ":
                continue
            for atom in residue:
                element = (atom.element or atom.get_name()[0]).strip().upper()
                if element == "H":
                    continue
                altloc = (atom.get_altloc() or "").strip()
                if config.pdb.altloc_policy == "A" and altloc not in ("", "A"):
                    continue
                protein_heavy_atoms.append(_protein_atom_from_biopy(atom, residue))

    return ProteinGeometry(
        active_site_anchor_xyz=anchor_xyz,
        anchor_derivation=derivation,
        anchor_source_atoms=anchor_sources,
        protein_heavy_atoms=tuple(protein_heavy_atoms),
        target_atom_xyz=target_xyz,
        offtarget_atoms=tuple(offtarget_atoms),
    )
