from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SUPPORTED_PATHWAYS = {"covalent", "noncovalent"}
SUPPORTED_PATH_MODELS = {"TUNNEL", "SURFACE_LIKE"}


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

    def resolve_structure_path(self, repo_root: Path) -> Path:
        pdb_path = Path(self.pdb.path)
        if pdb_path.is_absolute():
            return pdb_path
        if pdb_path.parts and pdb_path.parts[0].lower() == "data":
            return repo_root / pdb_path
        return repo_root / "data" / "structures" / pdb_path
