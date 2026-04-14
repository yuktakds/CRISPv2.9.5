# v3 RP-3 Activation Decision Surface

Status: accepted
Date: 2026-04-14
Parent: `v3_current_boundary.md`, `adr_v3_10_full_migration_contract.md`, `wp4_wp5_audit_criteria.md`, `v3_rp4_operator_surface_materialization_plan.md`
Scope: docs-only definition of the human decision boundary for operator-facing activation after RP-2 readiness. This document does not widen `comparator_scope`, does not widen `comparable_channels`, and does not authorize required promotion.

---

## Decision Intent

RP-3 activation is a decision surface, not a boundary-widening authorization.

Its purpose is to define the exact operator-facing surfaces that may be considered for activation once RP-2 readiness exists, while keeping these concerns separate from:

- scope widening
- comparable-channel widening
- required CI promotion
- Layer 0 / Layer 1 authority changes
- stronger full-migration claims

This document is now accepted. RP-4 materialized the gate logic into operator-facing rendering and derived sidecar state without changing the current boundary.

---

## Post-RP-4 Status

After RP-4 close:

- `bridge_operator_summary.md` calls the RP-3 activation kernel through `RuntimeActivationContext`
- `v3_shadow_verdict` rendering remains blocked unless decision acceptance, VN all-satisfied, and `full_verdict_computable` are simultaneously true
- numeric verdict-rate rendering remains blocked unless numeric acceptance, shadow-verdict renderability, and denominator-contract satisfaction are simultaneously true
- suppression reasons are machine-readable in `operator_surface_state.json` and mirrored under `sidecar_run_record.json.bridge_diagnostics.operator_surface_state`
- current boundary remains unchanged, so inactive or suppressed state is still the default under the current shipped activation decisions
- no stronger public claim, no Cap comparable participation, and no Rule3B comparable participation were added by this acceptance

---

## Current Boundary

The canonical current runtime boundary remains `v3_current_boundary.md`.

Under that boundary:

- `comparator_scope` remains `path_and_catalytic_partial`
- `comparable_channels` remains `["path", "catalytic"]`
- `v3_shadow_verdict` remains inactive
- `verdict_match_rate` and `verdict_mismatch_rate` remain `N/A`
- `path_component_match_rate` remains a component metric, not a verdict proxy

Nothing in this document rewrites those runtime facts.

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

If this document is accepted and merged, it means only that RP-3 activation has an explicit decision boundary and implementation may later target that exact surface.

It does not mean:

- activation is already live
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
