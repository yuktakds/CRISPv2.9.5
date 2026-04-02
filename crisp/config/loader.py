from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from crisp.config.models import (
    AnchoringConfig,
    AtomSpec,
    SamplingConfig,
    OfftargetConfig,
    PatConfig,
    PdbConfig,
    ScvConfig,
    StagingConfig,
    TargetConfig,
    TranslationConfig,
)

EXPECTED_TOP = {
    "target_name",
    "pathway",
    "pdb",
    "residue_id_format",
    "target_cysteine",
    "anchor_atom_set",
    "offtarget_cysteines",
    "search_radius",
    "distance_threshold",
    "sampling",
    "anchoring",
    "offtarget",
    "scv",
    "staging",
    "translation",
    "pat",
    "random_seed",
}
EXPECTED_PDB = {"path", "model_id", "altloc_policy", "include_hydrogens"}
EXPECTED_ATOM = {"chain", "residue_number", "insertion_code", "atom_name"}
EXPECTED_SAMPLING = {"n_conformers", "n_rotations", "n_translations", "alpha"}
EXPECTED_ANCHORING = {"bond_threshold", "near_threshold", "epsilon"}
EXPECTED_OFFTARGET = {"distance_threshold", "epsilon"}
EXPECTED_SCV = {"confident_fail_threshold", "zero_feasible_abort"}
EXPECTED_STAGING = {
    "retry_distance_lower",
    "retry_distance_upper",
    "far_target_threshold",
    "max_stage",
}
EXPECTED_TRANSLATION = {
    "local_fraction",
    "local_min_radius",
    "local_max_radius",
    "local_start_stage",
}
EXPECTED_PAT = {
    "path_model",
    "goal_mode",
    "grid_spacing",
    "probe_radius",
    "r_outer_margin",
    "blockage_pass_threshold",
    "top_k_poses",
    "goal_shell_clearance",
    "goal_shell_thickness",
    "surface_window_radius",
}


def _require_mapping(name: str, obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise TypeError(f"{name} must be a mapping")
    return obj


def _require_exact_keys(name: str, obj: dict[str, Any], expected: set[str]) -> None:
    actual = set(obj.keys())
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise ValueError(f"{name} keys mismatch; missing={missing}, extra={extra}")


def _atom_from_dict(name: str, obj: dict[str, Any]) -> AtomSpec:
    _require_exact_keys(name, obj, EXPECTED_ATOM)
    return AtomSpec(
        chain=str(obj["chain"]),
        residue_number=int(obj["residue_number"]),
        insertion_code=str(obj["insertion_code"]),
        atom_name=str(obj["atom_name"]),
    )


def load_target_config(path: str | Path) -> TargetConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    raw = _require_mapping("TargetConfig", raw)
    _require_exact_keys("TargetConfig", raw, EXPECTED_TOP)

    pdb = _require_mapping("pdb", raw["pdb"])
    sampling = _require_mapping("sampling", raw["sampling"])
    anchoring = _require_mapping("anchoring", raw["anchoring"])
    offtarget = _require_mapping("offtarget", raw["offtarget"])
    scv = _require_mapping("scv", raw["scv"])
    staging = _require_mapping("staging", raw["staging"])
    translation = _require_mapping("translation", raw["translation"])
    pat = _require_mapping("pat", raw["pat"])

    _require_exact_keys("pdb", pdb, EXPECTED_PDB)
    _require_exact_keys("sampling", sampling, EXPECTED_SAMPLING)
    _require_exact_keys("anchoring", anchoring, EXPECTED_ANCHORING)
    _require_exact_keys("offtarget", offtarget, EXPECTED_OFFTARGET)
    _require_exact_keys("scv", scv, EXPECTED_SCV)
    _require_exact_keys("staging", staging, EXPECTED_STAGING)
    _require_exact_keys("translation", translation, EXPECTED_TRANSLATION)
    _require_exact_keys("pat", pat, EXPECTED_PAT)

    target_cysteine = _atom_from_dict(
        "target_cysteine",
        _require_mapping("target_cysteine", raw["target_cysteine"]),
    )
    anchor_atom_set = [
        _atom_from_dict("anchor_atom_set[]", _require_mapping("anchor_atom_set[]", item))
        for item in raw["anchor_atom_set"]
    ]
    offtarget_cysteines = [
        _atom_from_dict(
            "offtarget_cysteines[]",
            _require_mapping("offtarget_cysteines[]", item),
        )
        for item in raw["offtarget_cysteines"]
    ]

    cfg = TargetConfig(
        target_name=str(raw["target_name"]),
        pathway=str(raw["pathway"]),
        pdb=PdbConfig(
            path=str(pdb["path"]),
            model_id=int(pdb["model_id"]),
            altloc_policy=str(pdb["altloc_policy"]),
            include_hydrogens=bool(pdb["include_hydrogens"]),
        ),
        residue_id_format=str(raw["residue_id_format"]),
        target_cysteine=target_cysteine,
        anchor_atom_set=anchor_atom_set,
        offtarget_cysteines=offtarget_cysteines,
        search_radius=float(raw["search_radius"]),
        distance_threshold=float(raw["distance_threshold"]),
        sampling=SamplingConfig(
            n_conformers=int(sampling["n_conformers"]),
            n_rotations=int(sampling["n_rotations"]),
            n_translations=int(sampling["n_translations"]),
            alpha=float(sampling["alpha"]),
        ),
        anchoring=AnchoringConfig(
            bond_threshold=float(anchoring["bond_threshold"]),
            near_threshold=float(anchoring["near_threshold"]),
            epsilon=float(anchoring["epsilon"]),
        ),
        offtarget=OfftargetConfig(
            distance_threshold=float(offtarget["distance_threshold"]),
            epsilon=float(offtarget["epsilon"]),
        ),
        scv=ScvConfig(
            confident_fail_threshold=int(
                scv["confident_fail_threshold"]
            ),
            zero_feasible_abort=int(scv["zero_feasible_abort"]),
        ),
        staging=StagingConfig(
            retry_distance_lower=float(staging["retry_distance_lower"]),
            retry_distance_upper=float(staging["retry_distance_upper"]),
            far_target_threshold=float(
                staging["far_target_threshold"]
            ),
            max_stage=int(staging["max_stage"]),
        ),
        translation=TranslationConfig(
            local_fraction=float(translation["local_fraction"]),
            local_min_radius=float(translation["local_min_radius"]),
            local_max_radius=float(translation["local_max_radius"]),
            local_start_stage=int(
                translation["local_start_stage"]
            ),
        ),
        pat=PatConfig(
            path_model=str(pat["path_model"]),
            goal_mode=str(pat["goal_mode"]),
            grid_spacing=float(pat["grid_spacing"]),
            probe_radius=float(pat["probe_radius"]),
            r_outer_margin=float(pat["r_outer_margin"]),
            blockage_pass_threshold=float(pat["blockage_pass_threshold"]),
            top_k_poses=int(pat["top_k_poses"]),
            goal_shell_clearance=float(pat["goal_shell_clearance"]),
            goal_shell_thickness=float(pat["goal_shell_thickness"]),
            surface_window_radius=float(pat["surface_window_radius"]),
        ),
        random_seed=int(raw["random_seed"]),
    )
    cfg.validate()
    return cfg
