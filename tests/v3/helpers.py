from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crisp.config.models import (
    AnchoringConfig,
    AtomSpec,
    OfftargetConfig,
    PatConfig,
    PdbConfig,
    SamplingConfig,
    ScvConfig,
    StagingConfig,
    TargetConfig,
    TranslationConfig,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def make_config(*, path_model: str = "TUNNEL", blockage_pass_threshold: float = 0.5) -> TargetConfig:
    return TargetConfig(
        target_name="tgt",
        config_role="smoke",
        expected_use="Pipeline health-check regime for end-to-end completion on real data.",
        allowed_comparisons=["cross-regime"],
        frozen_for_regression=False,
        pathway="covalent",
        pdb=PdbConfig(path="s.cif", model_id=1, altloc_policy="first", include_hydrogens=False),
        residue_id_format="auth",
        target_cysteine=AtomSpec(chain="A", residue_number=1, insertion_code="", atom_name="SG"),
        anchor_atom_set=[AtomSpec(chain="A", residue_number=1, insertion_code="", atom_name="SG")],
        offtarget_cysteines=[],
        search_radius=6.0,
        distance_threshold=2.2,
        sampling=SamplingConfig(n_conformers=1, n_rotations=1, n_translations=1, alpha=0.5),
        anchoring=AnchoringConfig(bond_threshold=2.2, near_threshold=3.5, epsilon=0.1),
        offtarget=OfftargetConfig(distance_threshold=2.2, epsilon=0.1),
        scv=ScvConfig(confident_fail_threshold=1, zero_feasible_abort=4096),
        staging=StagingConfig(
            retry_distance_lower=2.2,
            retry_distance_upper=3.5,
            far_target_threshold=6.0,
            max_stage=2,
        ),
        translation=TranslationConfig(
            local_fraction=0.5,
            local_min_radius=1.0,
            local_max_radius=2.0,
            local_start_stage=2,
        ),
        pat=PatConfig(
            path_model=path_model,
            goal_mode="shell",
            grid_spacing=0.5,
            probe_radius=1.4,
            r_outer_margin=2.0,
            blockage_pass_threshold=blockage_pass_threshold,
            top_k_poses=4,
            goal_shell_clearance=0.2,
            goal_shell_thickness=1.0,
            surface_window_radius=4.0,
        ),
        random_seed=42,
    )


def write_pat_payload(path: str | Path, payload: dict[str, Any]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return out


def load_pat_fixture(name: str) -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / name
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def write_pat_fixture(path: str | Path, name: str) -> Path:
    return write_pat_payload(path, load_pat_fixture(name))
