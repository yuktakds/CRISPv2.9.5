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

## Exact Promotion Unit For This Decision

RP-3 promotion surface に従い、この authorize close は 1 つの exact unit だけを扱う。

| field | fixed value |
|---|---|
| target | RP-5 release-blocking audit gate for the frozen keep-path RC evidence family |
| failure consequence | this gate may block release through `sidecar_run_record.json.bridge_diagnostics.release_gate_state.release_blocked = true` and may block CI through `ci_blocked = true` when the same exact gate is carried as `promotion_status = "blocking"` |
| governing artifact family | `required_ci_candidacy_report.json`, `operator_surface_state.json`, `sidecar_run_record.json.bridge_diagnostics.release_gate_state`, `docs/release/evidence/keep_path_rc/2026-04-09/*`, `.github/workflows/v3-keep-path-rc-exploratory.yml`, `tests/v3/test_rp5_release_blocking.py`, `tests/v3/test_keep_path_rc_exploratory_ci_workflow.py`, `tests/v3/test_exploratory_ci_separation.py` |
| freeze-back | revert only this gate from blocking back to advisory / exploratory handling; do not change `comparator_scope`, `comparable_channels`, operator visibility, authority layering, or the required matrix definition |

This unit is not:

- a workflow promotion
- a job promotion
- an activation decision
- a scope widening
- an operator-surface visibility change

The hosted keep-path workflow remains `[exploratory]`. The promoted unit here is
the RP-5 release-blocking audit gate only.

---

## Accepted Baseline

PR-03 baseline gap is closed here by naming one gate-specific accepted baseline:

- accepted baseline name: `rp5_release_blocking_keep_path_rc_baseline_v1`

This baseline is exact-unit-only. It is not a reusable verdict-level baseline
and it does not rename `path_component_match_rate` into `verdict_match_rate`.

`rp5_release_blocking_keep_path_rc_baseline_v1` is satisfied only when all of
the following are true for the same exact gate:

1. the gate-state carrier reports `required_ci_candidacy_report.json.pr_gates.PR-03.passed = true` for `channel_name = "path"`
2. the frozen 30-run gate bundle keeps `campaign_index.json.aggregate.path_component_match_rate_min >= 0.95`
3. the frozen history / hostile-audit surfaces continue to state that
   `path_component_match_rate` is a Path-only component metric and is not a full
   verdict proxy

Accepted baseline satisfaction is therefore read from:

- gate-state carrier: `required_ci_candidacy_report.json`
- fixed 30-run aggregate: `campaign_index.json`
- metric-contract audit: `keep_path_rc_history_report.json` and `keep_path_rc_hostile_audit_report.json`

The runtime candidacy payload is the machine-readable state carrier for this
gate. It is not, by itself, the human authorization authority for PR-02 /
PR-04 / PR-05 / PR-06. Those windows remain evidenced by the frozen audit
bundle below.

---

## Exact Evidence Bundle

PR-02 through PR-06 are bound to one exact evidence bundle for this gate:

| gate | exact evidence for this unit |
|---|---|
| PR-02 | `required_ci_candidacy_report.json.pr_gates.PR-02`, plus the 30-run window contract fixed by `shadow_stability_campaign.json` / `crisp/v3/shadow_stability.py` and the 30-run frozen pack in `campaign_index.json` |
| PR-03 | `required_ci_candidacy_report.json.pr_gates.PR-03`, `campaign_index.json.aggregate.path_component_match_rate_min`, `keep_path_rc_history_report.json.aggregate.metric_contract_note`, `keep_path_rc_hostile_audit_report.json.semantic_delta_watch` |
| PR-04 | `required_ci_candidacy_report.json.pr_gates.PR-04`, `campaign_index.json.aggregate.metrics_drift_zero_all_runs = true` |
| PR-05 | `required_ci_candidacy_report.json.pr_gates.PR-05`, `keep_path_rc_history_report.json.aggregate.windows_hosted_success_all_runs = true`, `.github/workflows/v3-keep-path-rc-exploratory.yml` |
| PR-06 | `required_ci_candidacy_report.json.pr_gates.PR-06`, `keep_path_rc_history_report.json.aggregate.required_matrix_untouched_all_runs = true`, `.github/workflows/v29-required-matrix.yml`, and `tests/v3/test_exploratory_ci_separation.py` |

The evidence bundle is exact-gate-scoped because every referenced artifact is
read only for the keep-path RC release-blocking audit gate and the accepted
baseline above.

