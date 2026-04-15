from __future__ import annotations

from rdkit import Chem

from crisp.models.runtime import WarheadMatch

WARHEAD_SMARTS: tuple[str, ...] = (
    "[C:1]=[C][C](=O)",
    "[C:1]=[C][S](=O)(=O)",
    "[C:1]=[C]C#N",
    "C(=O)[CH2:1][Cl,Br,I]",
    "C(=O)[CH:1]([Cl,Br,I])",
    "[N]=[C:1]=[S]",
    "[C:1]1[C:1]O1",
    "[C:1]1[C][N]1[C](=O)",
)


def compile_warheads() -> tuple[tuple[str, Chem.Mol, tuple[int, ...]], ...]:
    compiled: list[tuple[str, Chem.Mol, tuple[int, ...]]] = []
    for pattern in WARHEAD_SMARTS:
        query = Chem.MolFromSmarts(pattern)
        if query is None:
            raise ValueError(f"Invalid SMARTS: {pattern}")
        mapped_query_indices = tuple(
            sorted(a.GetIdx() for a in query.GetAtoms() if a.GetAtomMapNum() == 1)
        )
        if not mapped_query_indices:
            raise ValueError(f"SMARTS must contain at least one :1 mapped atom: {pattern}")
        compiled.append((pattern, query, mapped_query_indices))
    return tuple(compiled)


COMPILED_WARHEADS = compile_warheads()


def match_warheads(mol: Chem.Mol) -> tuple[tuple[WarheadMatch, ...], tuple[int, ...]]:
    matches: list[WarheadMatch] = []
    union: set[int] = set()
    for smarts_index, (pattern, query, mapped_query_indices) in enumerate(COMPILED_WARHEADS):
        for match in mol.GetSubstructMatches(query, uniquify=True):
            mapped_atoms = tuple(sorted({match[i] for i in mapped_query_indices}))
            matches.append(
                WarheadMatch(
                    smarts_index=smarts_index,
                    pattern=pattern,
                    mapped_atoms=mapped_atoms,
                )
            )
            union.update(mapped_atoms)
    matches.sort(key=lambda m: (m.smarts_index, m.mapped_atoms))
    return tuple(matches), tuple(sorted(union))
