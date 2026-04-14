# v3 Current Boundary (Canonical)

Status: canonical boundary + guards  
Date: 2026-04-14  
Scope: current frozen boundary and guard conditions. **This is the only document that restates the current boundary.**

## Authority & Inventory

- Canonical Layer 0 authority: `verdict_record.json` (M-2 accepted).
- Backward-compatible mirror: `sidecar_run_record.json`.
- Sidecar inventory + replay contract: `v3_sidecar/generator_manifest.json`.
- rc2 inventory authority: `output_inventory.json` (unchanged by v3 sidecar).

## Current Public Scope (Frozen)

- keep-path RC close has been superseded by the accepted RP-1 widening and landed RP-1I implementation.
- RP-2 validation-only gate and full-scope denominator prep have also landed.
- RP-3 activation / promotion decisions, RP-4 operator-surface materialization, and RP-5 release-blocking consolidation have landed without widening the boundary.
- `comparator_scope = path_and_catalytic_partial`
- `comparable_channels = ["path", "catalytic"]`
- comparable component keys are `path`, `catalytic_rule3a`
- v3-only retained evidence outside comparable component participation: `cap`, `catalytic_rule3b`
- internal full-SCV coverage and denominator readiness may be audited cross-artifact
- none of the above activates operator-facing verdict-level rendering by itself

## Operator Surface Guards

- `v3_shadow_verdict` is inactive.
- `verdict_match_rate` / `verdict_mismatch_rate` are `None` or `N/A` while operator-facing full verdict comparability remains unactivated.
- v3 operator sections must be labeled `[exploratory]` and rendered as secondary to rc2 primary.
- Mixed rc2/v3 summaries are forbidden.
- RP-5 may escalate forbidden-surface leakage or cross-artifact mismatch to run failure and artifact finalization refusal, but it does not activate stronger operator-facing claims.

## Failure Semantics

- exit code `0`: run completed without forbidden-surface or cross-artifact hard blocks; advisory promotion findings may still be present.
- exit code `1`: v3 gate violation or cross-artifact mismatch; sidecar finalization is refused and CI/release may be blocked according to the recorded gate state.
- exit code `2`: non-gate execution error outside the RP-5 release-blocking contract.
- advisory and blocking promotion lanes remain distinct; exploratory/advisory failure alone does not change the current public boundary.

## Canonical Invariants

- `cap` must not appear in `comparable_channels`.
- If `catalytic` appears in `comparable_channels`, the only comparable component is `catalytic_rule3a`.
- Rule3B remains v3-only evidence and must not appear in `component_matches`.
- RP-2 readiness evidence does not authorize operator-facing activation or required promotion.

## Human Decision Boundaries

- Activating operator-facing `v3_shadow_verdict`
- Making `verdict_match_rate` / `verdict_mismatch_rate` numeric on the operator surface
- Promoting exploratory CI lanes to required
- Any stronger public claim beyond the current `path_and_catalytic_partial` partial scope
- Any change to authority layering (Layer 0 / Layer 1 roles or canonical artifacts)

## Canonical Guard Sources

- Code guards: `crisp/v3/report_guards.py`, `crisp/v3/public_scope_validator.py`
- Authority decisions: `adr_v3_10_full_migration_contract.md`, `adr_v3_11_m2_authority_transfer.md`
- Public-scope semantics: `comparable_channels_semantics.md`, `v3_catalytic_public_representation_freeze.md`, `v3_scope_atomics_definition.md`

## Change Control

- Other documents must reference this file instead of restating current boundary or guard conditions.
- Any boundary change beyond this state requires an explicit, accepted decision record.
