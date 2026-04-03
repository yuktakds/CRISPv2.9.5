from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

SUPPORTED_PATHWAYS = {"covalent", "noncovalent"}
SUPPORTED_PATH_MODELS = {"TUNNEL", "SURFACE_LIKE"}
SUPPORTED_CONFIG_ROLES = {"lowsampling", "benchmark", "smoke", "production"}


class ComparisonType(StrEnum):
    NONE = "none"
    SAME_CONFIG = "same-config"
    CROSS_REGIME = "cross-regime"


SUPPORTED_COMPARISON_TYPES = frozenset(member.value for member in ComparisonType)
EXECUTABLE_COMPARISON_TYPES = frozenset({
    ComparisonType.SAME_CONFIG.value,
    ComparisonType.CROSS_REGIME.value,
})

CANONICAL_CONFIG_ROLE_POLICIES: dict[str, dict[str, Any]] = {
    "lowsampling": {
        "expected_use": "Low-sampling diagnostic regime for search-collapse inspection only.",
        "allowed_comparisons": (ComparisonType.CROSS_REGIME,),
        "frozen_for_regression": False,
    },
    "benchmark": {
        "expected_use": "Frozen regression baseline for parser, search, and reason-taxonomy changes.",
        "allowed_comparisons": (ComparisonType.SAME_CONFIG, ComparisonType.CROSS_REGIME),
        "frozen_for_regression": True,
    },
    "smoke": {
        "expected_use": "Pipeline health-check regime for end-to-end completion on real data.",
        "allowed_comparisons": (ComparisonType.CROSS_REGIME,),
        "frozen_for_regression": False,
    },
    "production": {
        "expected_use": "Operational full-run regime for real-data execution; not a regression baseline.",
        "allowed_comparisons": (ComparisonType.CROSS_REGIME,),
        "frozen_for_regression": False,
    },
}


def normalize_comparison_type(value: str | ComparisonType) -> ComparisonType:
    try:
        return value if isinstance(value, ComparisonType) else ComparisonType(str(value))
    except ValueError as exc:
        valid = ", ".join(sorted(SUPPORTED_COMPARISON_TYPES))
        raise ValueError(
            f"Unsupported comparison_type={value!r}; expected one of: {valid}"
        ) from exc


def _serialize_allowed_comparisons(
    values: tuple[ComparisonType, ...] | list[ComparisonType],
) -> list[str]:
    return [value.value for value in values]


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
    allowed_comparisons: tuple[ComparisonType, ...] | list[str] | list[ComparisonType]
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

    def __post_init__(self) -> None:
        normalized = tuple(
            normalize_comparison_type(value)
            for value in self.allowed_comparisons
        )
        object.__setattr__(self, "allowed_comparisons", normalized)

    def validate(self) -> None:
        if self.pathway not in SUPPORTED_PATHWAYS:
            raise ValueError(f"Unsupported pathway: {self.pathway}")
        if self.config_role not in SUPPORTED_CONFIG_ROLES:
            raise ValueError(f"Unsupported config_role: {self.config_role}")
        allowed_values = _serialize_allowed_comparisons(self.allowed_comparisons)
        invalid_comparisons = sorted(
            comparison
            for comparison in allowed_values
            if comparison not in SUPPORTED_COMPARISON_TYPES
        )
        if invalid_comparisons:
            raise ValueError(
                f"Unsupported allowed_comparisons for {self.config_role}: {invalid_comparisons}"
            )
        if len(set(self.allowed_comparisons)) != len(self.allowed_comparisons):
            raise ValueError(f"{self.config_role} allowed_comparisons must not contain duplicates")
        if ComparisonType.NONE in self.allowed_comparisons and len(self.allowed_comparisons) != 1:
            raise ValueError(
                f"{self.config_role} allowed_comparisons may contain 'none' only as a sole entry"
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
                f"{allowed_values!r} != {_serialize_allowed_comparisons(policy['allowed_comparisons'])!r}"
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
            "allowed_comparisons": self.allowed_comparison_values(),
            "frozen_for_regression": self.frozen_for_regression,
        }

    def sampling_signature(self) -> dict[str, Any]:
        return {
            "n_conformers": self.sampling.n_conformers,
            "n_rotations": self.sampling.n_rotations,
            "n_translations": self.sampling.n_translations,
            "alpha": self.sampling.alpha,
        }

    def allowed_comparison_values(self) -> list[str]:
        return _serialize_allowed_comparisons(self.allowed_comparisons)

    def allows_comparison(self, comparison_type: str | ComparisonType) -> bool:
        normalized = normalize_comparison_type(comparison_type)
        if normalized is ComparisonType.NONE:
            return False
        return normalized in self.allowed_comparisons

    def assert_allows_comparison(
        self,
        comparison_type: str | ComparisonType,
        *,
        context: str,
        config_path: str | Path | None = None,
    ) -> ComparisonType:
        normalized = normalize_comparison_type(comparison_type)
        if normalized.value not in EXECUTABLE_COMPARISON_TYPES:
            raise ValueError(
                f"{context} does not support comparison_type={normalized.value!r}"
            )
        if not self.allows_comparison(normalized):
            location = "" if config_path is None else f" ({config_path})"
            raise ValueError(
                f"{context} requires comparison_type={normalized.value!r}, "
                f"but config_role={self.config_role!r}{location} only allows "
                f"{self.allowed_comparison_values()!r}"
            )
        return normalized

    def assert_regression_ready(
        self,
        *,
        context: str,
        config_path: str | Path | None = None,
    ) -> None:
        if not self.frozen_for_regression:
            location = "" if config_path is None else f" ({config_path})"
            raise ValueError(
                f"{context} requires frozen_for_regression=true, "
                f"but config_role={self.config_role!r}{location} is not a regression baseline"
            )
        self.assert_allows_comparison(
            ComparisonType.SAME_CONFIG,
            context=context,
            config_path=config_path,
        )

    def resolve_structure_path(self, repo_root: Path) -> Path:
        pdb_path = Path(self.pdb.path)
        if pdb_path.is_absolute():
            return pdb_path
        if pdb_path.parts and pdb_path.parts[0].lower() == "data":
            return repo_root / pdb_path
        return repo_root / "data" / "structures" / pdb_path


def assert_config_comparison_allowed(
    *,
    lhs: TargetConfig,
    rhs: TargetConfig,
    comparison_type: str | ComparisonType,
    lhs_path: str | Path | None = None,
    rhs_path: str | Path | None = None,
    context: str = "config comparison",
) -> ComparisonType:
    normalized = normalize_comparison_type(comparison_type)
    lhs.assert_allows_comparison(
        normalized,
        context=context,
        config_path=lhs_path,
    )
    rhs.assert_allows_comparison(
        normalized,
        context=context,
        config_path=rhs_path,
    )
    if normalized is ComparisonType.SAME_CONFIG:
        if lhs.to_canonical_dict() != rhs.to_canonical_dict():
            raise ValueError(
                f"{context} with comparison_type='same-config' requires identical target configs"
            )
    elif normalized is ComparisonType.CROSS_REGIME:
        if lhs.config_role == rhs.config_role:
            raise ValueError(
                f"{context} with comparison_type='cross-regime' requires different config_role values"
            )
    else:
        raise ValueError(f"{context} does not support comparison_type={normalized.value!r}")
    return normalized
