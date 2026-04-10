"""分子ライブラリ入力の正規化ユーティリティ。

サポートするファイル形式:
  - .parquet / .jsonl / .json / .csv / .tsv / .txt : tableio 経由で読み込む
  - .smi / .smiles : SMI 形式（タブ区切りまたはスペース区切り）
    - col0 = SMILES（RDKit 拡張表記 |...| を除去）
    - col1 = molecule_id（省略時は連番）
    - 以降の列は無視する

Bug1 修正:
  旧実装は .smiles / .smi を未認識としてフォールバックし、
  line.split() でスペース・タブ両方を区切り文字として使っていた。
  RDKit 拡張表記 |&1:5,10,r| を含む行では
  col0="SMILES", col1="|&1:5,10,r|", col2="Z1234567890" となり
  正しい molecule_id が取れず、かつ重複 ID エラーが発生していた。

  修正: .smiles / .smi を明示的に認識し、タブ優先分割 + |...| 除去を行う。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from crisp.v29.tableio import read_records_table

_log = logging.getLogger(__name__)

RUN_MODE_ALIASES: dict[str, str] = {
    "core-only": "core-only",
    "core+rule1": "core+rule1",
    "core+rule1+cap": "core+rule1+cap",
    "full": "full",
    "rule1-bootstrap": "core+rule1",
}

# SMI 形式として扱う拡張子（Bug1 修正で追加）
_SMI_SUFFIXES: frozenset[str] = frozenset({".smi", ".smiles"})


def normalize_run_mode(value: str) -> str:
    """run_mode 文字列を正規化する。未知の値は ValueError を送出する。"""
    try:
        return RUN_MODE_ALIASES[value]
    except KeyError as exc:
        raise ValueError(f"Unsupported run mode: {value!r}") from exc


# ---------------------------------------------------------------------------
# RDKit 拡張表記の除去
# ---------------------------------------------------------------------------

def _strip_rdkit_extension(raw_smiles: str) -> str:
    """RDKit 拡張表記 ( |&1:5,10,r| 等) を除去した純粋な SMILES を返す。

    RDKit は SMILES 文字列の後ろにスペース + |...| の形で
    立体化学・増強表記を付加することがある。これは SMILES の一部ではなく
    RDKit 固有の拡張表記であり、Chem.MolFromSmiles は |...| を無視する。
    しかし空白区切りで分割すると molecule_id と混同されるため、先に除去する。
    """
    # " |" 以降をすべて除去する
    pipe_idx = raw_smiles.find(" |")
    if pipe_idx != -1:
        return raw_smiles[:pipe_idx].strip()
    return raw_smiles.strip()


# ---------------------------------------------------------------------------
# SMI 形式パーサ（Bug1 修正の核心）
# ---------------------------------------------------------------------------

def _parse_smi_file(path: Path) -> list[dict[str, Any]]:
    """SMI / SMILES 形式のファイルを読み込んで records リストを返す。

    フォーマット規則:
      - タブ区切りを優先。タブがない行はスペース区切りにフォールバック。
      - col0 = SMILES（|...| 拡張表記を除去）
      - col1 = molecule_id（省略時は連番）
      - コメント行 (#) と空行はスキップ。

    Bug1 修正:
      旧実装は line.split()（スペース・タブ両方）を使っていたため、
      "SMILES |&1:6,r|\tID" が ['SMILES', '|&1:6,r|', 'ID'] に分割され
      mol_id = '|&1:6,r|' になっていた。
      本実装はタブ優先分割により col1 が正しく ID を指すようにする。
    """
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    raw = path.read_text(encoding="utf-8")

    for lineno, raw_line in enumerate(raw.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # タブ区切り優先（ファイルが TSV 形式の場合）
        if "\t" in line:
            parts = line.split("\t")
        else:
            parts = line.split()

        if not parts:
            continue

        raw_smiles_field = parts[0]
        smiles = _strip_rdkit_extension(raw_smiles_field)

        if not smiles:
            _log.warning("SMI parse: empty SMILES at line %d, skipping", lineno)
            continue

        # molecule_id の取得
        if len(parts) > 1:
            candidate_id = parts[1].strip()
            # タブなし行でスペース分割した場合、col1 が |...|  になる可能性を除去
            if candidate_id.startswith("|"):
                # |...| をスキップして次の列を使う
                molecule_id = parts[2].strip() if len(parts) > 2 else f"compound_{lineno:05d}"
                _log.debug(
                    "SMI parse line %d: col1=%r is |...| notation, using col2=%r as molecule_id",
                    lineno, candidate_id, molecule_id,
                )
            else:
                molecule_id = candidate_id
        else:
            molecule_id = f"compound_{lineno:05d}"

        if molecule_id in seen_ids:
            raise ValueError(f"INPUT_DUPLICATE_ID: molecule_id={molecule_id} (line {lineno})")
        seen_ids.add(molecule_id)

        rows.append(
            {
                "molecule_id": molecule_id,
                "smiles": smiles,
                "library_id": path.stem,
                "input_order": len(rows),
            }
        )

    return rows


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def load_molecule_rows(path: str | Path) -> list[dict[str, Any]]:
    """ライブラリファイルを読み込み、正規化された records リストを返す。

    各 record の必須キー: molecule_id, smiles, library_id, input_order
    """
    p = Path(path)
    suffix = p.suffix.lower()

    # SMI / SMILES 形式（Bug1 修正）
    if suffix in _SMI_SUFFIXES:
        _log.debug("load_molecule_rows: SMI format detected (%s)", suffix)
        return _parse_smi_file(p)

    # tableio 対応形式
    if suffix in {".parquet", ".jsonl", ".json", ".csv", ".tsv", ".txt"}:
        rows = read_records_table(p)
        if rows and "smiles" in rows[0]:
            return _normalize_table_rows(rows, p)

    # その他: .txt など拡張子なしまたは未知 → SMI fallback
    _log.debug("load_molecule_rows: unknown suffix %r, trying SMI fallback", suffix)
    return _parse_smi_file(p)


def _normalize_table_rows(rows: list[dict[str, Any]], source_path: Path) -> list[dict[str, Any]]:
    """tableio で読んだ rows を正規化する（SMILES 列が存在する前提）。"""
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for i, row in enumerate(rows):
        molecule_id = str(
            row.get("molecule_id")
            or row.get("name")
            or row.get("compound_id")
            or f"compound_{i + 1:05d}"
        )
        smiles_val = row.get("smiles") or row.get("SMILES")
        if smiles_val is None:
            raise ValueError("INPUT_SCHEMA_INVALID: missing smiles column/value")
        if molecule_id in seen:
            raise ValueError(f"INPUT_DUPLICATE_ID: molecule_id={molecule_id}")
        seen.add(molecule_id)
        normalized.append(
            {
                "molecule_id": molecule_id,
                "smiles": str(smiles_val),
                "library_id": str(row.get("library_id", source_path.stem)),
                "input_order": int(row.get("input_order", i)),
                **{
                    k: v
                    for k, v in row.items()
                    if k not in {"molecule_id", "smiles", "library_id", "input_order"}
                },
            }
        )
    return normalized


def to_core_library_text(rows: Iterable[dict[str, Any]]) -> str:
    """rows を Core CLI が受け取る SMI 形式の文字列に変換する。"""
    lines = [f"{row['smiles']} {row['molecule_id']}" for row in rows]
    return "\n".join(lines) + ("\n" if lines else "")


def compute_joined_smiles(rows: Iterable[dict[str, Any]]) -> str:
    """全 SMILES を改行区切りで結合する（input_hash 計算用）。"""
    return "\n".join(str(row["smiles"]) for row in rows)
