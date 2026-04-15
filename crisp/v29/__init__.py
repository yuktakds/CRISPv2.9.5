"""CRISP v3 の互換性シム。

v3 側が参照する最小限の道具だけを残し、v29 実装の大半は attic に隔離する。
"""

from __future__ import annotations
from pathlib import Path

__all__ = ["contracts", "pathyes", "tableio"]

# Compatibility shim: extend package path to include attic legacy v29 modules so that
# `crisp.v29.cli`, `crisp.v29.cap`, etc. remain importable for the required-matrix
# tests after the attic isolation move.
_attic_v29 = str(Path(__file__).resolve().parents[2] / "attic" / "legacy" / "crisp" / "v29")
if _attic_v29 not in __path__:
    __path__.append(_attic_v29)
