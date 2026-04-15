__all__ = ["__version__"]
__version__ = "0.1.0"

# Compatibility shim: extend package path to include attic legacy modules so that
# `crisp.cli.*`, `crisp.cpg.*`, `crisp.mef.*`, etc. remain importable for the
# required-matrix tests after the attic isolation move.
from pathlib import Path as _Path
_attic_crisp = str(_Path(__file__).resolve().parent.parent / "attic" / "legacy" / "crisp")
if _attic_crisp not in __path__:
    __path__.append(_attic_crisp)
