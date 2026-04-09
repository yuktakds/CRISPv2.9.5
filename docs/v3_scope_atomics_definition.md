# v3 Scope Atomics Definition

Status: accepted  
Date: 2026-04-09  
Parent: `v3_catalytic_public_representation_freeze.md`, `v3_reopen_path_decision_frame.md`, `v3_reopen_path_implementation_plan.md`, `wp6_public_inclusion_decision_memo.md`  
Scope: RP-0.5. `comparator_scope` の次の値と widening の atomic semantics を docs-only で定義する。RP-1 code 以前の gate。

---

## Decision

`path_only_partial` の次の scope 値は **`path_and_catalytic_partial`** とする。

この scope は次を意味する。

- Path remains public comparable
- Catalytic Rule3A becomes public comparable under the mixed representation contract
- Catalytic Rule3B remains `[v3-only]`
- full verdict comparability is still not activated
- operator-facing `v3_shadow_verdict` is still inactive
- operator-facing `verdict_match_rate` remains `N/A`

---

## Current Boundary

current public scope は不変である。

- current: `path_only_partial`
- current `comparable_channels = ["path"]`
- current operator-facing final verdict surface inactive

この文書は next scope value と transition rule を定義するだけであり、遷移そのものを authorize しない。

---

## Next Scope Value

`path_and_catalytic_partial` は次の partial scope である。

| field | value |
|---|---|
| `comparator_scope` | `path_and_catalytic_partial` |
| `comparable_channels` | `["path", "catalytic"]` |
| comparable component keys | `path`, `catalytic_rule3a` |
| v3-only retained | `cap`, `catalytic_rule3b` |
| `v3_shadow_verdict` | inactive |
| operator `verdict_match_rate` | `N/A` |

注記: `comparable_channels` に `catalytic` を入れる意味は、RP-0 mixed representation に従った Rule3A public comparable surface の有効化である。Rule3B を comparable に昇格させる意味ではない。

---

## Atomic Widening Rule

`comparator_scope` widening と `comparable_channels` widening は atomic に行う。

allowed transition:

- `path_only_partial` + `["path"]`
- to
- `path_and_catalytic_partial` + `["path", "catalytic"]`

forbidden transitions:

- `comparator_scope` だけを `path_and_catalytic_partial` に変える
- `comparable_channels` だけを `["path", "catalytic"]` に変える
- `catalytic` を追加するが Rule3A/Rule3B mixed representation を無視する
- widening と同時に `v3_shadow_verdict` を activate する
- widening と同時に numeric `verdict_match_rate` を出す
- Cap を `comparable_channels` に混ぜる

cross-artifact では次が同一 commit / 同一 decision で揃っていなければ hard block とする。

- `verdict_record.json`
- `sidecar_run_record.json`
- bridge summary
- operator summary
- validators / guards

---

## Metric Semantics Under `path_and_catalytic_partial`

この scope で成立する指標と、まだ成立しない指標を次に固定する。

| metric | status |
|---|---|
| `path_component_match_rate` | continue as Path-only component metric |
| `catalytic_rule3a` component match | may be introduced as a component-level comparable metric |
| coverage drift | allowed at component level |
| applicability drift | allowed at component level |
| metrics drift | allowed at component level |
| `verdict_match_rate` | `N/A` |
| `verdict_mismatch_rate` | `N/A` |
| `v3_shadow_verdict` | inactive |

`path_component_match_rate` は引き続き verdict-level quality 指標ではない。
`catalytic_rule3a` component match が追加されても、それは full verdict comparability の成立を意味しない。

---

## Activation Non-Trigger Rule

scope widening は activation trigger ではない。

`path_only_partial -> path_and_catalytic_partial` の遷移が起きても、次は自動的に起きない。

- `v3_shadow_verdict` activation
- operator-facing numeric `verdict_match_rate`
- full verdict comparability publish
- required promotion

これらはすべて別の explicit human decision surface に残る。

---

## What This Definition Authorizes

- next scope value の docs-only freeze
- scope atomics rule の docs-only freeze

## What This Definition Does Not Authorize

- actual widening
- operator activation
- full verdict comparability claim
- required promotion

RP-1 は、human widening decision が merged した後にのみ code へ進める。

---

*End of document*
