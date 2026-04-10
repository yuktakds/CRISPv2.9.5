# CRISP v3 クリーンコード監査 (KISS/DRY/YAGNI/SoC/SRP/POLA/UNIX)

Date: 2026-04-10

## Scope

- 主要対象: `crisp/v3`, `crisp/config`, `crisp/repro`, `crisp/utils`, `crisp/v29` 互換シム
- 参照対象: `docs/`, `tests/v3`
- 除外: `attic/legacy/`（参照のみ、実装範囲外）

## Principles (短い定義)

- KISS: 最小の状態で理解できる設計に寄せる
- DRY: 重複は共通化し、責務の境界を明確にする
- YAGNI: 使っていない拡張性や将来予測を削る
- 関心の分離: I/O・ドメイン・調停を分ける
- SRP: 1モジュール/1関数が1理由でのみ変更される状態に近づける
- POLA: 直感に反する挙動や暗黙規約を排除する
- UNIX哲学: 小さく、合成できる部品に分ける

## 現状ホットスポット (行数ベース上位)

- `crisp/v3/runner.py` (~1035)
- `crisp/v3/preconditions.py` (~968)
- `crisp/v3/keep_path_rc_audit.py` (~618)
- `crisp/v3/bridge/comparator.py` (~612)
- `crisp/v3/vn06_readiness.py` (~563)

## Roadmap (Authority + Semantics)

- Phase A: Authority compression (done)
  - `docs/v3_current_boundary.md` に current boundary/guard を集約
- Phase B: Semantic pruning (done)
  - `docs/v3_initial_implementation_contract.md` に初期実装語彙を固定
  - `docs/v3_deferred_appendix.md` に将来拡張を隔離
- Phase C: POLA hardening (done)
  - catalytic comparable の意味を 1 行 invariant + 1 validator で固定
- Phase D: Artifact austerity (done)
  - `docs/v3_artifact_budget.md` で default artifact budget を明文化
  - debug/calibration artifacts は `artifact_policy=full` opt-in
- Phase E: Code-entry gate (planned)
  - RP-1 は atomic widening + catalytic_rule3a projector/validator/tests に限定

## Roadmap (Code Orchestration)

1. v3 sidecar pipeline 分離 (done)
2. builder/source provenance の分離 (done)
3. preconditions の判定/記録/フォーマット分割 (done)
4. artifact policy の default/opt-in 分離 (done)
5. v29 互換シムの最小化 (planned)
6. v3 低頻度モジュールの整流 (in progress)

## Iteration 3 (2026-04-10)

- `crisp/v3/preconditions.py` を判定/記録/フォーマットで分離。
- `crisp/v29/cli.py` の manifest/sidecar orchestration を分割（v29 実装は attic へ隔離）。
- `docs/v3_artifact_budget.md` を追加し、default 出力を budget 化。
- v3 sidecar の debug artifacts を `artifact_policy=full` opt-in に整理。
- v3 非依存資産を `attic/legacy/` に隔離。

## Next Focus (Iteration 4)

- `crisp/v29` 互換依存（pathyes/tableio）の v3 側移設/縮小
- v3 レポート/ガード周辺の小粒な SRP 分離
- pytest の全件確認と回帰差分の監査
