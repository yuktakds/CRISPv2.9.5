# v3 RP-3 Activation Decision Surface

Status: accepted and landed
Date: 2026-04-14
Parent: `v3_current_boundary.md`, `adr_v3_10_full_migration_contract.md`, `wp4_wp5_audit_criteria.md`
Scope: docs-only definition of the human decision boundary for operator-facing activation after RP-2 readiness. This document does not widen `comparator_scope`, does not widen `comparable_channels`, and does not authorize required promotion.

---

## Decision Intent

RP-3 activation is a decision surface, not an implementation authorization by itself.

Its purpose is to define the exact operator-facing surfaces that may be considered for activation once RP-2 readiness exists, while keeping these concerns separate from:

- scope widening
- comparable-channel widening
- required CI promotion
- Layer 0 / Layer 1 authority changes
- stronger full-migration claims

This decision is accepted as a decision-surface definition, and minimal activation kernel wiring landed in RP-3, was materialized into operator surfaces in RP-4, and was later consumed by RP-5 release-blocking evaluation without widening public scope.

---

## Current Boundary

The canonical current runtime boundary remains `v3_current_boundary.md`.

Nothing in this document rewrites those runtime facts. This document defines the activation surface only; current runtime outcomes remain those stated in `v3_current_boundary.md`.

---

## Activation Units

RP-3 activation is split into two independent decision units.

### A. `v3_shadow_verdict`

Meaning:

- operator surfaces may render `v3_shadow_verdict`
- rc2 remains the primary verdict surface
- v3 remains secondary and explicitly labeled

This unit does not authorize:

- numeric `verdict_match_rate`
- numeric `verdict_mismatch_rate`
- required promotion
- stronger verdict comparability than already accepted

### B. Numeric `verdict_match_rate` / `verdict_mismatch_rate`

Meaning:

- operator surfaces may render verdict-level numeric comparison metrics
- denominator semantics remain the exact accepted full-verdict-comparable subset

This unit has a strict dependency:

- numeric verdict metrics may activate only after, or together with, `v3_shadow_verdict`
- numeric verdict metrics may never activate while `v3_shadow_verdict` is inactive

This unit does not authorize:

- new comparable channels
- Cap comparable participation
- Rule3B comparable participation
- required promotion

---

## Non-Authorization Boundary

This document does not authorize:

- any widening of `comparator_scope`
- any widening of `comparable_channels`
- treating `path_component_match_rate` as a verdict proxy
- treating `catalytic_rule3a` as a verdict proxy
- any mixed rc2/v3 aggregate summary
- any automatic activation based only on green readiness evidence
- any authority transfer change

Readiness evidence proves computability or consistency only. It does not, by itself, authorize publication.

---

## Formal Gate Requirements

`v3_shadow_verdict` activation requires the formal gate already defined in [adr_v3_10_full_migration_contract.md](/d:/CRISPv2.9.5/docs/adr_v3_10_full_migration_contract.md):

- VN-01 through VN-06 must all be satisfied
- operator surface labeling must remain explicit
- rollback to inactive must remain possible

Numeric `verdict_match_rate` / `verdict_mismatch_rate` additionally require:

- the same VN gate to remain satisfied at activation time
- `v3_shadow_verdict` activation to be active in the same accepted surface
- denominator semantics to remain the full-verdict-comparable subset frozen by contract

If those conditions are not simultaneously true, numeric verdict metrics remain `N/A`.

---

## Cross-Artifact Alignment Required

The following must agree before activation can be merged and at runtime before rendering can occur:

- `verdict_record.json`
- `sidecar_run_record.json`
- bridge summary artifacts
- drift / denominator artifacts
- operator summaries
- validators and tamper tests

If any artifact still encodes inactive state, if runtime VN status is unmet, or if a validator detects activation leakage, rendering must remain blocked.

---

## Operator Rendering Contract After Activation

Required:

- rc2 remains primary
- v3 remains secondary
- `[exploratory]` labeling remains explicit until a separate promotion decision says otherwise
- `semantic_policy_version` remains visible
- component metrics and verdict metrics remain separately rendered

Forbidden:

- showing numeric verdict metrics while `v3_shadow_verdict` is inactive
- presenting `path_component_match_rate` as a verdict proxy
- presenting `catalytic_rule3a` as a verdict proxy
- presenting Rule3B as publicly comparable
- presenting Cap as publicly comparable
- silently making v3 the primary operator surface
- mixed rc2/v3 aggregate summaries

---

## Merge Meaning

This document now means that RP-3 activation has an explicit accepted decision boundary and the implementation is constrained to that exact surface.

It still does not mean:

- any concrete operator-facing activation outcome is live
- promotion is accepted
- stronger scope claims are accepted
- full migration is complete

---

## Freeze-Back Requirement

Any RP-3 activation surface must support freeze-back without reopening RP-1 or RP-2 semantics.

Freeze-back target:

- `v3_shadow_verdict` -> inactive
- `verdict_match_rate` -> `N/A`
- `verdict_mismatch_rate` -> `N/A`
- rc2 primary surface unchanged

That rollback is a rendering freeze-back, not a scope change.

*End of document*
