# CRISP v3 クリーンコード監査

Date: 2026-04-10  
Status: completed

## Scope

- 対象: `crisp/v3`, `crisp/v29` 互換シム, `docs/`
- 除外: `attic/legacy/`

## 完了済みフェーズ

- Authority compression: `docs/v3_current_boundary.md` に current boundary を集約
- Semantic pruning: `docs/v3_initial_implementation_contract.md` / `docs/v3_deferred_appendix.md`
- POLA hardening: catalytic comparable の意味を invariant + validator で固定
- Artifact austerity: `docs/v3_artifact_budget.md`
- v29 互換依存 (pathyes / tableio) を `crisp/v3` 側に移設、v29 は re-export shim に縮小
- `runner.py` / `comparator.py` の I/O と判定を分離 (`crisp/v3/io/`, `crisp/v3/bridge/path_view.py`)
- `keep_path_rc_audit.py` / `vn06_readiness.py` の DRY / dead-code 除去
- docs/ の DRY / YAGNI 除去 (boundary restatement / defensive negation section 削除)

コード変更の詳細は git log を参照。

*End of document*
