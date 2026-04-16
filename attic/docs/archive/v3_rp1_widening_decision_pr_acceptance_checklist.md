# v3 RP-1 Widening Decision PR Acceptance Checklist

Status: design-only  
Date: 2026-04-09  
Parent: `v3_reopen_path_decision_frame.md`, `v3_catalytic_public_representation_freeze.md`, `v3_scope_atomics_definition.md`  
Scope: RP-1 widening decision PR が何を authorize し、何を authorize しないかを review / merge 前に固定するための acceptance checklist。merge それ自体が human decision であり、この文書単体は widening を authorize しない。RP-1 code 着手前に merge される decision artifact として使う。

---

## Purpose

この checklist は、current keep-path public scope を壊さずに、

- `comparator_scope: path_only_partial -> path_and_catalytic_partial`
- `comparable_channels: ["path"] -> ["path", "catalytic"]`

を **atomic に authorize するかどうか** を判断するための review surface である。

RP-1 PR は widening decision PR であって、次を同時に authorize してはならない。

- operator-facing `v3_shadow_verdict` activation
- numeric `verdict_match_rate`
- full verdict comparability claim
- required promotion
- Cap の public comparable inclusion

automation、green artifacts、readiness evidence、materialized sidecar state は widening を authorize しない。authorization boundary を越えるのは human decision merge のみである。

---

## Current Frozen Boundary

review 開始時点で current public scope は `v3_current_boundary.md` の定義を前提とする。この current boundary を PR review 中に前提として崩してはならない。

---

## Proposed RP-1 Decision Surface

この PR で authorize されうる change は次に限定する。

1. `comparator_scope` を `path_and_catalytic_partial` に widen する
2. `comparable_channels` を `["path", "catalytic"]` に widen する
3. Catalytic の public comparable meaning を Rule3A-only comparable projection として有効化する
4. Rule3B を `[v3-only]` のまま残す

この PR で authorize してはならない change は次のとおり。

1. `v3_shadow_verdict` activation
2. numeric `verdict_match_rate`
3. full verdict publish
4. `comparator_scope = full`
5. Cap の `comparable_channels` 参加
6. required matrix change

---

## Acceptance Checklist

以下は PR merge 前にすべて `yes` でなければならない。

### A. Authority And Doc Preconditions

- [ ] `v3_catalytic_public_representation_freeze.md` が current authority set から参照可能である
- [ ] `v3_scope_atomics_definition.md` が current authority set から参照可能である
- [ ] `comparable_channels_semantics.md` が Catalytic Rule3A-only comparable projection と Rule3B `[v3-only]` 分離に揃っている
- [ ] `README.md` の reopen-path 導線が docs-only / non-authorizing wording を維持している
- [ ] current authority set に `scv_anchoring=CANDIDATE` または `scv_offtarget=UNKNOWN` の stale fragment が混入していない

### B. Exact Decision Boundary

- [ ] PR description が widening decision であると明記している
- [ ] PR description が `path_only_partial -> path_and_catalytic_partial` を exact scope transition として明記している
- [ ] PR description が `["path"] -> ["path", "catalytic"]` を exact comparable transition として明記している
- [ ] PR description が “widening does not activate `v3_shadow_verdict` or numeric `verdict_match_rate`” と明記している
- [ ] PR description が “Rule3B remains `[v3-only]`” と明記している
- [ ] PR description が “Cap remains outside `comparable_channels`” と明記している
- [ ] PR description が “required promotion is out of scope” と明記している

### C. Mixed Representation Contract

- [ ] `catalytic` を `comparable_channels` に入れる意味が Rule3A-only public comparable projection だと明記されている
- [ ] comparable component key が `catalytic_rule3a` に固定されている
- [ ] Rule3B が `component_matches` に入らない
- [ ] Rule3B が comparable drift lists に入らない
- [ ] Rule3B が `COMPONENT_VERDICT_COMPARABLE` / `FULL_VERDICT_COMPARABLE` に入らない
- [ ] Rule3B が operator-facing numeric metric explanation に混入しない
- [ ] Catalytic channel 全体を “fully comparable” と表現していない

### D. Atomic Widening Contract

- [ ] `comparator_scope` と `comparable_channels` の変更が同一 PR / 同一 merge decision に束ねられている
- [ ] scope-only widening path が存在しない
- [ ] channels-only widening path が存在しない
- [ ] cross-artifact update target が明示されている

cross-artifact update target は最低限次を含む。

- [ ] `verdict_record.json`
- [ ] `sidecar_run_record.json`
- [ ] bridge summary
- [ ] operator summary
- [ ] validators / guards
- [ ] drift report representation

### E. Operator Safety And Non-Activation

- [ ] operator-facing `v3_shadow_verdict` remains inactive
- [ ] operator-facing `verdict_match_rate` remains `N/A`
- [ ] `path_component_match_rate` remains a Path-only component metric
- [ ] any future `catalytic_rule3a` component metric is labeled as component-level only
- [ ] no text treats `path_component_match_rate` as a full verdict proxy
- [ ] no text treats `catalytic_rule3a` component match as a full verdict proxy
- [ ] `[exploratory]` labeling remains on the widened public surface

### F. Non-Goals And Safety Rails

- [ ] `output_inventory.json` remains unchanged
- [ ] `verdict_record.json` remains canonical Layer 0 authority
- [ ] `sidecar_run_record.json` remains the mirror, not the canonical source
- [ ] Cap remains `[v3-only]`
- [ ] full verdict activation remains a separate decision
- [ ] required promotion remains a separate decision
- [ ] rollback path continues to reuse ADR-V3-11 M-2 rollback framing where applicable

### G. Validation Evidence Required In The PR

- [ ] validator / guard evidence shows non-atomic widening would fail
- [ ] validator / guard evidence shows `v3_shadow_verdict` activation leakage would fail
- [ ] validator / guard evidence shows numeric `verdict_match_rate` leakage would fail
- [ ] validator / guard evidence shows Rule3B comparable leakage would fail
- [ ] validator / guard evidence shows Cap comparable leakage would fail
- [ ] validator / guard evidence shows `output_inventory.json` mutation would fail
- [ ] widened-path green evidence is attached only after the explicit human widening decision surface is fully described

この section は “tests exist” では不十分であり、RP-1 boundary violation を red にできることが必要である。

---

## Suggested PR Footer

```text
RP-1 widening decision boundary:
- authorize only: comparator_scope path_only_partial -> path_and_catalytic_partial
- authorize only: comparable_channels ["path"] -> ["path", "catalytic"]
- keep inactive: v3_shadow_verdict
- keep N/A: verdict_match_rate
- keep v3-only: catalytic Rule3B, cap
- keep unchanged: output_inventory.json
- do not authorize: required promotion
```

---

*End of document*
