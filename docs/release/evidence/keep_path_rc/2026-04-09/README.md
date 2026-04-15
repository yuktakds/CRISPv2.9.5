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
- `keep_path_rc_history_report.json`
  result: `history_passed = true`
- `keep_path_rc_history_summary.md`
  result: hosted history remains non-authorizing and Path-only
- `keep_path_rc_hostile_audit_report.json`
  result: `audit_passed = true`
- `keep_path_rc_hostile_audit_summary.md`
  result: authorization boundary check remains green
- `keep_path_rc_freeze_manifest.json`
  result: fixed digest index for the closed keep-path RC bundle

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
- hosted history source:
  `hosted_history/hosted-run-01` through `hosted_history/hosted-run-03`
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
- hosted history kept `required_matrix_untouched_all_runs = true`
- hosted history kept `public_scope_widening_authorized_any_run = false`
- release packet smoke keeps `[exploratory]` labeling and `semantic_policy_version` visible while preserving `verdict_match_rate: N/A`
- hostile audit re-checks current authority, keep-scope, CI separation, and Path-only metric labeling without authorizing widening or required promotion
- freeze manifest records the fixed evidence locations and digests for replayable third-party audit

## Close Boundary

- `attic/docs/archive/v3_keep_path_rc_close_memo.md` closes the current keep-path RC bundle under the current public scope
- this close is not a full-migration declaration
- this close does not authorize comparator widening, operator activation, or required promotion

*End of document*
