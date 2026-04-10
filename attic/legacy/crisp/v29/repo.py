from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


class RepoRootResolutionError(FileNotFoundError):
    """Raised when the repo root cannot be resolved for the integrated CLI."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class RepoRootResolution:
    repo_root: Path
    source: str


REPO_ROOT_ENV = "CRISP_REPO_ROOT"


def resolve_repo_root(
    *,
    explicit_repo_root: str | Path | None = None,
    start: Path | None = None,
) -> RepoRootResolution:
    """Resolve the repo root with explicit override precedence.

    Precedence is fixed as required by the v29.2+ design:
    1. explicit ``--repo-root``
    2. ``CRISP_REPO_ROOT``
    3. upward search for ``pyproject.toml`` from ``start`` / cwd
    """

    if explicit_repo_root is not None:
        candidate = Path(explicit_repo_root).expanduser().resolve()
        if not candidate.exists() or not candidate.is_dir():
            raise RepoRootResolutionError(
                "CONFIG_REPO_ROOT_INVALID",
                f"Explicit repo root is invalid: {candidate}",
            )
        return RepoRootResolution(repo_root=candidate, source="cli")

    env_value = os.environ.get(REPO_ROOT_ENV)
    if env_value:
        candidate = Path(env_value).expanduser().resolve()
        if not candidate.exists() or not candidate.is_dir():
            raise RepoRootResolutionError(
                "CONFIG_REPO_ROOT_INVALID",
                f"Environment repo root is invalid: {candidate}",
            )
        return RepoRootResolution(repo_root=candidate, source="env")

    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists():
            return RepoRootResolution(repo_root=candidate, source="search")

    raise RepoRootResolutionError(
        "CONFIG_REPO_ROOT_NOT_FOUND",
        "Could not locate repo root containing pyproject.toml; provide --repo-root or set CRISP_REPO_ROOT",
    )
