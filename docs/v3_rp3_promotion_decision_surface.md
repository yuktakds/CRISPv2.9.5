# v3 RP-3 Promotion Decision Surface

Status: proposed
Date: 2026-04-13
Parent: `v3_current_boundary.md`, `adr_v3_10_full_migration_contract.md`, `wp4_wp5_audit_criteria.md`
Scope: docs-only definition of the human decision boundary for exploratory-to-required promotion after RP-2 readiness. This document does not authorize operator-facing activation by itself.

---

## Decision Intent

RP-3 promotion is a decision surface for requiredness, not a decision surface for visibility.

Activation answers:

- may an operator-facing surface be rendered?

Promotion answers:

- must a specific lane, validator, or gate now block merge or release?

These remain separate decisions and must not be merged into one implicit authorization.

---

## Current Boundary

The canonical current runtime boundary remains `v3_current_boundary.md`.

Under that boundary:

- v3 lanes remain exploratory
- required promotion remains blocked
- rc2 required lanes remain authoritative
- RP-2 readiness evidence is informative, not self-promoting

Nothing in this document changes those runtime facts until it is accepted and merged.

---

## Promotion Units

Every promotion decision must name one exact unit.

Valid promotion units include:

- one CI workflow
- one CI job
- one validator
- one release-blocking audit gate

Each accepted promotion unit must define:

- the exact target being promoted
- the exact failure consequence
- the exact artifact family or contract it governs
- the exact rollback path

`Promote RP-3` is not a valid unit. Promotion must remain lane-by-lane or gate-by-gate.

---

## Non-Authorization Boundary

This document does not authorize:

- any widening of `comparator_scope`
- any widening of `comparable_channels`
- `v3_shadow_verdict` activation
- numeric `verdict_match_rate` activation
- Cap comparable participation
- Rule3B comparable participation
- authority transfer changes
- mixed rc2/v3 summaries

Required promotion cannot be inferred from green exploratory evidence alone.

---

## Human Decision Requirement

Human decision remains mandatory because required promotion changes failure semantics.

A green exploratory lane demonstrates observed stability. It does not, by itself, authorize:

- merge-blocking semantics
- release-blocking semantics
- higher operational burden
- reduced rollback flexibility

Therefore:

- readiness evidence is necessary
- readiness evidence is not sufficient

---

## Formal Gate Requirements

Promotion adopts by reference the CI promotion gate in [adr_v3_10_full_migration_contract.md](/d:/CRISPv2.9.5/docs/adr_v3_10_full_migration_contract.md).

For the exact lane or gate being promoted:

- PR-01 through PR-06 must be satisfied
- the accepted baseline must be explicitly named
- rc2 frozen guarantees must remain intact
- rollback to exploratory must remain possible

If those conditions are not met for the exact unit under review, promotion remains blocked.

---

## Cross-Artifact Alignment Required

Before a promotion decision can merge, and at runtime once it is active, the following must agree for the exact promoted unit:

- CI workflow configuration
- validator behavior
- machine-readable output contracts
- operator-surface guard expectations
- docs defining blocking semantics

If docs say `required` while CI still treats the lane as exploratory, or if validators still treat failure as advisory, the state is inconsistent and merge must be blocked.

---

## Requiredness Contract After Promotion

If a promotion unit is accepted, the repository must state clearly:

- what blocks merge
- what blocks release
- which artifact or gate owns that decision
- whether the blocking applies to all runs or only the named scope

Forbidden:

- implicit promotion of adjacent lanes
- promotion by green history alone
- promotion that silently changes operator visibility semantics
- promotion that changes rc2 authority without a separate accepted decision

---

## Merge Meaning

If this document is accepted and merged, it means only that RP-3 promotion has an explicit decision boundary and future implementation may target a named required lane or gate.

It does not mean:

- any lane is already promoted
- operator activation is accepted
- stronger scope claims are accepted
- full migration is complete

---

## Freeze-Back Requirement

Any promoted unit must support freeze-back to exploratory by explicit follow-up decision without reopening RP-1 or RP-2 semantics.

Freeze-back target:

- blocking lane or gate returns to exploratory or advisory
- artifact contracts remain auditable
- unrelated lanes remain unchanged

That rollback is a requiredness change, not a scope change and not an activation change.

*End of document*
