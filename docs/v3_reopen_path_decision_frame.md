# v3 Reopen-Path Decision Frame

Status: updated after RP-5 close
Date: 2026-04-14
Parent: `v3_current_boundary.md`, `adr_v3_10_full_migration_contract.md`, `comparable_channels_semantics.md`, `v3_catalytic_public_representation_freeze.md`, `v3_scope_atomics_definition.md`
Scope: define the legitimate post-RP-2 decision surfaces after the accepted RP-1 widening and landed RP-2 readiness work under the current public partial scope.

## Current Frozen Boundary (Reference)

See `v3_current_boundary.md`. This document does not restate or reopen any boundary item.

## Decision Status After RP-5

The RP-3 activation and promotion decision surfaces are accepted and implemented. RP-4 and RP-5 also landed without changing the public boundary.

Closed:

1. operator-facing `v3_shadow_verdict` activation decision surface  
   Accepted as a gate-aware decision surface and wired implementation surface. This does not by itself authorize any concrete operator-facing activation outcome under the current public partial scope.

2. operator-facing numeric `verdict_match_rate` / `verdict_mismatch_rate` activation decision surface  
   Accepted as a gate-aware decision surface and wired implementation surface. It remains strictly dependent on shadow-verdict renderability and denominator contract, and does not by itself authorize any concrete numeric rendering outcome under the current public partial scope.

3. promotion decision surface  
   Accepted as PR-01..PR-06 by-reference gate wiring with advisory/blocking separation. This does not promote any exact lane or gate; current lanes remain exploratory unless a future lane-specific decision is accepted.

## Open Decisions

The next design-only question is intentionally narrow.

1. stronger public claim boundary  
   Current state: open.  
   Open question: whether any stronger claim beyond the current `path_and_catalytic_partial` partial scope should ever be authorized.

## Per-Channel Blocker Table

| channel / surface | current public status | blocker summary | current implication |
|---|---|---|---|
| `path` | public comparable in current partial scope | path component semantics remain component-level, not verdict-level | do not reinterpret `path_component_match_rate` as a verdict proxy |
| `cap` | materialized but not publicly comparable | no rc2 SCV component mapping; remains v3-only evidence | keep outside `comparable_channels`; keep as `[v3-only]` |
| `catalytic_rule3a` | public comparable in current partial scope via `catalytic` | component comparability is active, but verdict-level activation remains separately gated | do not reinterpret `catalytic_rule3a` component match as full verdict comparability |
| `catalytic_rule3b` | materialized but not publicly comparable | retained as v3-only evidence by mixed representation contract | keep outside `component_matches`, verdict denominators, and full-comparability rendering |

## Explicit Human Decision Points

Repo-level design surface definition is now closed except for the stronger-claim boundary above. The following still remain explicit human-decision boundaries for any future concrete authorization under the accepted surfaces.

- activating operator-facing `v3_shadow_verdict`
- activating numeric operator-facing `verdict_match_rate`
- promoting exploratory CI lanes to required
- authorizing any stronger public claim beyond the current `path_and_catalytic_partial` partial scope

Automation, green artifacts, denominator readiness, or materialized sidecar channels are insufficient by themselves to cross these boundaries.

## UNKNOWN Register

The following remain explicitly UNKNOWN at the current repo state.

- whether any future public scope beyond the current `path_and_catalytic_partial` bundle should ever be accepted
- whether any stronger future public claim should bundle operator-facing activation, required promotion, or both
- whether activation and required promotion should remain independently authorized even if a stronger public claim is later proposed

These UNKNOWNs are not implementation TODOs. They are unresolved design decisions.
