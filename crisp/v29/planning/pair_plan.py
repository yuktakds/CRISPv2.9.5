from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


def _stable_id(*parts: str) -> str:
    return sha256("||".join(parts).encode("utf-8")).hexdigest()[:16]


def select_canonical_caps(caps_rows: list[dict[str, Any]]) -> dict[str, str]:
    by_target: dict[str, list[dict[str, Any]]] = {}
    for row in caps_rows:
        by_target.setdefault(str(row["target_id"]), []).append(row)
    out: dict[str, str] = {}
    for target_id, rows in by_target.items():
        canonical = [r for r in rows if bool(r.get("is_canonical_cap", False))]
        if len(canonical) != 1:
            raise ValueError(f"UNCLEAR_CAP_MULTIPLICITY: target_id={target_id}")
        out[target_id] = str(canonical[0]["cap_id"])
    return out


def build_pair_plan(
    *,
    entries: list[tuple[str, str]],
    target_id: str,
    caps_rows: list[dict[str, Any]],
    shuffle_seed: int,
) -> list[dict[str, Any]]:
    canonical_map = select_canonical_caps(caps_rows)
    native_cap_id = canonical_map[target_id]
    pool = [r for r in caps_rows if str(r["target_id"]) == target_id]
    donors = [r for r in pool if str(r["cap_id"]) != native_cap_id]
    rows: list[dict[str, Any]] = []
    for smiles, molecule_id in entries:
        canonical_link_id = _stable_id(molecule_id, target_id, native_cap_id)
        native_pair_id = _stable_id(molecule_id, target_id, native_cap_id, 'native', '0')
        rows.append(
            {
                'pair_id': native_pair_id,
                'canonical_link_id': canonical_link_id,
                'molecule_id': molecule_id,
                'smiles': smiles,
                'target_id': target_id,
                'cap_id': native_cap_id,
                'native_cap_id': native_cap_id,
                'pairing_role': 'native',
                'shuffle_id': 0,
                'rotation_seed': int(shuffle_seed),
                'shuffle_seed': int(shuffle_seed),
            }
        )
        if donors:
            donor = donors[hash((molecule_id, shuffle_seed)) % len(donors)]
            donor_cap_id = str(donor['cap_id'])
            pair_id = _stable_id(molecule_id, target_id, donor_cap_id, 'matched_falsification', '1')
            rows.append(
                {
                    'pair_id': pair_id,
                    'canonical_link_id': canonical_link_id,
                    'molecule_id': molecule_id,
                    'smiles': smiles,
                    'target_id': target_id,
                    'cap_id': donor_cap_id,
                    'native_cap_id': native_cap_id,
                    'pairing_role': 'matched_falsification',
                    'shuffle_id': 1,
                    'rotation_seed': int(shuffle_seed),
                    'shuffle_seed': int(shuffle_seed),
                }
            )
    return rows