This close does not reinterpret the hosted keep-path workflow as a required CI
lane. The workflow remains exploratory evidence generation. The blocking unit is
the release-blocking gate that consumes the evidence family.

For operational close, PR-05 and PR-06 still require hosted evidence:

- PR-05 requires hosted Windows CI history for the named exact gate
- PR-06 requires hosted PR-branch evidence that the rc2-frozen required matrix
  remains regression-free on that same PR branch

Until those hosted artifacts are attached, this evidence bundle is sufficient
for docs-only authorization and design close, not for an operationally final
close claim.

---

## Cross-Artifact Alignment For This Unit

Required promotion for this exact gate is valid only if the following five
layers keep the same blocking semantics:

| layer | required meaning for this exact unit |
|---|---|
| docs | only this RP-5 release-blocking audit gate is authorized; hosted CI lane, scope, activation, and operator visibility remain unchanged |
| CI config | `.github/workflows/v3-keep-path-rc-exploratory.yml` remains exploratory evidence generation only; `.github/workflows/v29-required-matrix.yml` remains the frozen rc2 required-matrix definition and is not mutated by this decision |
| validator / behavior audit | `tests/v3/test_rp5_release_blocking.py` keeps advisory vs blocking separation exact; `tests/v3/test_keep_path_rc_exploratory_ci_workflow.py` and `tests/v3/test_exploratory_ci_separation.py` keep the hosted lane exploratory-only |
| machine-readable outputs | `required_ci_candidacy_report.json`, `operator_surface_state.json`, and `sidecar_run_record.json.bridge_diagnostics.release_gate_state` remain the exact gate-state carriers |
| operator / guard audit | `keep_path_rc_history_report.json` and `keep_path_rc_hostile_audit_report.json` continue to prove that this decision did not widen scope, activate verdict rendering, or overclaim Path-only metrics |

If any layer starts implying workflow promotion, operator activation, scope
widening, or full-verdict comparability, this exact-unit authorization is
invalid and must freeze back.

---

## Docs-Only Authorization Close

Authorize exactly one promotion unit:

- the RP-5 release-blocking audit gate for the frozen keep-path RC evidence family is authorized as a required promotion unit on the RP-3 promotion surface

Current state after this document:

- `design-authorized, operationally pending`
- docs-only authorization is closed for the exact RP-5 gate
- operational close remains pending hosted Windows evidence for PR-05
- operational close remains pending hosted PR-branch rc2-frozen evidence for PR-06
- until those hosted proofs exist on an upstream PR, this repo state must not be
  described as fully closed in the operational sense

This authorize close changes requiredness only. It does not change:

- `comparator_scope`
- `comparable_channels`
- operator visibility semantics
- `[exploratory]` labeling of hosted keep-path CI
- rc2 primary / v3 secondary display roles
- Layer 0 / Layer 1 authority layering
- the required workflow matrix definition

The frozen keep-path RC evidence bundle remains non-authorizing by itself. The
authorization happens here, by explicit human decision on one exact RP-5 gate.

---

## Operational Close

**Status update: operationally closed**  
**Date: 2026-04-17**

PR-05 hosted Windows CI requirement is satisfied. Evidence: `docs/pr05_30run_tracking.md`, count 30/30 consecutive green `exploratory / v3-release-blocking` conclusions on main-branch `v3 Readiness Exploratory` workflow runs (run #1 through run #30, SHA `cf5049483bae` through `e2190e14406a`).

PR-06 required-matrix no-regression requirement is satisfied. The `v2.9.5 Required Matrix` workflow returned `success` on all 30 counted main-branch SHAs without modification to `.github/workflows/v29-required-matrix.yml`. Evidence: `req-matrix` column in `docs/pr05_30run_tracking.md`.

The operational close applies to exactly one unit: the RP-5 release-blocking audit gate for the frozen keep-path RC evidence family.

This operational close does not change:

- the hosted keep-path CI lane label — `[exploratory]` remains
- `comparator_scope`, `comparable_channels`, or operator visibility
- the required workflow matrix definition
- authority layering or Layer 0 / Layer 1 roles
- any adjacent gate, workflow promotion status, or activation decision

Green history accumulated for this exact gate does not authorize adjacent lanes, does not widen scope, and does not activate stronger operator-facing claims. Per RP-3, requiredness remains limited to the exact unit authorized in this document.

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
