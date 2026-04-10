from __future__ import annotations

from crisp.v29.inputs import load_molecule_rows
from tests.v29_smoke_helpers import (
    create_minimal_full_mode_fixture_bundle,
    row_count,
)


def test_minimal_cap_and_assay_fixtures_are_ci_sized(tmp_path) -> None:
    bundle = create_minimal_full_mode_fixture_bundle(tmp_path)

    assert len(load_molecule_rows(bundle["library_path"])) == 2
    assert row_count(bundle["caps_path"]) == 2
    assert row_count(bundle["assays_path"]) == 2
