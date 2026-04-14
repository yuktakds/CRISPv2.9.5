# v3 RP-5 Release-Blocking Gate Plan

Status: closed  
Date: 2026-04-14  
Parent: `v3_current_boundary.md`, `v3_rp4_operator_surface_materialization_plan.md`, `v3_rp3_activation_decision_surface.md`, `v3_rp3_promotion_decision_surface.md`  
Scope: RP-5 は RP-4 の suppression を置き換えず、その上に run failure / CI block / artifact finalization refusal を積む。boundary は動かさない。

---

## Closed Intent

RP-5 で landed したのは failure semantics の昇格である。

- RP-4 suppression は引き続き first line of defense として残る
- forbidden surface violation と cross-artifact mismatch は run-level hard block に昇格する
- promotion gate failure は advisory と blocking に分離される
- runner / artifacts / CI-facing status は RP-3 / RP-4 の machine-readable state を読むだけで判定する

RP-5 は新しい success path を追加していない。current boundary は不変であり、stronger public claim も増えていない。

The canonical current boundary is defined in `v3_current_boundary.md`. This document records the landed RP-5 failure-semantics layer under that boundary; it does not redefine the boundary itself.

---

## Implemented State

実装済みの挙動は次のとおり。

1. `operator_surface_state.json` と RP-4 由来の promotion gate result を run-level final gate に集約する
2. forbidden surface violation または cross-artifact mismatch を `exit_code = 1` と artifact finalization refusal に変換する
3. advisory promotion lane failure と blocking promotion lane failure を分離する
4. `sidecar_run_record.json.bridge_diagnostics.release_gate_state` に machine-readable gate state を残す
5. `SidecarRunResult` が `exit_code`, `artifact_failure`, `release_blocked`, `ci_blocked`, advisory/blocking failure lists を返す

---

## Failure Semantics

### Exit code meaning

- `0`: RP-5 hard block なし。suppression reason や advisory promotion failure は残りうる
- `1`: forbidden surface violation または cross-artifact mismatch。sidecar finalization は拒否される
- `2`: RP-5 gate ではない実行エラー。current boundary の外で扱う

### Hard block elevation

RP-5 で run failure へ昇格した主要条件:

- numeric verdict rates leakage while shadow verdict is inactive
- `cap` comparable leakage
- `catalytic_rule3b` component-match leakage
- mixed rc2/v3 aggregate summary request
- verdict-record / sidecar-run-record cross-artifact mismatch
- invalid promotion gate authority reference or unsupported gate ID

これらは suppression だけで通過させず、artifact finalization refusal まで昇格する。

### Advisory vs blocking promotion lanes

- advisory lane failure: run is allowed to complete; CI block は発生しない
- blocking lane failure: run-level hard failureではないが、CI / release block が machine-readable に残る

exploratory lane は advisory のままであり、RP-5 は required promotion を暗黙に authorize しない。

---

## Current Boundary Remains Unchanged

All current-scope facts remain exactly as defined in `v3_current_boundary.md`.

In particular, RP-5 does not widen scope, does not activate stronger operator-facing outcomes, does not change rc2 primary / v3 secondary display semantics, and does not reinterpret component-level indicators as verdict proxies.

---

## Machine-Readable Audit Surface

RP-5 で監査可能になった state:

- `operator_surface_state.json`
- `sidecar_run_record.json.bridge_diagnostics.operator_surface_state`
- `sidecar_run_record.json.bridge_diagnostics.release_gate_state`

これらは explanatory / derived state であり、canonical Layer 0 authority の役割変更は行っていない。`verdict_record.json` が canonical Layer 0 authority、`sidecar_run_record.json` が backward-compatible mirror、`generator_manifest.json` が sidecar inventory authority のままである。

---

## Still Out of Scope

- Cap comparable 参加
- Rule3B comparable 昇格
- `comparator_scope` の変更
- `comparable_channels` の変更
- authority layering 変更
- `output_inventory.json` 変更
- full migration closure
- mixed rc2/v3 aggregate summary authorization
- `[exploratory]` label の除去
- operator-facing stronger claim beyond the current partial scope

---

*End of document*
