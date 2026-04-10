from __future__ import annotations

from crisp.v29.cap import build_falsification_table


def test_falsification_table_contains_matched_only() -> None:
    pair_rows = [
        {'canonical_link_id': 'c1', 'molecule_id': 'm1', 'target_id': 'T', 'pairing_role': 'native', 'comb': 0.8, 'P_hit': 0.7, 'PAS': 0.6, 'dist': 1.0, 'LPCS': 0.5, 'PCF': 0.4},
        {'canonical_link_id': 'c1', 'molecule_id': 'm1', 'target_id': 'T', 'pairing_role': 'matched_falsification', 'comb': 0.2, 'P_hit': 0.1, 'PAS': 0.1, 'dist': 2.0, 'LPCS': 0.1, 'PCF': 0.1},
    ]
    assays = [{'canonical_link_id': 'c1', 'molecule_id': 'm1', 'target_id': 'T', 'condition_hash': 'h1', 'functional_score_raw': 80.0, 'assay_type': 'activity', 'direction': 'higher_is_better', 'unit': '%'}]
    fals = build_falsification_table(pair_rows, assays, donor_plan={'shuffle_donor_pool_hash': 'd1', 'donor_plan_hash': 'd2'})
    assert len(fals) == 1
    assert fals[0]['pairing_role'] == 'matched_falsification'
