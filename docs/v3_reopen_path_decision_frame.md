# v3 Reopen-Path Decision Frame

Status: design-only
Date: 2026-04-13
Parent: `v3_current_boundary.md`, `adr_v3_10_full_migration_contract.md`, `comparable_channels_semantics.md`, `v3_catalytic_public_representation_freeze.md`, `v3_scope_atomics_definition.md`
Scope: define the legitimate post-RP-2 decision surfaces after the accepted RP-1 widening and landed RP-2 readiness work under the current public partial scope.

## Current Frozen Boundary (Reference)

See `v3_current_boundary.md`. This document does not restate or reopen any boundary item.

## Open Decisions

The next design-only questions are separated into distinct decisions.

1. operator-facing `v3_shadow_verdict` activation  
   Current state: closed as inactive (see `v3_current_boundary.md`).  
   Open question: whether operator-facing `v3_shadow_verdict` may activate under the current `path_and_catalytic_partial` partial scope.

2. operator-facing numeric `verdict_match_rate` / `verdict_mismatch_rate` activation  
   Current state: closed as non-numeric / `N/A` (see `v3_current_boundary.md`).  
   Open question: whether verdict-level numeric rendering may activate, and under what exact denominator / claim boundary.

3. required promotion  
   Current state: closed as exploratory-only (see `v3_current_boundary.md`, `adr_v3_10_full_migration_contract.md`).  
   Open question: whether any exploratory lane may become required after a separate accepted promotion decision.

4. stronger public claim boundary  
   Current state: open.  
   Open question: whether any stronger claim beyond the current `path_and_catalytic_partial` partial scope should ever be authorized.

These are independent decision surfaces. Closing one does not imply the others.

## Per-Channel Blocker Table

| channel / surface | current public status | blocker summary | current implication |
|---|---|---|---|
| `path` | public comparable in current partial scope | path component semantics remain component-level, not verdict-level | do not reinterpret `path_component_match_rate` as a verdict proxy |
| `cap` | materialized but not publicly comparable | no rc2 SCV component mapping; remains v3-only evidence | keep outside `comparable_channels`; keep as `[v3-only]` |
| `catalytic_rule3a` | public comparable in current partial scope via `catalytic` | component comparability is active, but verdict-level activation remains separately gated | do not reinterpret `catalytic_rule3a` component match as full verdict comparability |
| `catalytic_rule3b` | materialized but not publicly comparable | retained as v3-only evidence by mixed representation contract | keep outside `component_matches`, verdict denominators, and full-comparability rendering |

## Explicit Human Decision Points

The following remain explicit human-decision boundaries.

- activating operator-facing `v3_shadow_verdict`
- activating numeric operator-facing `verdict_match_rate`
- promoting exploratory CI lanes to required
- authorizing any stronger public claim beyond the current `path_and_catalytic_partial` partial scope

Automation, green artifacts, denominator readiness, or materialized sidecar channels are insufficient by themselves to cross these boundaries.

## UNKNOWN Register

The following remain explicitly UNKNOWN at the current repo state.

- whether operator-facing `v3_shadow_verdict` activation should be accepted at all
- whether numeric `verdict_match_rate` activation should be accepted at all
- whether activation and required promotion should remain independent or be sequenced by later policy
- whether any future public scope beyond the current `path_and_catalytic_partial` bundle should ever be accepted

These UNKNOWNs are not implementation TODOs. They are unresolved design decisions.