"""テーブル読み書きユーティリティ (v3 自己完結版)。

parquet を優先するが利用不可の場合は JSONL にフォールバックする。
crisp.v29 に依存しない。
"""
from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

_log = logging.getLogger(__name__)

TableFormat = Literal["parquet", "jsonl"]


@dataclass(frozen=True, slots=True)
class TableWriteResult:
    path: str
    format: TableFormat
    row_count: int
    primary_path: str | None = None
    primary_format: TableFormat | None = None
    fallback_used: bool = False
    fallback_reason_code: str | None = None
    fallback_reason_detail: str | None = None

    def to_materialization_event(self, *, logical_output: str) -> dict[str, Any]:
        return {
            "logical_output": logical_output,
            "primary_path": self.primary_path or logical_output,
            "materialized_path": self.path,
            "primary_format": self.primary_format,
            "materialized_format": self.format,
            "fallback_used": self.fallback_used,
            "fallback_reason_code": self.fallback_reason_code,
            "fallback_reason_detail": self.fallback_reason_detail,
        }


# ---------------------------------------------------------------------------
# pandas バックエンドのキャッシュ（モジュールレベル）
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _pandas_backend():
    """pandas をインポートしてキャッシュする。利用不可の場合は None を返す。"""
    try:
        import pandas as pd  # type: ignore[import]
        return pd
    except ImportError:
        _log.debug("pandas not available; JSONL fallback will be used")
        return None


# ---------------------------------------------------------------------------
# 書き込み
# ---------------------------------------------------------------------------

def write_records_table(path: str | Path, rows: list[dict[str, Any]]) -> TableWriteResult:
    """records を parquet（優先）または JSONL に書き出す。"""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    primary_path = str(out)

    pd = _pandas_backend()
    if pd is not None:
        try:
            df = pd.DataFrame(rows)
            df.to_parquet(out)
            _log.debug("write_records_table: parquet %s (%d rows)", out, len(rows))
            return TableWriteResult(
                path=str(out),
                format="parquet",
                row_count=len(rows),
                primary_path=primary_path,
                primary_format="parquet",
            )
        except Exception as exc:
            try:
                out.unlink(missing_ok=True)
            except OSError:
                pass
            _log.warning("parquet write failed (%s); falling back to JSONL", exc)
            fallback_reason_code = "FALLBACK_PARQUET_WRITE_FAILED"
            fallback_reason_detail = str(exc)
    else:
        fallback_reason_code = "FALLBACK_PARQUET_BACKEND_UNAVAILABLE"
        fallback_reason_detail = "pandas unavailable"

    jsonl_path = out.with_suffix(".jsonl")
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            fh.write("\n")
    _log.debug("write_records_table: jsonl %s (%d rows)", jsonl_path, len(rows))
    return TableWriteResult(
        path=str(jsonl_path),
        format="jsonl",
        row_count=len(rows),
        primary_path=primary_path,
        primary_format="parquet",
        fallback_used=True,
        fallback_reason_code=fallback_reason_code,
        fallback_reason_detail=fallback_reason_detail,
    )


# ---------------------------------------------------------------------------
# 読み込み
# ---------------------------------------------------------------------------

def read_records_table(path: str | Path) -> list[dict[str, Any]]:
    """parquet / JSONL / JSON / CSV を読み込み records リストを返す。"""
    p = Path(path)
    suffix = p.suffix.lower()
    pd = _pandas_backend()

    if suffix == ".jsonl":
        return _read_jsonl(p)

    if suffix == ".json":
        payload = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        raise TypeError(f"Expected list payload in {p}")

    if suffix == ".csv":
        with p.open("r", encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    if suffix == ".parquet":
        if pd is None:
            raise RuntimeError(f"parquet support unavailable; cannot read {p}")
        df = pd.read_parquet(p)
        return df.to_dict(orient="records")

    if pd is not None and suffix in {".tsv", ".txt"}:
        df = pd.read_csv(p, sep="\t")
        return df.to_dict(orient="records")

    raise ValueError(f"Unsupported table format: {p}")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """JSONL を読み込む。空行はスキップする。"""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def write_dataframe(path: str | Path, df: Any) -> TableWriteResult:
    """pandas DataFrame を records テーブルとして書き出すヘルパー。"""
    return write_records_table(path, df.to_dict(orient="records"))
