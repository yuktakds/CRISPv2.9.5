# v3 Reopen-Path Implementation Plan (Order Only)

Status: design-only  
Date: 2026-04-10  
Scope: ordering only. Boundary is defined in `v3_current_boundary.md`. Decision detail lives in `v3_reopen_path_decision_frame.md` and `v3_full_migration_preconditions.md`.

---

## Ordering

1. **RP-0 (docs-only)**: Catalytic public comparable representation freeze  
   Reference: `v3_catalytic_public_representation_freeze.md`

2. **RP-0.5 (docs-only)**: scope atomics definition  
   Reference: `v3_scope_atomics_definition.md`

3. **RP-1D (docs-only human decision)**: authorize the exact atomic widening boundary  
   Reference: `v3_rp1_atomic_widening_decision.md`

4. **RP-1I (code)**: implement the authorized atomic widening and `catalytic_rule3a` public comparable surface  
   Reference: `v3_rp1_atomic_widening_decision.md`

5. **RP-2 (code)**: validation-only gates (WP-3) and full-scope denominator prep (WP-4)  
   Reference: `adr_v3_10_full_migration_contract.md`, `v3x_bridge_ci_contracts.md`

6. **RP-3 (human decision)**: operator activation and required promotion decisions

---

## Guardrails

- No change to the current frozen boundary unless an explicit human decision is accepted.
- RP-1I code must stay within the scoped responsibilities (atomic widening + catalytic_rule3a comparator / validator / tests only).
