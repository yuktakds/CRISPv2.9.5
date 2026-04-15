# v3 Reopen-Path Implementation Plan (Archived)

Archived on: 2026-04-14  
Reason: order-only implementation plan was superseded by landed RP-3 / RP-4 / RP-5 decisions and close memos. Current boundary remains in `docs/v3_current_boundary.md`.

Original content follows.

---

# v3 Reopen-Path Implementation Plan (Order Only)

Status: archived  
Date: 2026-04-13  
Scope: ordering only. Boundary is defined in `v3_current_boundary.md`. Decision detail lives in `v3_reopen_path_decision_frame.md` and `adr_v3_10_full_migration_contract.md`.

---

## Completed Order

1. **RP-0 (docs-only)**: Catalytic public comparable representation freeze  
   Reference: `v3_catalytic_public_representation_freeze.md`

2. **RP-0.5 (docs-only)**: scope atomics definition  
   Reference: `v3_scope_atomics_definition.md`

3. **RP-1D (docs-only human decision)**: authorize the exact atomic widening boundary  
   Reference: `v3_rp1_atomic_widening_decision.md`

4. **RP-1I (code)**: implement the authorized atomic widening and `catalytic_rule3a` public comparable surface  
   Resulting current scope: `path_and_catalytic_partial`

5. **RP-2 (code)**: validation-only gates and full-scope denominator prep  
   Resulting current state: internal full-SCV coverage and denominator readiness are auditable cross-artifact, while operator-facing verdict-level activation remains inactive

---

## Next Order

6. **RP-3A (docs-only human decision)**: operator activation decision surface  
   Scope: `v3_shadow_verdict` activation and numeric `verdict_match_rate` / `verdict_mismatch_rate` activation remain separate decisions

7. **RP-3B (docs-only human decision)**: required-promotion decision surface  
   Scope: exploratory -> required promotion remains separate from operator-facing activation

8. **RP-3I (code, minimal)**: implement only the accepted RP-3A / RP-3B decisions, with minimal touch surface and no boundary widening

---

## Guardrails

- No change beyond the current frozen boundary unless an explicit human decision is accepted.
- RP-1I widened only to `path_and_catalytic_partial`; it did not authorize operator-facing verdict-level activation.
- RP-2 readiness evidence does not authorize operator-facing activation or required promotion.
- RP-3 implementation must keep activation, numeric rendering, and required promotion as distinct decision units.
- Cap must remain outside `comparable_channels`.
- Rule3B must remain `[v3-only]`.
