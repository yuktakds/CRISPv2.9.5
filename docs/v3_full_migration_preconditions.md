# v3 Full Migration Preconditions

Date: 2026-04-07  
Status: design-only precondition note  
Scope: conditions that must be satisfied before `v3` may claim anything beyond Path-only partial comparability

This note is not a migration contract implementation plan.
It exists to define the conditions that must be true before the current
`Path + Cap + Catalytic` sidecar may advance from:

- sidecar materialization
- Path-only partial comparison
- exploratory operator-facing summaries

to any stronger claim such as:

- full-channel migration contract
- full verdict comparability
- promotion criteria
- required CI gating for non-rc2 sidecar lanes

## Canonical references

Current authority for this note is distributed across:

- [CRISP_v3x_semantic_design_SOT_RC_rev1.md](CRISP_v3x_semantic_design_SOT_RC_rev1.md)
- [v3x_evidence_channel_kernel_architecture_rev3.1.md](v3x_evidence_channel_kernel_architecture_rev3.1.md)
- [v3x_bridge_ci_contracts.md](v3x_bridge_ci_contracts.md)
- [v3_05_bridge_drift_policy.md](v3_05_bridge_drift_policy.md)
- [v3_07_rule3_catalytic_contract_freeze.md](v3_07_rule3_catalytic_contract_freeze.md)

This note does not replace those documents. It summarizes the gating conditions
that must be met before a stronger migration claim is allowed.

## Current status snapshot

The current repository state should be read as:

- Path-first milestone complete
- Path-only partial comparator available
- Cap sidecar materialization available
- Cap provenance / replay contract available
- Catalytic sidecar-only observational channel available
- three-channel sidecar contract freeze available
- full migration contract still open
- full verdict comparability still open

## Non-goals

This note does not authorize:

- widening the current comparator scope
- changing rc2 public outputs
- changing `output_inventory.json`
- publishing v3 final verdicts
- mixing rc2 and v3 shadow verdicts into one operator summary
- promoting exploratory CI to required

## Preconditions

### P1. Comparable-channel promotion must be channel-owned and explicit

A channel may enter `comparable_channels` only when all of the following are true:

- the channel has an explicit rc2-side source inventory
- the channel has a channel-specific adapter coverage table
- missing-source behavior is frozen as `None`, `skip`, or explicit fallback, never silent inference
- channel projector fields needed for drift attribution are preserved without lossy collapse
- deterministic tests exist for adapter mapping, projector output, and replayable materialization

Current implication:

- `path` is the only channel allowed to participate in the current comparator scope
- `cap` and `catalytic` materialization does not by itself promote them into `comparable_channels`

### P2. Truth-source chains must be complete enough for replay and audit

Before full migration claims are allowed, each compared channel must have a stable,
reconstructable truth-source chain with:

- source label
- source digest
- source location kind
- builder identity
- projector identity
- observation artifact pointer

Additional rule:

- truth-source chains must be reconstructable from Layer 0 / Layer 1 artifacts
- external tool outputs or frozen rc2 artifacts are not promoted to unqualified final truth sources

Current implication:

- Path / Cap / Catalytic truth-source chains are materialized for sidecar audit
- this is necessary but not yet sufficient for full migration claims

### P3. Channel-level applicability semantics must be frozen before comparison widens

Each channel must explicitly distinguish:

- disabled
- applicability-only
- observation materialized
- not comparable

The meaning of these states must be stable at both builder and report level.

Current channel obligations:

- `path`: `goal_precheck` failure remains run-level applicability only
- `cap`: missing or unusable `pair_features` remains applicability only
- `catalytic`: missing or unreadable `evidence_core` remains applicability only

Full migration cannot proceed while any channel still conflates:

- absence of evaluation
- insufficient evidence
- public failure

### P4. Operator-facing mixed-summary prohibition must remain in force

Before full migration, operator-facing rendering must keep:

- rc2 verdicts primary
- v3 shadow content secondary
- `[exploratory]` visible on v3-rendered summaries
- `semantic_policy_version` always displayed

Additional guard:

- verdict match rate is `N/A` whenever full verdict comparability is absent
- Cap / Catalytic evidence materialization must not be displayed as if it implied full verdict comparability
- no mixed aggregate summary may combine rc2 primary verdicts with exploratory v3 content

### P5. Required vs exploratory CI promotion must remain gated

No new v3 sidecar lane may become required until the canonical bridge / CI contract
conditions are satisfied.

Minimum gating surface:

- channel contract ADR is complete
- sidecar invariants remain green
- metrics drift baseline is stable
- Windows CI stability is demonstrated
- rc2-frozen suite remains untouched and green

Current implication:

- Path comparator, Cap sidecar, and Catalytic sidecar lanes remain exploratory
- required / v3-sidecar-determinism is not a license to widen semantic claims

### P6. Channel-specific blockers must be closed separately

`path`

- full rc2 adapter coverage table must be frozen
- a full bridge consumer for Path semantics must exist
- final verdict comparability semantics must be defined

`cap`

- rc2 adapter inputs and truth-source equivalence must be frozen against `cap_batch_eval` and related provenance
- applicability semantics must be frozen for compareable cases
- comparator drift schema for Cap metrics and witnesses must be defined

`catalytic`

- the Rule 3 anchoring vs catalytic-frame disruption ADR must be complete
- the final catalytic-frame object and replay contract must be frozen
- proposal-connected Rule 3 must remain forbidden until separately authorized
- comparator drift schema for Catalytic observational evidence must be defined

### P7. Inventory and report authority must be explicit

Before full migration, the repo must explicitly decide:

- whether sidecar artifacts remain outside rc2 `output_inventory.json`
- how canonical operator-facing summaries enumerate sidecar outputs
- which filenames are canonical authority for bridge / CI / migration policy

Until that decision is frozen:

- `v3_sidecar/generator_manifest.json` remains the canonical sidecar inventory
- rc2 `output_inventory.json` remains untouched
- bridge / migration claims remain conservative

## Exit rule

The repository must continue to treat the comparator as `path_only_partial`
until all of `P1` through `P7` are satisfied for the channels being compared.

Operational reading:

- if only Path satisfies the conditions, keep the comparator Path-only
- if Cap or Catalytic materialize without satisfying the conditions, record them but do not promote comparability
- if any operator-facing surface would overclaim migration progress, freeze the change at the docs / design layer and do not implement

## Next design-only follow-up

The next legitimate design step after this note is a full migration contract ADR
that answers:

- what exact artifact set constitutes the canonical full migration boundary
- when `comparable_channels` may expand beyond `path`
- how final verdict comparability is computed without reinterpreting rc2 semantics
- what promotion criteria move a v3 lane from exploratory to required

That ADR should begin only after the preconditions in this note are individually addressed.
