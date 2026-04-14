# v3 Reopen-Path Implementation Plan (Archived Order Only)

Status: archived after RP-4 close  
Date: 2026-04-14  
Scope: historical ordering note kept for traceability only. Current active references are `docs/v3_reopen_path_decision_frame.md`, `docs/v3_rp3_activation_decision_surface.md`, `docs/v3_rp3_promotion_decision_surface.md`, and `docs/v3_rp4_operator_surface_materialization_plan.md`.

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

6. **RP-3A / RP-3B (docs-only human decision)**: activation and promotion decision surfaces  
   Result: accepted as separate decision surfaces

7. **RP-4 (code)**: operator-surface materialization and derived suppression / promotion state  
   Result: landed without boundary change

---

## Archive Note

This file is no longer an active root document.

- RP-3 decision surfaces are now recorded in the dedicated RP-3 docs
- RP-4 close is recorded in `docs/v3_rp4_operator_surface_materialization_plan.md`
- future work should not use this file as current authority

---

## Guardrails

- No change beyond the current frozen boundary unless an explicit human decision is accepted.
- RP-1I widened only to `path_and_catalytic_partial`; it did not authorize operator-facing verdict-level activation.
- RP-2 readiness evidence does not authorize operator-facing activation or required promotion.
- RP-3 implementation must keep activation, numeric rendering, and required promotion as distinct decision units.
- Cap must remain outside `comparable_channels`.
- Rule3B must remain `[v3-only]`.
