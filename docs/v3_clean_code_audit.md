# CRISP v3 クリーンコード監査

Date: 2026-04-10  
Status: in progress

## Scope

- 対象: `crisp/v3`, `crisp/config`, `crisp/repro`, `crisp/utils`, `crisp/v29` 互換シム, `docs/`
- 除外: `attic/legacy/`

## 監査ロードマップ

1. Authority compression (done)
2. Semantic pruning (done)
3. POLA hardening (done)
4. Artifact austerity (done)
5. Orchestration 分割: runner / preconditions / provenance (done)
6. v29 互換依存の縮小: pathyes / tableio を v3 側へ移設し、active code の v29 import を解消 (done)
7. v3 主要モジュール監査: bridge comparator を比較判定 / run-report 集計 / 結果整形に分割 (done)
8. v3 低頻度モジュール監査: keep_path_rc_audit / vn06_readiness を spec / loader / checks に分割 (done)
9. テスト・ドキュメント最終整合 (in progress)

## 実施済み

- current boundary を `docs/v3_current_boundary.md` に集約
- initial implementation 契約と deferred appendix を追加
- catalytic comparable の invariant と validator を固定
- default artifact budget を明文化し debug artifacts を opt-in に分離
- preconditions を判定/記録/フォーマットに分割
- builder/source provenance を分離
- active code / tests の `crisp.v29.pathyes` / `crisp.v29.tableio` 依存を除去
- `crisp/v3/bridge/comparator.py` を orchestration 専用に縮小
- `crisp/v3/vn06_authority.py` を追加し、authority spec と dual-write 判定を分離
- `crisp/v3/keep_path_rc_audit_io.py` / `crisp/v3/keep_path_rc_audit_checks.py` を追加

## 次の反復

- `crisp/v29/contracts.py` を attic 側 legacy 契約へ寄せるか、shim 化するかを決定
- `crisp/v3/migration_scope.py` と `crisp/v3/report_guards.py` の定数境界を再点検
- `uv run pytest -q` の全件確認を継続

*End of document*
