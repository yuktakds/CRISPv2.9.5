# WP-4 Close Memo

Status: closed  
Date: 2026-04-09  
Parent: `adr_v3_10_full_migration_contract.md`, `wp4_wp5_audit_criteria.md`

---

## Closed Scope

WP-4 is closed for the current Path-only bridge implementation boundary.

Implemented and enforced:

1. shared mapping-status truth source for `scv_pat`, `scv_anchoring`, `scv_offtarget`
2. `required_scv_components_frozen()` guard-first activation check
3. `FULL_VERDICT_COMPARABLE` subset computation path
4. denominator resolution split:
   - `coverage_drift_rate`: all compounds
   - `applicability_drift_rate`: all compounds
   - `verdict_match_rate`: `FULL_VERDICT_COMPARABLE`
   - `verdict_mismatch_rate`: `FULL_VERDICT_COMPARABLE`
   - `path_component_match_rate`: `COMPONENT_VERDICT_COMPARABLE`
5. hard block preventing full-scope aggregation while `comparator_scope == "path_only_partial"`
6. `run_drift_report.json` materialization and manifest registration
7. stale authority wording describing `scv_anchoring=CANDIDATE` / `scv_offtarget=UNKNOWN` removed from current authority set

Current enforced result:

- `scv_pat = FROZEN`
- `scv_anchoring = FROZEN`
- `scv_offtarget = FROZEN`
- public comparator scope is still `path_only_partial`
- `full_verdict_computable = false` in current public bridge path
- `full_verdict_comparable_count = 0` in current public bridge path
- `verdict_match_rate = N/A`

Authority note:

- `wp1_wp2_channel_contracts_schema_freeze.md` and `adr_v3_10_full_migration_contract.md` are synchronized to the current mapping/source freeze
- pre-freeze wording is superseded and should not be cited as current authority

---

## Not Closed

WP-4 does not authorize full verdict comparability.

The following remain open:

- public full-scope comparator activation
- `v3_shadow_verdict` activation in operator-facing flow
- numeric `verdict_match_rate`

---

## Forward Risk

- Do not treat Catalytic Rule3A semantic narrowing as “must-match metrics” by default.
- Do not introduce hybrid or passthrough handling beyond the selected thin-wrapper source for `scv_offtarget`.
