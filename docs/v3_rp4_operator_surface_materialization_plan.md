# v3 RP-4 Operator Surface Materialization Plan

Status: closed  
Date: 2026-04-14  
Parent: `v3_current_boundary.md`, `v3_rp3_activation_decision_surface.md`, `v3_rp3_promotion_decision_surface.md`, `adr_v3_10_full_migration_contract.md`  
Scope: RP-4 close memo for operator-surface gate wiring and derived machine-readable suppression / promotion state. Boundary is unchanged.

---

## Closed Scope

RP-4 is closed as the stage that materializes RP-3 activation and promotion gates into operator-facing rendering and derived sidecar artifacts.

Implemented and enforced:

1. `bridge_operator_summary.md` now renders through RP-3 activation gating rather than implicit field formatting alone
2. `v3_shadow_verdict` is renderable only when activation is accepted, all VN gates are satisfied, and `full_verdict_computable == true`
3. numeric `verdict_match_rate` / `verdict_mismatch_rate` are renderable only when numeric activation is accepted, shadow-verdict rendering is already allowed, and the denominator contract is satisfied
4. `required_ci_candidacy_report.json` remains `[exploratory]` and now carries by-reference PR-01 through PR-06 promotion-gate payload as the operator-facing promotion surface
5. `operator_surface_state.json` is emitted as a derived Layer 1 artifact and mirrored under `sidecar_run_record.json.bridge_diagnostics.operator_surface_state`
6. suppression reasons and promotion-gate outcomes are machine-readable and auditable without changing Layer 0 authority
7. mixed rc2/v3 aggregate summaries, Cap comparable participation, and Rule3B comparable participation remain hard-blocked

RP-4 closed rendering / hardening only. It did not widen scope, change authority layering, or increase the semantic strength of the public claim surface.

---

## Current Enforced Result

Current boundary remains exactly the boundary defined in `v3_current_boundary.md`.

Still true after RP-4:

- `comparator_scope == "path_and_catalytic_partial"`
- `comparable_channels == ["path", "catalytic"]`
- public comparable component keys remain `path` and `catalytic_rule3a`
- `cap` remains outside `comparable_channels`
- `catalytic_rule3b` remains `[v3-only]` and must not appear in `component_matches`
- rc2 remains primary and v3 remains `[exploratory] secondary`
- `path_component_match_rate` and `catalytic_rule3a` component status remain component-level indicators, not verdict proxies

Operator surface is now gate-aware, but stronger claims did not increase:

- accepted decision state alone does not render verdict-level v3 content
- unmet runtime gate state suppresses rendering
- suppression is rendered as `N/A` or absent on the operator surface and recorded machine-readably
- required promotion is still not auto-authorized
- current partial-scope component metrics are still not reinterpreted as full-verdict comparability

---

## Materialized Surfaces

### Operator-facing

Implemented:

- `bridge_operator_summary.md`
- `[exploratory]` required-CI candidacy surface carried by `required_ci_candidacy_report.json`

Explicitly not materialized by RP-4:

- `eval_report.json`
- `qc_report.json`
- `collapse_figure_spec.json`

Those registry entries remain untouched as generic guarded-surface definitions. RP-4 did not expand them into new active operator surfaces.

### Machine-readable derived state

RP-4 records derived, non-authoritative state in:

- `operator_surface_state.json`
- `sidecar_run_record.json.bridge_diagnostics.operator_surface_state`
- `sidecar_run_record.json.bridge_diagnostics.operator_surface_state_artifact`

At minimum, the derived state records:

- `activation_decisions`
- `vn_gate_state`
- `full_verdict_computable`
- `denominator_contract_satisfied`
- `suppressed_surfaces`
- `promotion_gate_results`

This state is explanatory / derived only. It does not change the canonical authority role of `verdict_record.json`, `sidecar_run_record.json`, `generator_manifest.json`, or `output_inventory.json`.

---

## Cross-Artifact Meaning After Close

RP-4 now guarantees the following operator-safety properties:

1. operator rendering actually uses RP-3 gate logic instead of ad hoc local conditions
2. runtime-unmet activation state suppresses operator-facing shadow-verdict and numeric-rate rendering
3. suppression reasons are machine-readable and survive into sidecar diagnostics
4. promotion-gate payload remains by-reference to ADR PR-01 through PR-06
5. Cap / Rule3B leakage and mixed summary generation remain hard-blocked
6. activation and promotion remain separate surfaces even when both are visible in the same sidecar output family

---

## Still Out of Scope

RP-4 does not authorize:

- any `comparator_scope` change
- any `comparable_channels` change
- Cap comparable participation
- Rule3B comparable participation
- Layer 0 / Layer 1 authority redesign
- `output_inventory.json` mutation
- required-matrix mutation
- stronger public claim wording than the current accepted boundary
- removal of `[exploratory]`
- mixed rc2/v3 aggregate summaries
- treating component-level indicators as verdict-level indicators
- full migration closure

---

## Isolation Note

The order-only file `attic/docs/archive/v3_reopen_path_implementation_plan.md` is no longer needed as an active root doc after RP-4 close. It should be treated as an archived trace document rather than current authority.

---

*End of document*
