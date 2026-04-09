# VN-05 Close Memo

Status: accepted
Date: 2026-04-09
Parent: `wp6_close_memo.md`, `verdict_record_schema_freeze.md`, `wp6_public_inclusion_decision_memo.md`

## Campaign Summary

- 30-run campaign summary is fixed by local proof at `outputs/wp6_campaign/campaign-30/campaign_summary.json`.
- `run_count = 30`
- `vn05_sidecar_invariant_30_green = true`
- `vn05_metrics_drift_30_green = true`
- `vn05_windows_30_green = true`
- `run_drift_digest_stable = true`

## Provenance

- probe run provenance: `outputs/wp6_campaign/probe-run`
- 30-run campaign provenance: `outputs/wp6_campaign/campaign-30`
- internal debug replay provenance: `outputs/wp6_campaign/direct-probe`

## Guarded State

- `all_internal_bundles_operator_inactive = true`
- `all_verdict_record_dual_write_non_authoritative = true`
- public inclusion is still not authorized

*End of document*
