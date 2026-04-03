from __future__ import annotations

from pathlib import Path

import pytest

from crisp.config.loader import DEPRECATED_CONFIG_FILENAMES, load_target_config
from crisp.config.models import (
    CANONICAL_CONFIG_ROLE_POLICIES,
    ComparisonType,
    assert_config_comparison_allowed,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"


def _load(name: str):
    return load_target_config(CONFIG_DIR / name)


def _sampling_budget(config) -> int:
    sampling = config.sampling
    return sampling.n_conformers * sampling.n_rotations * sampling.n_translations


def test_9kr6_taxonomy_configs_load() -> None:
    expected_roles = {
        "9kr6_cys328.lowsampling.yaml": "lowsampling",
        "9kr6_cys328.benchmark.yaml": "benchmark",
        "9kr6_cys328.smoke.yaml": "smoke",
        "9kr6_cys328.production.yaml": "production",
    }
    for filename, role in expected_roles.items():
        config = _load(filename)
        assert config.target_name == "9KR6_CYS328"
        assert config.config_role == role
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


def test_9kr6_role_policy_is_fixed() -> None:
    for filename in [
        "9kr6_cys328.lowsampling.yaml",
        "9kr6_cys328.benchmark.yaml",
        "9kr6_cys328.smoke.yaml",
        "9kr6_cys328.production.yaml",
    ]:
        config = _load(filename)
        policy = CANONICAL_CONFIG_ROLE_POLICIES[config.config_role]
        assert config.expected_use == policy["expected_use"]
        assert config.allowed_comparisons == policy["allowed_comparisons"]
        assert config.frozen_for_regression == policy["frozen_for_regression"]


def test_only_benchmark_allows_same_config_comparison() -> None:
    benchmark = _load("9kr6_cys328.benchmark.yaml")
    lowsampling = _load("9kr6_cys328.lowsampling.yaml")
    smoke = _load("9kr6_cys328.smoke.yaml")
    production = _load("9kr6_cys328.production.yaml")

    assert benchmark.allows_comparison(ComparisonType.SAME_CONFIG) is True
    assert lowsampling.allows_comparison(ComparisonType.SAME_CONFIG) is False
    assert smoke.allows_comparison(ComparisonType.SAME_CONFIG) is False
    assert production.allows_comparison(ComparisonType.SAME_CONFIG) is False


def test_cross_regime_guard_accepts_lowsampling_vs_smoke() -> None:
    lowsampling = _load("9kr6_cys328.lowsampling.yaml")
    smoke = _load("9kr6_cys328.smoke.yaml")

    comparison = assert_config_comparison_allowed(
        lhs=lowsampling,
        rhs=smoke,
        comparison_type=ComparisonType.CROSS_REGIME,
        context="test",
    )
    assert comparison is ComparisonType.CROSS_REGIME


def test_same_config_guard_accepts_benchmark_pair() -> None:
    benchmark_lhs = _load("9kr6_cys328.benchmark.yaml")
    benchmark_rhs = _load("9kr6_cys328.benchmark.yaml")

    comparison = assert_config_comparison_allowed(
        lhs=benchmark_lhs,
        rhs=benchmark_rhs,
        comparison_type=ComparisonType.SAME_CONFIG,
        context="test",
    )
    assert comparison is ComparisonType.SAME_CONFIG


def test_regression_guard_rejects_smoke_config() -> None:
    smoke = _load("9kr6_cys328.smoke.yaml")
    with pytest.raises(ValueError, match="frozen_for_regression=true"):
        smoke.assert_regression_ready(context="test-regression")


def test_regression_guard_rejects_production_config() -> None:
    production = _load("9kr6_cys328.production.yaml")
    with pytest.raises(ValueError, match="frozen_for_regression=true"):
        production.assert_regression_ready(context="test-regression")


def test_unknown_allowed_comparison_rejected_at_load(tmp_path: Path) -> None:
    source = (CONFIG_DIR / "9kr6_cys328.benchmark.yaml").read_text(encoding="utf-8")
    invalid = source.replace(
        "allowed_comparisons:\n  - same-config\n  - cross-regime",
        "allowed_comparisons:\n  - unknown-comparison",
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(invalid, encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported comparison_type"):
        load_target_config(path)


def test_deprecated_9kr6_alias_is_rejected(tmp_path: Path) -> None:
    deprecated = tmp_path / "9kr6_cys328.yaml"
    with pytest.raises(ValueError, match="Deprecated target config filename"):
        load_target_config(deprecated)
    assert DEPRECATED_CONFIG_FILENAMES["9kr6_cys328.yaml"] == "configs/9kr6_cys328.lowsampling.yaml"
