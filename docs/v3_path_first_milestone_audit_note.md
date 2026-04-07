# v3 Path-First Milestone Audit Note

Date: 2026-04-07  
Status: Path-first milestone achieved, comparator / adapter work deferred

This note records what the first `crisp/v3/` sidecar batch does, what it does not
claim yet, and which items remain intentionally deferred.

## Satisfied invariants

- `crisp/v3/` is side-separated from `v29`; the only `v29` change is a default-off hook
  that starts after `replay_audit.json` has been written.
- `SCV` is the only component that emits `PASS` / `FAIL` / `UNCLEAR`.
- `ChannelEvidence` returns `EvidenceState` plus payload, never a verdict.
- `SCVBridge` is a routing shell only; it maps `SUPPORTED -> PASS`,
  `REFUTED -> FAIL`, `INSUFFICIENT -> UNCLEAR` and does not reinterpret payload semantics.
- `PathEvidenceChannel` is currently formalized only for `TUNNEL`.
- `goal_precheck` failure is treated as a run-level applicability diagnostic and does not
  become compound-level `FAIL` / `UNCLEAR`.
- `numeric_resolution_limited` maps to `INSUFFICIENT`.
- `blockage_ratio >= blockage_pass_threshold` maps to `SUPPORTED`.
- `blockage_ratio < blockage_pass_threshold` maps to `REFUTED`.
- `persistence_confidence` is recorded in payload / bridge metrics only and is not used as a gate.
- The sidecar emits `SCVObservationBundle` and related sidecar artifacts, but it does not
  claim a final verdict because current `crisp.scv.core` has no Path consumer.

## Sidecar stop criterion

The sidecar must stop immediately if it mutates any pre-existing rc2 output after the public
rc2 outputs have been finalized. The code path enforces this by computing rc2 output digests
before and after sidecar materialization and raising `SidecarInvariantError` on any drift.

Operational reading:

- if sidecar mode changes even one rc2 verdict-bearing artifact, stop
- if sidecar mode changes any retained rc2 artifact bytes after hook entry, stop
- `v3_sidecar/` is the only allowed write scope for the first batch

The corresponding regression guard lives in `tests/v3/test_sidecar_invariants.py` and
`tests/v29/test_v3_sidecar_hook.py`.

## Unverified items

- `PathChannelProjector` preserves the currently required PAT quantities
  (`blockage_ratio`, `witness_pose_id`, `obstruction_path_ids`,
  `apo_accessible_goal_voxels`, `feasible_count`, `persistence_confidence`), but
  quantitative completeness of a future `quantitative_metrics / exploration_slice`
  contract is not yet proven.
- `SCVObservationBundle` is emitted, but no bridge comparator, rc2 adapter, or
  Path consumer in `crisp.scv.core` exists yet. Final-verdict comparison therefore remains
  out of scope for this milestone.

## Explicitly deferred items

- bridge comparator design
- rc2 adapter design
- Path consumer in `crisp.scv.core`
- Cap / Catalytic channels
- canonical `v3.x` repo split and migration map refresh

## Inventory note

`v3_sidecar/` is intentionally not mixed into rc2 `output_inventory.json` in this first batch.
This is a deliberate minimal-implementation hold, not an accident.

Reason:

- it preserves the frozen rc2 inventory meaning
- it avoids quietly widening replay / operator expectations on the rc2 line
- canonical v3-sidecar inventory remains `v3_sidecar/generator_manifest.json` for now

Tradeoff:

- operator discoverability is lower until a later inventory policy explicitly freezes
  how `v3_sidecar/` should be registered

## Follow-on order

1. deterministic regeneration CI
2. Path fixture expansion
3. bridge comparator design
4. Cap / Catalytic channel work

