"""Compatibility shim: re-exports tests.v29_smoke_helpers from attic legacy location.

The canonical implementation lives at attic/legacy/tests/v29_smoke_helpers.py.
This file restores the original import path (tests.v29_smoke_helpers) used by the
required-matrix test suite after the attic isolation move.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_attic_impl = Path(__file__).resolve().parents[1] / "attic" / "legacy" / "tests" / "v29_smoke_helpers.py"
_spec = importlib.util.spec_from_file_location("_attic_v29_smoke_helpers", _attic_impl)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
# Path constants (REPO_ROOT, CONFIG_DIR, DATA_DIR) are computed by the attic module
# relative to its own __file__, so they correctly resolve to attic/legacy/{configs,data}/.

# Re-export the full public API
REPO_ROOT = _mod.REPO_ROOT
CONFIG_DIR = _mod.CONFIG_DIR
DATA_DIR = _mod.DATA_DIR
assert_outputs_exist = _mod.assert_outputs_exist
create_minimal_full_mode_fixture_bundle = _mod.create_minimal_full_mode_fixture_bundle
make_stub_core_bridge = _mod.make_stub_core_bridge
required_cap_smoke_outputs = _mod.required_cap_smoke_outputs
required_full_smoke_outputs = _mod.required_full_smoke_outputs
row_count = _mod.row_count
write_managed_theta_table = _mod.write_managed_theta_table
write_minimal_assays_fixture = _mod.write_minimal_assays_fixture
write_minimal_caps_fixture = _mod.write_minimal_caps_fixture
write_pat_diagnostics = _mod.write_pat_diagnostics
write_real_library_subset = _mod.write_real_library_subset
