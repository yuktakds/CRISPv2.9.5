# v3 Reopen-Path Decision Frame

Status: design-only
Date: 2026-04-09
Parent: `v3_keep_path_rc_close_memo.md`, `v3_full_migration_preconditions.md`, `adr_v3_10_full_migration_contract.md`, `wp6_public_inclusion_decision_memo.md`
Scope: define the next legitimate reopen-path decision surface after the keep-path RC bundle has been closed under the current public scope.

## Current Frozen Boundary

The current repository state is frozen as follows.

- keep-path RC is closed under the current public scope
- `comparator_scope = path_only_partial`
- `comparable_channels = ["path"]`
- `verdict_record.json` is canonical Layer 0 authority
- `sidecar_run_record.json` is the backward-compatible mirror
- operator-facing `v3_shadow_verdict` is inactive
- operator-facing `verdict_match_rate = N/A`
- `output_inventory.json` remains unchanged rc2 authority

This document does not reopen any of those points.

## Open Decisions

The next design-only questions are separated into distinct decisions.

1. `comparable_channels` widening
   Current state: closed.
   Open question: whether any channel beyond `path` may ever enter the public comparable set under a separately accepted decision.

2. operator activation
   Current state: closed.
   Open question: whether operator-facing `v3_shadow_verdict` and numeric `verdict_match_rate` may ever activate, and under what exact preconditions.

3. required promotion
   Current state: closed.
   Open question: whether any exploratory v3 lane may become required after a separate accepted promotion decision.

4. blocker inventory closure
   Current state: open.
   Open question: which blocker set must be closed before any stronger claim can be proposed, and which blockers are channel-specific versus cross-cutting.

These are independent decision surfaces. Closing one does not imply the others.

## Per-Channel Blocker Table

| channel | current public status | blocker summary | current implication |
|---|---|---|---|
| `path` | public comparable in current keep scope | full-migration and full-verdict claims remain out of scope; Path-only metric semantics must remain separate from verdict-level semantics | stay at `path_only_partial`; do not reinterpret `path_component_match_rate` as a verdict proxy |
| `cap` | materialized but not publicly comparable | rc2-side comparable input boundary, applicability semantics, and drift schema for public comparability remain unresolved | keep outside `comparable_channels`; keep as observational / `[v3-only]` |
| `catalytic` | materialized but not publicly comparable | public comparable representation, applicability semantics, and drift schema remain unresolved; mixed `Rule3A comparable / Rule3B v3-only` representation is not yet defined | keep outside `comparable_channels`; do not widen on the basis of materialization alone |

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
- whether `catalytic` can be represented publicly without semantic ambiguity
- whether operator-facing activation should precede, follow, or remain independent from any future scope widening
- whether any future required-promotion path should operate on the current keep-path bundle, a widened public bundle, or a separate bridge surface entirely

These UNKNOWNs are not implementation TODOs. They are unresolved design decisions.

## Not Authorized By Keep-Path Close

The keep-path RC close does not authorize:

- comparator extension
- CI extension with stronger semantics
- required-matrix changes
- public widening
- operator activation
- reinterpretation of `path_component_match_rate` as verdict-level quality

The next legitimate step is therefore a design-only reopen-path decision, not additional keep-path implementation.

*End of document*
