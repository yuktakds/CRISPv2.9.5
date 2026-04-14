# v3 Reopen-Path Decision Frame

Status: active reference after RP-4 close
Date: 2026-04-14
Parent: `v3_current_boundary.md`, `adr_v3_10_full_migration_contract.md`, `comparable_channels_semantics.md`, `v3_catalytic_public_representation_freeze.md`, `v3_scope_atomics_definition.md`, `v3_rp3_activation_decision_surface.md`, `v3_rp3_promotion_decision_surface.md`, `v3_rp4_operator_surface_materialization_plan.md`
Scope: summarize which reopen-path surfaces are now defined and closed through RP-4, and which decision boundary still remains open.

## Current Frozen Boundary (Reference)

See `v3_current_boundary.md`. This document does not restate or reopen any boundary item.

## Resolved Surfaces

The following surfaces are no longer undefined design questions.

1. operator-facing `v3_shadow_verdict` activation surface  
   Status: decision surface accepted and materialized gate-aware in RP-4.  
   Current runtime meaning: still suppressed unless accepted activation state, VN all-satisfied, and `full_verdict_computable` are all true.

2. operator-facing numeric `verdict_match_rate` / `verdict_mismatch_rate` activation surface  
   Status: decision surface accepted and materialized gate-aware in RP-4.  
   Current runtime meaning: still `N/A` unless numeric activation is accepted, shadow-verdict rendering is already allowed, and the denominator contract is satisfied.

3. exploratory-to-required promotion surface  
   Status: decision surface accepted and materialized as exploratory candidacy only.  
   Current runtime meaning: PR-01 through PR-06 are rendered by reference for candidacy and audit, but no lane is auto-promoted to required.

These surfaces are now defined, implemented, and auditably separated. They are not open design ambiguities anymore.

## Remaining Open Decision

The remaining open reopen-path question is narrower.

1. stronger public claim boundary  
   Current state: open.  
   Open question: whether any stronger claim beyond the current `path_and_catalytic_partial` partial scope should ever be authorized.

Closing that question would still require an explicit human decision. RP-4 did not move it.

## Per-Channel Blocker Table

| channel / surface | current public status | blocker summary | current implication |
|---|---|---|---|
| `path` | public comparable in current partial scope | path component semantics remain component-level, not verdict-level | do not reinterpret `path_component_match_rate` as a verdict proxy |
| `cap` | materialized but not publicly comparable | no rc2 SCV component mapping; remains v3-only evidence | keep outside `comparable_channels`; keep as `[v3-only]` |
| `catalytic_rule3a` | public comparable in current partial scope via `catalytic` | component comparability is active, but verdict-level activation remains separately gated | do not reinterpret `catalytic_rule3a` component match as full verdict comparability |
| `catalytic_rule3b` | materialized but not publicly comparable | retained as v3-only evidence by mixed representation contract | keep outside `component_matches`, verdict denominators, and full-comparability rendering |

## Explicit Human Decision Points

The following still require explicit human decision rather than green automation alone.

- accepting any runtime activation state that would render operator-facing `v3_shadow_verdict`
- accepting any runtime activation state that would render numeric verdict rates
- promoting any exploratory lane or gate to required
- authorizing any stronger public claim beyond the current `path_and_catalytic_partial` partial scope

Automation, green artifacts, denominator readiness, machine-readable suppression state, and sidecar channel materialization remain insufficient by themselves to cross these boundaries.

## UNKNOWN Register

The following remain explicitly UNKNOWN at the current repo state.

- whether any stronger public claim beyond the current `path_and_catalytic_partial` bundle should ever be accepted
- whether any future accepted activation state should remain permanently exploratory or later pair with a separate required-promotion decision
- whether any additional operator-facing surface beyond the currently materialized bridge summary and exploratory candidacy surface should ever be activated

These UNKNOWNs are not implementation TODOs. They remain unresolved policy choices.
