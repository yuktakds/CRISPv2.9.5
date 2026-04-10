# v3 Current Boundary (Canonical)

Status: canonical boundary + guards  
Date: 2026-04-10  
Scope: current frozen boundary and guard conditions. **This is the only document that restates the current boundary.**

## Authority & Inventory

- Canonical Layer 0 authority: `verdict_record.json` (M-2 accepted).
- Backward-compatible mirror: `sidecar_run_record.json`.
- Sidecar inventory + replay contract: `v3_sidecar/generator_manifest.json`.
- rc2 inventory authority: `output_inventory.json` (unchanged by v3 sidecar).

## Current Public Scope (Frozen)

- keep-path RC is closed under the current public scope
- `comparator_scope = path_only_partial`
- `comparable_channels = ["path"]`
- v3-only evidence channels: `cap`, `catalytic`
- Any widening of `comparator_scope` or `comparable_channels` requires explicit human decision.

## Operator Surface Guards

- `v3_shadow_verdict` is inactive.
- `verdict_match_rate` / `verdict_mismatch_rate` are `None` or `N/A` while full verdict comparability is absent.
- v3 operator sections must be labeled `[exploratory]` and rendered as secondary to rc2 primary.
- Mixed rc2/v3 summaries are forbidden.

## Canonical Invariants

- If `catalytic` ever appears in `comparable_channels`, the only comparable component is `catalytic_rule3a`. Rule3B remains v3-only evidence and must not appear in `component_matches`.

## Human Decision Boundaries

- Widening `comparator_scope`
- Widening `comparable_channels`
- Activating `v3_shadow_verdict`
- Making `verdict_match_rate` / `verdict_mismatch_rate` numeric
- Promoting exploratory CI lanes to required
- Any change to authority layering (Layer 0 / Layer 1 roles or canonical artifacts)

## Canonical Guard Sources

- Code guards: `crisp/v3/report_guards.py`, `crisp/v3/public_scope_validator.py`
- Authority decisions: `adr_v3_10_full_migration_contract.md`, `adr_v3_11_m2_authority_transfer.md`
- Public-scope keep decision: `wp6_public_inclusion_decision_memo.md`

## Change Control

- Other documents must reference this file instead of restating current boundary or guard conditions.
- Any boundary change requires an explicit, accepted decision record.
