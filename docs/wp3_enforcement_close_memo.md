# WP-3 Close Memo

Status: closed  
Date: 2026-04-09  
Parent: `adr_v3_10_full_migration_contract.md`, `comparable_channels_semantics.md`, `wp1_wp2_channel_contracts_schema_freeze.md`

---

## Closed Scope

WP-3 enforcement is closed for the current Path-only bridge scope.

The following points are now enforced in code and regression tests:

1. `comparable_channels = ["path"]` remains fixed for current public bridge scope.
2. Cap / Catalytic materialization is separated as `v3_only_evidence_channels` and does not enter `component_matches` or match-rate aggregation.
3. `channel_lifecycle_states` is recorded only as the primary 3-value lifecycle set:
   - `disabled`
   - `applicability_only`
   - `observation_materialized`
   Derived `NOT_COMPARABLE` is report-level only and is not persisted as a primary stored enum.
4. Cross-artifact consistency checking hard-blocks drift across:
   - `sidecar_run_record.json`
   - `bridge_comparison_summary.json`
   - `bridge_operator_summary.md`
5. Regression coverage for this enforcement chain is green: `53 tests passed`.

---

## Guardrail For WP-4

WP-4 must not treat current Path-only semantics as if full verdict comparability already existed.

- `scv_anchoring` remains `CANDIDATE`
- `scv_offtarget` remains `UNKNOWN`
- full-SCV denominator and `FULL_VERDICT_COMPARABLE` aggregation must stay gated behind explicit non-hybrid guards
- full verdict comparability must remain absent until the ADR-defined prerequisites are satisfied

This memo closes enforcement for WP-3 only. It does not authorize WP-4 scope widening by inference.
