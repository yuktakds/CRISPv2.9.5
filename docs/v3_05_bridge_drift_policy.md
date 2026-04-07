# v3-05 Bridge Drift Policy

Date: 2026-04-07  
Status: active design note for the path-only bridge comparator milestone

This note defines what the current bridge comparator is allowed to claim and what it
must keep out of scope while `v3` remains a sidecar on the `v2.9.5` line.

## Public claim

The current implementation is a `path_only_partial` bridge comparator.
It is not a full semantic drift comparator and it does not publish a final verdict drift.

Required operator-facing interpretation:

- `comparison_scope=path_only_partial`
- `verdict_comparability=not_comparable` or `partially_comparable`
- no claim that full-channel verdict drift has been computed
- no claim that rc2 meaning has been reinterpreted

This keeps the comparator in an audit role rather than a second evaluator role.

## Responsibility split

`RC2Adapter`

- converts rc2-side path observations into the bridge format
- does not evaluate, promote, or reinterpret semantics
- owns field binding when rc2 and `v3` names differ

`SCVBridge`

- converts `ChannelEvidence` into `SCVObservationBundle`
- remains routing-only
- does not compare or re-evaluate

`BridgeComparator`

- decides comparability status
- extracts drift records
- generates explanatory output
- does not publish or override final verdicts

## Path-only adapter coverage rule

The current adapter is intentionally path-only. That means missing channels are a coverage gap,
not evidence that no drift exists.

For Path comparison, the adapter should preserve or explicitly mark absence for at least:

- `goal_precheck_passed`
- `goal_precheck_reason`
- `supported_path_model`
- `apo_accessible_goal_voxels`
- `goal_voxel_count`
- `blockage_ratio` or `max_blockage_ratio`
- `numeric_resolution_limited`
- `feasible_count`
- `witness_pose_id` or equivalent witness identity
- `obstruction_path_ids`
- `path_family`

If a source field is not yet mapped, the comparator must record that as coverage or structural
drift. It must not quietly collapse the gap into "no drift".

This is the operational consequence of rev.3 `FB-BRIDGE-01`: if projector / bridge compression
hides drift-relevant information, metrics must be extended before stronger comparability claims
are made.

## Drift taxonomy

The path-only comparator uses four first-class drift kinds:

- `coverage_drift`
- `metrics_drift`
- `witness_drift`
- `applicability_drift`

`applicability_drift` must remain independent from `metrics_drift`.

Reason:

- `goal_precheck` failure is a run-level applicability separation, not a compound-level metric mismatch
- `PAT_NOT_EVALUABLE` style handling must not be folded into quantitative disagreement
- v4.3.2 treats run-level applicability and compound-level public state as separate concerns

If one side reports a run-level applicability record and the other side does not, the comparator
must emit `applicability_drift` even when all available quantitative fields happen to match.

## Comparability contract

The current bridge comparator is allowed to report:

- channel coverage
- structural drift
- metric drift
- witness drift
- run-level applicability drift

It is not allowed to report:

- full final-verdict drift
- promotion decisions
- object-logic changes to rc2
- taxonomy or comparison semantics redesign

Those remain blocked on:

- fuller rc2 adapter coverage
- a Path consumer in `crisp.scv.core` or equivalent full-channel bridge consumer
- explicit ADR work for any semantic-policy expansion

## Comparator header contract

Every operator-facing bridge report should surface a small comparability header.

Minimum fields:

- `semantic_policy_version`
- `comparator_scope`
- `verdict_comparability`
- `comparable_channels`
- `rc2_policy_version` when known

For the current milestone, the expected public header is:

- `comparator_scope=path_only_partial`
- `verdict_comparability=not_comparable` or `partially_comparable`

Do not silently upgrade this to a full-bridge claim while the comparator remains Path-only.

If the report format exposes a verdict match rate, it must be rendered as `N/A` when either:

- there is no shadow-side final verdict
- there are zero comparable runs

Do not coerce that condition to `0.0`; the absence of comparability is different from a zero match rate.

## Artifact and inventory policy

Comparator artifacts remain sidecar-separated for now:

- `bridge_comparison_summary.json`
- `bridge_drift_attribution.jsonl`
- `bridge_operator_summary.md`

These artifacts are intentionally not mixed into rc2 `output_inventory.json` on the
`v2.9.5` line. This continues the same conservative deviation already documented for
other `v3_sidecar/` artifacts.

Reason:

- rc2 inventory schema stays frozen
- exploratory comparator outputs are kept visibly separate from frozen operator artifacts

Tradeoff:

- discoverability is weaker than rev.3 G.8 sidecar-inventory registration would prefer

Mitigation:

- keep this deviation documented
- keep pointers in the audit note and operator summary
- revisit inventory registration only when the replay / operator contract is explicitly frozen

## Exit criteria for stronger claims

Do not upgrade beyond `path_only_partial` until all of the following are true:

1. rc2 adapter coverage for compared fields is explicit and tested
2. applicability drift remains independently attributable
3. comparator output is deterministic across repeat runs
4. operator-facing reports show `semantic_policy_version`
5. full-channel comparison semantics are defined separately from exploratory drift logging
