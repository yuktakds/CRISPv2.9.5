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
6. v29 互換依存の縮小: pathyes / tableio / contracts を v3 側へ移設 (in progress)
7. v3 主要モジュール監査: bridge comparator / report guards / public scope (in progress)
8. v3 低頻度モジュール監査: keep_path_rc_audit / vn06_readiness / migration_scope (pending)
9. テスト・ドキュメント最終整合 (pending)

## 実施済み

- current boundary を `docs/v3_current_boundary.md` に集約
- initial implementation 契約と deferred appendix を追加
- catalytic comparable の invariant と validator を固定
- default artifact budget を明文化し debug artifacts を opt-in に分離
- preconditions を判定/記録/フォーマットに分割
- builder/source provenance を分離

## 次の反復

- `crisp/v29/pathyes.py` の v3 移設計画を確定
- `crisp/v3/bridge/comparator.py` の責務分割を検討
- 監査対象ごとに unit テストで回帰を確認

*End of document*
