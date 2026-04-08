from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.channels.cap import CapEvidenceChannel


def test_cap_scaffold_preserves_existing_rc2_outputs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest_path = run_dir / "run_manifest.json"
    inventory_path = run_dir / "output_inventory.json"
    manifest_path.write_text(json.dumps({"run_id": "run"}), encoding="utf-8")
    inventory_path.write_text(json.dumps({"generated_outputs": ["run_manifest.json"]}), encoding="utf-8")
    before = {
        manifest_path.name: manifest_path.read_bytes(),
        inventory_path.name: inventory_path.read_bytes(),
    }

    result = CapEvidenceChannel().evaluate(
        pair_features_rows=[
            {"canonical_link_id": "a", "molecule_id": "n1", "cap_id": "c1", "pairing_role": "native", "comb": 0.82, "PAS": 0.75},
            {"canonical_link_id": "a", "molecule_id": "n2", "cap_id": "c2", "pairing_role": "native", "comb": 0.80, "PAS": 0.72},
            {"canonical_link_id": "a", "molecule_id": "n3", "cap_id": "c3", "pairing_role": "native", "comb": 0.78, "PAS": 0.70},
            {"canonical_link_id": "a", "molecule_id": "f1", "cap_id": "c4", "pairing_role": "matched_falsification", "comb": 0.22, "PAS": 0.18},
        ],
        source=tmp_path / "pair_features.json",
    )

    after = {
        manifest_path.name: manifest_path.read_bytes(),
        inventory_path.name: inventory_path.read_bytes(),
    }
    assert result.evidence is not None
    assert result.applicability_records == []
    assert before == after
