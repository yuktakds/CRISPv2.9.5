# VN-06 M-1 Close Memo

Status: accepted
Date: 2026-04-09
Parent: `verdict_record_schema_freeze.md`, `vn05_close_memo.md`, `wp6_public_inclusion_decision_memo.md`

## Decision

- VN-06 M-1 is closed for `verdict_record.json` schema freeze, M-1 dual-write authority checks, and M-1 soak proof.
- VN-06 full closure is not claimed here.
- M-2 authority transfer remains a separate decision.
- `sidecar_run_record.json` remains the current canonical Layer 0 authority.
- `verdict_record.json` remains non-authoritative.
- public bridge inclusion is still not authorized.

## Window Provenance

- probe-run provenance: `outputs/vn06_campaign/2026-04-09/probe-run`
- 30-run soak provenance: `outputs/vn06_campaign/2026-04-09/campaign-30`
- per-run `vn06_readiness.json` archive: `outputs/vn06_campaign/2026-04-09/campaign-30/vn06_readiness_payloads`
- window history: `outputs/vn06_campaign/2026-04-09/campaign-30/vn06_readiness_window.json`
- campaign summary: `outputs/vn06_campaign/2026-04-09/campaign-30/campaign_summary.json`

## Fixed Results

- `window_is_consecutive = true`
- `same_semantic_policy_version = true`
- `same_vn06_readiness_schema = true`
- `same_verdict_record_schema_requirement = true`
- `bridge_comparator_disabled_run_count = 0`
- `dual_write_mismatch_zero_all_runs = true`
- `schema_complete_all_runs = true`
- `manifest_registration_complete_all_runs = true`
- `operator_surface_never_active = true`
- `authority_transfer_not_yet_executed_all_runs = true`
- `soak_window.window_passed = true`

## Audit Points

- The 30-run window is consecutive: `run-01` through `run-30`.
- All runs use the same `semantic_policy_version`, `vn06_readiness` schema, and `verdict_record` schema requirement.
- No bridge-comparator-disabled run is counted as an M-1 soak candidate.
- Operator-facing output never activates during the window.

## Boundary

- M-1 soak success does not authorize M-2 cutover by itself.
- authority transfer still requires human explicit decision after the full trigger set is satisfied.

*End of document*
