# ADR: Rule3 Proposal-Connected Evolution Boundary

Date: 2026-04-03
Status: Accepted for `v2.9.5`, deferred beyond trace-only

## Context

`v2.9.5` implements Rule3 as a trace-only no-op:

- `crisp.v29.anchor_proposal.policy.PROPOSAL_POLICY_VERSION = "v29.trace-only.noop"`
- candidate sources are recorded
- candidate ordering is recorded
- `core_bridge` writes proposal trace into `evidence_core`
- frozen core public behavior is not changed

This was intentional. The integrated shell needed to expose Rule3 provenance without
reopening the object-logic boundary between the frozen core, Rule1 gating, Cap branch,
and run-level reporting.

## Decision

`v2.9.5` does not implement proposal-connected Rule3.

The accepted Rule3 contract for this release is:

1. record candidate sources and order only
2. do not change `run_cpg()` public behavior
3. do not redefine anchoring predicates or thresholds
4. do not emit outcome-collapse claims from Rule3 traces
5. do not route PAT, Rule1, or Cap run-level signals back into Core object logic

In short: Rule3 remains observational in `v2.9.5`.

## Why this decision was taken

The main risks of going proposal-connected too early are:

- boundary break between integrated-shell diagnostics and frozen core logic
- hidden coupling between candidate ordering and CoreSCV outcomes
- replay ambiguity if proposal ordering changes object-level evaluation but trace fields are incomplete
- taxonomy collapse if smoke/production behavior is reinterpreted as same-config benchmark drift

The current trace-only mode avoids those risks while still making Rule3 auditable.

## Non-goals for `v2.9.5`

The following are explicitly out of scope for this release:

- proposal order affecting anchoring pass/fail logic
- Rule3 changing `CONTINUE` / `FINALIZE` behavior
- Rule3 changing near-band semantics from reporting-only into execution semantics
- PAT diagnostics influencing Core predicate logic
- Rule1 applicability influencing Core predicate logic
- Cap branch outputs influencing candidate generation or ordering

If any of those become desired, that is not a patch-level hardening change. It is a
new semantic release boundary.

## What is implemented now

Implemented trace fields and contracts:

- candidate source typing: `struct_conn`, `smarts_union`, `near_band`
- deterministic candidate ordering
- `candidate_order_hash`
- `struct_conn_status`
- `near_band_triggered`
- `proposal_policy_version`
- `semantic_mode = "trace-only-noop"`

These are sufficient for audit and replay provenance. They are not sufficient to claim
proposal-connected semantics.

## Conditions required before proposal-connected work may start

Proposal-connected Rule3 should not start until all of the following are true:

1. the input-normalization, benchmark-contract, and Rule3 ADR documents are fixed
2. benchmark, production, and CI-sized full fixtures are stable in test coverage
3. the intended semantic delta is written down before coding
4. a new policy version is allocated; `v29.trace-only.noop` must not be repurposed
5. replay artifacts needed to explain changed outcomes are enumerated up front
6. benchmark same-config acceptance criteria are defined for any expected collapse or non-collapse

Without those, a proposal-connected change would be under-specified.

## Minimum design requirements for a future proposal-connected phase

Any future design should answer, before implementation:

- which candidate sources become execution-significant
- whether ordering changes only trial order or also predicate eligibility
- how `near_band` transitions from trace field to execution input, if at all
- what new replay evidence must be written
- what same-config benchmark tests prove non-regression
- what cross-regime tests prove the taxonomy remains separated

## Required safeguards if the project proceeds to `v3.x`

Before merging proposal-connected Rule3 into a future `v3.x`, require at least:

- a new ADR revising this one
- a new semantic mode and policy version
- benchmark same-config regression coverage
- cross-regime guard coverage
- replay-audit additions for any new execution-significant Rule3 input
- an explicit statement about whether Rule3 remains outside CoreSCV or becomes part of object logic

## Consequence for current maintenance

For `v2.9.5`, the preferred work is:

- contract documentation
- CI promotion decisions
- long-run robustness and failure triage

It is not rational to advance Rule3 into proposal-connected logic before those are fixed,
because that would reintroduce ambiguity into the very boundaries that were just stabilized.
