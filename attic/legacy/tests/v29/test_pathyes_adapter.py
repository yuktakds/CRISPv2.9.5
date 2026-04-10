from __future__ import annotations

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
from crisp.v29.pathyes import pathyes_bootstrap_state


def make_config() -> TargetConfig:
    return TargetConfig(
        target_name="t",
        config_role="smoke",
        expected_use="Pipeline health-check regime for end-to-end completion on real data.",
        allowed_comparisons=["cross-regime"],
        frozen_for_regression=False,
        pathway="covalent",
        pdb=PdbConfig(path="x.cif", model_id=1, altloc_policy="first", include_hydrogens=False),
        residue_id_format="auth",
        target_cysteine=AtomSpec(chain="A", residue_number=1, insertion_code="", atom_name="SG"),
        anchor_atom_set=[AtomSpec(chain="A", residue_number=1, insertion_code="", atom_name="SG")],
        offtarget_cysteines=[],
        search_radius=5.0,
        distance_threshold=2.2,
        sampling=SamplingConfig(n_conformers=1, n_rotations=1, n_translations=1, alpha=0.8),
        anchoring=AnchoringConfig(bond_threshold=2.2, near_threshold=3.5, epsilon=0.1),
        offtarget=OfftargetConfig(distance_threshold=5.0, epsilon=0.1),
        scv=ScvConfig(confident_fail_threshold=1, zero_feasible_abort=4096),
        staging=StagingConfig(retry_distance_lower=2.2, retry_distance_upper=3.5, far_target_threshold=6.0, max_stage=2),
        translation=TranslationConfig(local_fraction=0.5, local_min_radius=0.5, local_max_radius=1.5, local_start_stage=2),
        pat=PatConfig(path_model="TUNNEL", goal_mode="anchor", grid_spacing=0.5, probe_radius=1.4, r_outer_margin=1.0, blockage_pass_threshold=0.5, top_k_poses=5, goal_shell_clearance=0.5, goal_shell_thickness=1.0, surface_window_radius=2.0),
        random_seed=42,
    )


def test_bootstrap_pathyes_never_infers_goal_precheck() -> None:
    state = pathyes_bootstrap_state(config=make_config(), pathyes_force_false=True)
    assert state.goal_precheck_passed is None
    assert state.rule1_applicability == "PATH_NOT_EVALUABLE"
    assert state.skip_code == "SKIP_PATHYES_BOOTSTRAP"
