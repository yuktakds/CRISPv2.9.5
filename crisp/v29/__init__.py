"""CRISP v29 integration shell.

This package adds an integration layer around the frozen Phase 1 core without
changing the existing core public behavior. The initial implementation focuses
on the audited backlog items:

- integrated manifest / inventory writers
- frozen core bridge
- Rule 3 proposal trace as a trace-only no-op
- Rule 1 bootstrap branch with PathYesAdapter suppression
- Cap batch verdict truth source writer
- integrated CLI entrypoints
"""

from __future__ import annotations

__all__ = [
    "core_bridge",
    "pathyes",
    "rule1",
    "repo",
    "writers",
    "validation",
]
