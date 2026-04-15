from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is in sys.path so that `from tests.<module>` imports
# resolve correctly when pytest is invoked directly on attic/legacy/tests/**.
_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
