from __future__ import annotations

from typing import Any


def build_candidate_sources(*, warhead_atoms_union: list[int] | tuple[int, ...], struct_conn_atoms: list[int] | None = None, near_band_atoms: list[int] | None = None) -> list[dict[str, Any]]:
    struct_conn_atoms = [] if struct_conn_atoms is None else list(struct_conn_atoms)
    near_band_atoms = [] if near_band_atoms is None else list(near_band_atoms)
    warhead_atoms_union = list(warhead_atoms_union)
    rows: list[dict[str, Any]] = []
    for atom in warhead_atoms_union:
        source = 'smarts_union'
        if atom in struct_conn_atoms:
            source = 'struct_conn'
        elif atom in near_band_atoms:
            source = 'near_band'
        rows.append({'atom_index': int(atom), 'source': source})
    return rows
