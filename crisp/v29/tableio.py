"""後方互換シム — 実装は crisp.v3.io.tableio に移設済み。

このモジュールは crisp.v3 の外部から tableio を参照する旧コードのためだけに
存在する。新規コードは crisp.v3.io.tableio を直接インポートすること。
"""
from crisp.v3.io.tableio import (  # noqa: F401
    TableFormat,
    TableWriteResult,
    read_records_table,
    write_dataframe,
    write_records_table,
)
