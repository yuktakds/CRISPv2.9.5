# v3 RP-6 Stronger Public Claim Boundary Decision

Status: closed
Date: 2026-04-14
Parent: `v3_current_boundary.md`, `adr_v3_10_full_migration_contract.md`, `v3_reopen_path_decision_frame.md`
Scope: decide whether any stronger public claim beyond the current `path_and_catalytic_partial` partial scope is authorized.

## Decision

Not authorized.

No stronger public claim beyond the current `path_and_catalytic_partial` partial scope is authorized at the current repo state.

This closes the RP-6 decision surface by keeping the current boundary unchanged.

## Meaning

The following remain unchanged:

- `comparator_scope = path_and_catalytic_partial`
- `comparable_channels = ["path", "catalytic"]`
- public comparable component keys remain `path`, `catalytic_rule3a`
- `cap` remains `[v3-only]` and outside `comparable_channels`
- `catalytic_rule3b` remains `[v3-only]` and outside `component_matches`
- `v3_shadow_verdict` remains inactive on the operator surface
- `verdict_match_rate` / `verdict_mismatch_rate` remain non-numeric / `N/A`
- rc2 remains primary and v3 remains `[exploratory]` secondary

## What This Decision Does Not Authorize

This decision does not authorize:

- operator-facing `v3_shadow_verdict` activation
- numeric `verdict_match_rate` / `verdict_mismatch_rate` activation
- required promotion of any CI lane / validator / release gate
- any widening of `comparator_scope`
- any widening of `comparable_channels`
- Cap comparable participation
- Rule3B comparable participation
- any mixed rc2/v3 aggregate summary
- any authority layering change

## Rationale

The current partial bundle already exposes the maximum public claim that is justified without collapsing component-level comparability into SCV-level full verdict comparability.

`path` and `catalytic_rule3a` remain component-level comparable surfaces only. They are not verdict proxies.

Cap has no rc2 SCV component mapping and remains v3-only evidence. Rule3B remains retained v3-only evidence under the mixed-representation contract.

RP-3, RP-4, and RP-5 establish activation, promotion, rendering, and release-blocking surfaces, but none of them authorizes a stronger public claim by itself.

## Consequences

- repo-level design focus remains on preserving the current public boundary
- later activation decisions, if any, remain separate human decisions on already-defined RP-3 surfaces
- later promotion decisions, if any, remain exact unit-by-unit decisions on the RP-3 promotion surface
- any future reconsideration of stronger public claim requires a new explicit decision record

## Freeze-Back / Compatibility

No freeze-back action is required because this decision does not widen scope.

This decision is compatible with all landed RP-0–RP-5 states and requires no authority transfer, no report schema widening, and no CI semantic change.

*End of document*