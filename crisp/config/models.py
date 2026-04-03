from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SUPPORTED_PATHWAYS = {"covalent", "noncovalent"}
SUPPORTED_PATH_MODELS = {"TUNNEL", "SURFACE_LIKE"}
SUPPORTED_CONFIG_ROLES = {"lowsampling", "benchmark", "smoke", "production"}
SUPPORTED_COMPARISON_TYPES = {"same-config", "cross-regime"}

CANONICAL_CONFIG_ROLE_POLICIES: dict[str, dict[str, Any]] = {
    "lowsampling": {
        "expected_use": "Low-sampling diagnostic regime for search-collapse inspection only.",
        "allowed_comparisons": ["cross-regime"],
        "frozen_for_regression": False,
    },
    "benchmark": {
        "expected_use": "Frozen regression baseline for parser, search, and reason-taxonomy changes.",
        "allowed_comparisons": ["same-config", "cross-regime"],
        "frozen_for_regression": True,
    },
    "smoke": {
        "expected_use": "Pipeline health-check regime for end-to-end completion on real data.",
        "allowed_comparisons": ["cross-regime"],
        "frozen_for_regression": False,
    },
    "production": {
        "expected_use": "Operational full-run regime for real-data execution; not a regression baseline.",
        "allowed_comparisons": ["cross-regime"],
        "frozen_for_regression": False,
    },
}


@dataclass(frozen=True, slots=True)
class AtomSpec:
    chain: str
    residue_number: int
    insertion_code: str
    atom_name: str


@dataclass(frozen=True, slots=True)
class PdbConfig:
    path: str
    model_id: int
    altloc_policy: str
    include_hydrogens: bool


@dataclass(frozen=True, slots=True)
class SamplingConfig:
    n_conformers: int
    n_rotations: int
    n_translations: int
    alpha: float


@dataclass(frozen=True, slots=True)
class AnchoringConfig:
    bond_threshold: float
    near_threshold: float
    epsilon: float


@dataclass(frozen=True, slots=True)
class OfftargetConfig:
    distance_threshold: float
    epsilon: float


@dataclass(frozen=True, slots=True)
class ScvConfig:
    confident_fail_threshold: int
    zero_feasible_abort: int


@dataclass(frozen=True, slots=True)
class StagingConfig:
    retry_distance_lower: float
    retry_distance_upper: float
    far_target_threshold: float
    max_stage: int


@dataclass(frozen=True, slots=True)
class TranslationConfig:
    local_fraction: float
    local_min_radius: float
    local_max_radius: float
    local_start_stage: int


@dataclass(frozen=True, slots=True)
class PatConfig:
    path_model: str
    goal_mode: str
    grid_spacing: float
    probe_radius: float
    r_outer_margin: float
    blockage_pass_threshold: float
    top_k_poses: int
    goal_shell_clearance: float
    goal_shell_thickness: float
    surface_window_radius: float


@dataclass(frozen=True, slots=True)
class TargetConfig:
    target_name: str
    config_role: str
    expected_use: str
    allowed_comparisons: list[str]
    frozen_for_regression: bool
    pathway: str
    pdb: PdbConfig
    residue_id_format: str
    target_cysteine: AtomSpec
    anchor_atom_set: list[AtomSpec]
    offtarget_cysteines: list[AtomSpec]
    search_radius: float
    distance_threshold: float
    sampling: SamplingConfig
    anchoring: AnchoringConfig
    offtarget: OfftargetConfig
    scv: ScvConfig
    staging: StagingConfig
    translation: TranslationConfig
    pat: PatConfig
    random_seed: int

    def validate(self) -> None:
        if self.pathway not in SUPPORTED_PATHWAYS:
            raise ValueError(f"Unsupported pathway: {self.pathway}")
        if self.config_role not in SUPPORTED_CONFIG_ROLES:
            raise ValueError(f"Unsupported config_role: {self.config_role}")
        invalid_comparisons = sorted(
            comparison
            for comparison in self.allowed_comparisons
            if comparison not in SUPPORTED_COMPARISON_TYPES
        )
        if invalid_comparisons:
            raise ValueError(
                f"Unsupported allowed_comparisons for {self.config_role}: {invalid_comparisons}"
            )
        policy = CANONICAL_CONFIG_ROLE_POLICIES[self.config_role]
        if self.expected_use != policy["expected_use"]:
            raise ValueError(
                f"{self.config_role} expected_use mismatch: "
                f"{self.expected_use!r} != {policy['expected_use']!r}"
            )
        if self.allowed_comparisons != policy["allowed_comparisons"]:
            raise ValueError(
                f"{self.config_role} allowed_comparisons mismatch: "
                f"{self.allowed_comparisons!r} != {policy['allowed_comparisons']!r}"
            )
        if self.frozen_for_regression != policy["frozen_for_regression"]:
            raise ValueError(
                f"{self.config_role} frozen_for_regression mismatch: "
                f"{self.frozen_for_regression!r} != {policy['frozen_for_regression']!r}"
            )
        if self.pat.path_model not in SUPPORTED_PATH_MODELS:
            raise ValueError(f"Unsupported path_model: {self.pat.path_model}")
        if self.scv.zero_feasible_abort != 4096:
            raise ValueError(
                "This scaffold expects scv.zero_feasible_abort == 4096"
            )
        if self.translation.local_start_stage < 2:
            raise ValueError("local_start_stage must be >= 2")
        if self.staging.max_stage < self.translation.local_start_stage:
            raise ValueError("max_stage must be >= local_start_stage")
        if self.random_seed != 42:
            raise ValueError("This scaffold expects random_seed == 42")

    def to_canonical_dict(self) -> dict[str, Any]:
        return asdict(self)

    def taxonomy_metadata(self) -> dict[str, Any]:
        return {
            "config_role": self.config_role,
            "expected_use": self.expected_use,
            "allowed_comparisons": list(self.allowed_comparisons),
            "frozen_for_regression": self.frozen_for_regression,
        }

    def sampling_signature(self) -> dict[str, Any]:
        return {
            "n_conformers": self.sampling.n_conformers,
            "n_rotations": self.sampling.n_rotations,
            "n_translations": self.sampling.n_translations,
            "alpha": self.sampling.alpha,
        }

    def allows_comparison(self, comparison_type: str) -> bool:
        return comparison_type in self.allowed_comparisons

    def resolve_structure_path(self, repo_root: Path) -> Path:
        pdb_path = Path(self.pdb.path)
        if pdb_path.is_absolute():
            return pdb_path
        if pdb_path.parts and pdb_path.parts[0].lower() == "data":
            return repo_root / pdb_path
        return repo_root / "data" / "structures" / pdb_path
