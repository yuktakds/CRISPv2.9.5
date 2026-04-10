from __future__ import annotations

from pathlib import Path

import pytest

from crisp.v29.repo import RepoRootResolutionError, resolve_repo_root


def test_resolve_repo_root_prefers_explicit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = resolve_repo_root(explicit_repo_root=repo)
    assert result.repo_root == repo.resolve()
    assert result.source == "cli"


def test_resolve_repo_root_invalid_explicit(tmp_path: Path) -> None:
    bad = tmp_path / "missing"
    with pytest.raises(RepoRootResolutionError) as exc:
        resolve_repo_root(explicit_repo_root=bad)
    assert exc.value.code == "CONFIG_REPO_ROOT_INVALID"
