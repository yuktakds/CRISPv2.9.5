"""後方互換シム — 実装は crisp.v3.pathyes に移設済み。

このモジュールは crisp.v3 の外部から pathyes を参照する旧コードのためだけに
存在する。新規コードは crisp.v3.pathyes を直接インポートすること。
"""
from crisp.v3.pathyes import (  # noqa: F401
    PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
    PAT_DIAGNOSTICS_MISSING_SKIP_CODE,
    PAT_GOAL_PRECHECK_SOURCE,
    PathYesMode,
    PathYesState,
    pathyes_bootstrap_state,
    pathyes_contract_fields,
    pathyes_pat_backed_state,
    resolve_pathyes_state,
)
