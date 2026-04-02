from __future__ import annotations

from crisp.v29.cap import run_layer0, run_layer1
from crisp.v29.planning import build_pair_plan


def test_cap_layer0_layer1_generate_expected_columns() -> None:
    entries = [('c1ccccc1O', 'mol1')]
    caps_rows = [
        {'cap_id': 'cap_native', 'target_id': 'T', 'axis_x': 1.0, 'axis_y': 0.0, 'axis_z': 0.0, 'polar_coords_json': '[]', 'motion_class': 'm', 'source_db': 'x', 'source_entry_id': '1', 'derivation_method': 'd', 'is_canonical_cap': True},
        {'cap_id': 'cap_donor', 'target_id': 'T', 'axis_x': 0.0, 'axis_y': 1.0, 'axis_z': 0.0, 'polar_coords_json': '[1,2]', 'motion_class': 'm', 'source_db': 'x', 'source_entry_id': '2', 'derivation_method': 'd', 'is_canonical_cap': False},
    ]
    pair_plan = build_pair_plan(entries=entries, target_id='T', caps_rows=caps_rows, shuffle_seed=42)
    l0 = run_layer0(pair_plan, caps_rows, n_rotations=64)
    l1 = run_layer1(l0)
    assert len(l1) == 2
    assert 'P_hit' in l1[0]
    assert 'PAS' in l1[0]
    assert 'rotation_graph_metric' in l1[0]
