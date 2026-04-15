# v3 RP-1 Atomic Widening Decision

Status: accepted  
Date: 2026-04-10  
Parent: `v3_current_boundary.md`, `v3_scope_atomics_definition.md`, `v3_catalytic_public_representation_freeze.md`, `v3_rp6_stronger_public_claim_boundary_decision.md`  
Scope: docs-only human decision record for RP-1. This document authorizes the exact widening boundary for the follow-up implementation PR. It does not itself claim that the current runtime has already widened.

---

## Decision

The repository accepts the RP-1 public-scope widening decision with the following exact atomic transition:

- `comparator_scope: path_only_partial -> path_and_catalytic_partial`
- `comparable_channels: ["path"] -> ["path", "catalytic"]`

This authorization is limited to the current public partial scope. It does not authorize full-scope verdict publication.

---

## Authorized Surface

The authorized RP-1 surface is exactly:

| field | authorized value |
|---|---|
| `comparator_scope` | `path_and_catalytic_partial` |
| `comparable_channels` | `["path", "catalytic"]` |
| comparable component keys | `path`, `catalytic_rule3a` |
| retained v3-only surface | `cap`, `catalytic Rule3B` |

Meaning:

- Path remains public comparable.
- Catalytic enters `comparable_channels` only as the Rule3A public comparable surface.
- Rule3B remains `[v3-only]` and must not appear in `component_matches`.
- Cap remains outside `comparable_channels`.

---

## Non-Authorization Boundary

This decision does not authorize any of the following:

- `v3_shadow_verdict` activation
- numeric `verdict_match_rate`
- numeric `verdict_mismatch_rate`
- full verdict comparability
- `comparator_scope = full_channel_bundle`
- Cap public comparable inclusion
- required CI promotion
- authority layering changes beyond the already accepted M-2 state

---

## Atomicity Contract

The widening remains atomic.

Forbidden implementation shapes:

- change `comparator_scope` without changing `comparable_channels`
- change `comparable_channels` without changing `comparator_scope`
- add `catalytic` to `comparable_channels` while exposing `catalytic` itself in `component_matches`
- expose `catalytic Rule3B` in `component_matches`
- treat the widening as a trigger for operator activation

Cross-artifact update targets for the follow-up implementation PR remain:

- `verdict_record.json`
- `sidecar_run_record.json`
- bridge summary
- operator summary
- validators / guards
- drift report representation

---

## Runtime Boundary During Decision-Only Phase

`v3_current_boundary.md` remains the canonical description of the current runtime boundary until the RP-1 implementation PR lands.

This accepted decision record changes the authorization state, not the already-materialized runtime state.

---

## Implementation Handoff

The next code PR must implement only the authorized RP-1 surface:

- atomic widening to `path_and_catalytic_partial`
- `["path", "catalytic"]` public comparable channel set
- `catalytic_rule3a` comparable surface enablement

The implementation PR must continue to keep:

- `v3_shadow_verdict = inactive`
- `verdict_match_rate = N/A`
- `verdict_mismatch_rate = N/A`
- `output_inventory.json` unchanged

---

*End of document*
