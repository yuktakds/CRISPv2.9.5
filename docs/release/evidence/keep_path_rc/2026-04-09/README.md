# Keep-Path RC Ops Evidence Index

Date: 2026-04-09
Scope: fixed M-2 ops evidence set for the current keep-path RC acceptance.

## Reports

- `rc_gate_keep_path_report.json`
  result: `gate_passed = true`
- `campaign_index.json`
  result: `campaign_passed = true`
- `m2_rollback_drill_report.json`
  result: `drill_passed = true`
- `m2_rehearsal_report.json`
  result: `rehearsal_passed = true`
- `m2_post_cutover_monitoring_report.json`
  result: `window_passed = true`
- `release_packet_smoke_snapshot.json`
  result: fixed packet hash baseline for keep-path RC smoke
- `release_packet_smoke_report.json`
  result: `smoke_passed = true`

## Provenance

- run provenance root:
  `outputs/keep_path_rc_acceptance/2026-04-09/monitoring/runs`
- rollback drill source run:
  `outputs/keep_path_rc_acceptance/2026-04-09/monitoring/runs/run-01`
- rehearsal source runs:
  `outputs/keep_path_rc_acceptance/2026-04-09/monitoring/runs/run-01`
  `outputs/keep_path_rc_acceptance/2026-04-09/monitoring/runs/run-02`
- monitoring window:
  `run-01` through `run-30`
- campaign gate reports:
  `campaign_runs/run-01/rc_gate_keep_path_report.json` through
  `campaign_runs/run-30/rc_gate_keep_path_report.json`
- release packet source run:
  `outputs/keep_path_rc_acceptance/2026-04-09/monitoring/runs/run-01`

## Fixed Audit Points

- single keep-path RC gate artifact binds validator, docs routing, and ops evidence
- campaign index preserves run-level keep-scope conditions and Path-only metrics for every run
- rollback drill detected the injected `comparator_scope` mismatch in the same report
- rehearsal preserved normalized round-trip integrity
- post-cutover monitoring kept `authority_phase_m2_streak = true`
- post-cutover monitoring kept `dual_write_mismatch_zero_streak = true`
- post-cutover monitoring kept `operator_surface_inactive_streak = true`
- release packet smoke keeps `[exploratory]` labeling and `semantic_policy_version` visible while preserving `verdict_match_rate: N/A`

*End of document*
