# v3-07 Rule3 / Catalytic Contract Freeze

Date: 2026-04-07  
Status: active for current sidecar scope

This note freezes the current `Path + Cap + Catalytic` sidecar contract without
claiming a full migration contract or full-channel verdict comparability.

It exists to make three things explicit:

- what the current sidecar is allowed to materialize
- what Catalytic is allowed to mean at the current milestone
- how operator-facing exploratory output must be labeled

## Scope

This freeze applies to the current `crisp/v3/` sidecar only:

- `PathEvidenceChannel`
- `CapEvidenceChannel`
- `CatalyticEvidenceChannel`
- `SCVBridge`
- `sidecar_run_record.json`
- `observation_bundle.json`
- `builder_provenance.json`
- `bridge_operator_summary.md`

This freeze does not authorize:

- full-channel bridge comparison
- full verdict comparability
- promotion criteria
- proposal-connected Rule 3
- same-pose style predicates
- CoreSCV reverse-flow
- taxonomy / comparison semantics redesign

Those remain deferred behind explicit ADR work.

## Rule 3 split at current scope

Current-sidecar Rule 3 handling is intentionally narrow.

- `anchoring` remains on the frozen rc2 line
- `catalytic` is sidecar-only observational evidence
- `catalytic` is evaluated from a read-only `evidence_core` snapshot
- `catalytic` currently reports a constraint-set observation, not a new object-logic predicate

Operational consequence:

- Catalytic must not be used to reinterpret rc2 verdicts
- Catalytic must not imply proposal-connected execution semantics
- Catalytic may be materialized and audited, but it remains exploratory

## Truth-source chain freeze

Current truth-source chains are:

- `path`: `pat_diagnostics` snapshot -> `PathEvidenceChannel.evaluate` -> `channel_evidence_path.jsonl` -> `SCVBridge.route` -> `observation_bundle.json`
- `cap`: `pair_features` snapshot -> `CapEvidenceChannel.evaluate` -> `channel_evidence_cap.jsonl` -> `SCVBridge.route` -> `observation_bundle.json`
- `catalytic`: `evidence_core` snapshot -> `CatalyticEvidenceChannel.evaluate` -> `channel_evidence_catalytic.jsonl` -> `SCVBridge.route` -> `observation_bundle.json`

For the current sidecar milestone:

- truth-source chains must remain label + digest based
- truth-source chains must remain reconstructable from Layer 0 / Layer 1 artifacts
- external outputs are not promoted to final truth sources just because they are present

## None / not-evaluated / applicability handling

The current sidecar must distinguish four cases.

### 1. Disabled

- channel opt-in is `false`
- `builder_status=disabled`
- no channel evidence artifact is materialized
- truth-source chain records a toggle stage only

### 2. Applicability-only

- input artifact is missing, unreadable, or a run-level gate fails
- channel returns `evidence=None`
- runner records `RunApplicabilityRecord`
- `observation_bundle.json` omits the channel
- `builder_status=applicability_only`

This is absence of evaluation, not a public `FAIL`.

### 3. Observation materialized

- channel returns `ChannelEvidence`
- `SCVBridge` routes it into `SCVObservation`
- `builder_status=observation_materialized`

### 4. Not comparable

- comparator coverage remains Path-only
- Cap / Catalytic materialization does not widen bridge comparability claims
- missing comparison coverage must stay explicit rather than inferred away

Channel-specific current rules:

- `path`: `goal_precheck` failure stays run-level applicability only
- `cap`: missing or unsupported `pair_features` stays applicability only
- `catalytic`: missing or unreadable `evidence_core` stays applicability only

## Forbidden scope freeze

The current Catalytic sidecar contract explicitly forbids:

- `proposal_connected_rule3`
- `same_pose_requirement`
- `corescv_reverse_flow`
- `taxonomy_redesign`

This prohibition is not cosmetic. It means:

- no execution-significant Rule 3 evolution is implied by current Catalytic artifacts
- no new witness-equivalence rule is introduced
- no shell diagnostic may flow back into CoreSCV object logic
- no benchmark / production or comparison vocabulary redesign may be smuggled in

## Operator-facing display rule

All rendered `v3` sidecar output must remain visibly exploratory.

Minimum current rule:

- show `semantic_policy_version`
- show `[exploratory]` in the visible operator-facing label
- keep rc2 verdicts primary and frozen
- keep v3 shadow content secondary
- do not present Cap / Catalytic as if they made full verdicts comparable

Current operator-facing surfaces in scope:

- `bridge_operator_summary.md`
- any future rendered summary derived from `sidecar_run_record.json`
- any future rendered summary derived from `builder_provenance.json`

Current claim boundary:

- `bridge_operator_summary.md` may describe Path-only partial comparison
- it must not imply that Cap / Catalytic are already part of a full migration comparator
- Cap / Catalytic channel presence is evidence-materialization status, not verdict-comparability status

## Inventory and frozen-boundary note

This freeze does not change the current conservative inventory rule.

- `v3_sidecar/` artifacts remain side-separated
- rc2 `output_inventory.json` remains frozen
- canonical sidecar enumeration remains `v3_sidecar/generator_manifest.json`

This is still an intentional deviation from rev.3 sidecar-inventory registration
for the sake of rc2 schema preservation.

## Still open after this freeze

The following remain open:

- full-channel migration contract
- full verdict comparability
- bridge promotion criteria
- proposal-connected Rule 3 ADR
- same-pose ADR
- CoreSCV reverse-flow ADR

This note closes the current sidecar boundary. It does not close the future semantic program.
