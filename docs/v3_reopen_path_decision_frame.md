# v3 Reopen-Path Decision Frame

Status: design-only
Date: 2026-04-09
Parent: `v3_keep_path_rc_close_memo.md`, `v3_full_migration_preconditions.md`, `adr_v3_10_full_migration_contract.md`, `wp6_public_inclusion_decision_memo.md`
Scope: define the next legitimate reopen-path decision surface after the keep-path RC bundle has been closed under the current public scope.

## Current Frozen Boundary (Reference)

See `v3_current_boundary.md`. This document does not restate or reopen any boundary item.

## Open Decisions

The next design-only questions are separated into distinct decisions.

1. `comparable_channels` widening
   Current state: closed (see `v3_current_boundary.md`).
   Open question: whether the now-defined next step to `path_and_catalytic_partial` should be explicitly authorized by human decision.

2. operator activation
   Current state: closed (see `v3_current_boundary.md`).
   Open question: whether operator-facing `v3_shadow_verdict` and numeric `verdict_match_rate` may ever activate, and under what exact preconditions.

3. required promotion
   Current state: closed (see `v3_current_boundary.md`).
   Open question: whether any exploratory v3 lane may become required after a separate accepted promotion decision.

4. blocker inventory closure
   Current state: open.
   Open question: which residual blockers remain after RP-0 / RP-0.5 and before any stronger claim can be proposed.

These are independent decision surfaces. Closing one does not imply the others.

## Per-Channel Blocker Table

| channel | current public status | blocker summary | current implication |
|---|---|---|---|
| `path` | public comparable in current keep scope | full-migration and full-verdict claims remain out of scope; Path-only metric semantics must remain separate from verdict-level semantics | stay at `path_only_partial`; do not reinterpret `path_component_match_rate` as a verdict proxy |
| `cap` | materialized but not publicly comparable | rc2-side comparable input boundary, applicability semantics, and drift schema for public comparability remain unresolved | keep outside `comparable_channels`; keep as observational / `[v3-only]` |
| `catalytic` | materialized but not publicly comparable | mixed `Rule3A comparable / Rule3B v3-only` representation and next-scope atomics are frozen; widening is now an explicit accepted decision, but code remains unimplemented until RP-1I lands | current runtime stays outside `comparable_channels` until the RP-1 implementation PR lands |

## Explicit Human Decision Points

The following remain explicit human-decision boundaries.

- reopening `comparator_scope` beyond `path_only_partial`
- widening `comparable_channels`
- activating operator-facing `v3_shadow_verdict`
- activating numeric operator-facing `verdict_match_rate`
- promoting exploratory CI lanes to required

Automation, green artifacts, or materialized sidecar channels are insufficient by themselves to cross these boundaries.

## UNKNOWN Register

The following remain explicitly UNKNOWN at the current repo state.

- whether public widening beyond `["path"]` will ever be accepted
- whether operator-facing activation should precede, follow, or remain independent from any future scope widening
- whether any future required-promotion path should operate on the current keep-path bundle, a widened public bundle, or a separate bridge surface entirely

These UNKNOWNs are not implementation TODOs. They are unresolved design decisions.

*End of document*
