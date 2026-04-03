from __future__ import annotations

from pathlib import Path

from crisp.config.loader import load_target_config


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"


def _load(name: str):
    return load_target_config(CONFIG_DIR / name)


def _sampling_budget(config) -> int:
    sampling = config.sampling
    return sampling.n_conformers * sampling.n_rotations * sampling.n_translations


def test_9kr6_taxonomy_configs_load() -> None:
    for filename in [
        "9kr6_cys328.lowsampling.yaml",
        "9kr6_cys328.benchmark.yaml",
        "9kr6_cys328.smoke.yaml",
        "9kr6_cys328.production.yaml",
    ]:
        config = _load(filename)
        assert config.target_name == "9KR6_CYS328"
        assert config.pathway == "covalent"
        assert config.random_seed == 42


def test_9kr6_sampling_budget_order_is_monotonic() -> None:
    lowsampling = _load("9kr6_cys328.lowsampling.yaml")
    benchmark = _load("9kr6_cys328.benchmark.yaml")
    smoke = _load("9kr6_cys328.smoke.yaml")
    production = _load("9kr6_cys328.production.yaml")

    assert _sampling_budget(lowsampling) < _sampling_budget(benchmark)
    assert _sampling_budget(benchmark) < _sampling_budget(smoke)
    assert _sampling_budget(smoke) <= _sampling_budget(production)


def test_9kr6_benchmark_uses_distinct_sampling_signature() -> None:
    benchmark = _load("9kr6_cys328.benchmark.yaml")
    lowsampling = _load("9kr6_cys328.lowsampling.yaml")
    smoke = _load("9kr6_cys328.smoke.yaml")

    benchmark_signature = (
        benchmark.sampling.n_conformers,
        benchmark.sampling.n_rotations,
        benchmark.sampling.n_translations,
        benchmark.sampling.alpha,
    )
    assert benchmark_signature != (
        lowsampling.sampling.n_conformers,
        lowsampling.sampling.n_rotations,
        lowsampling.sampling.n_translations,
        lowsampling.sampling.alpha,
    )
    assert benchmark_signature != (
        smoke.sampling.n_conformers,
        smoke.sampling.n_rotations,
        smoke.sampling.n_translations,
        smoke.sampling.alpha,
    )
