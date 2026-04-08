from __future__ import annotations

from crisp.v3.adapters.rc2_bridge import (
    PATH_ONLY_COVERAGE_CONTRACT_VERSION,
    PATH_ONLY_COVERAGE_FIELDS,
    RC2BridgeAdapter,
    adapt_result_to_dict,
)

RC2Adapter = RC2BridgeAdapter

__all__ = [
    "PATH_ONLY_COVERAGE_CONTRACT_VERSION",
    "PATH_ONLY_COVERAGE_FIELDS",
    "RC2Adapter",
    "RC2BridgeAdapter",
    "adapt_result_to_dict",
]
