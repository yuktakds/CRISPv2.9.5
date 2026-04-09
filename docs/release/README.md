# Release Docs

`docs/release/` contains operational release and audit templates that are meant
to be reused during fixture drills, rehearsals, and release-candidate checks.

- `m2_authority_ops_reports.md`: rollback drill, rehearsal, and post-cutover monitoring report contract
- `release/evidence/keep_path_rc/<date>/campaign_index.json`: keep-path RC campaign evidence pack; RC candidate approval requires a green aggregate index under the current keep decision
- `release/evidence/keep_path_rc/<date>/release_packet_smoke_snapshot.json`: fixed release packet snapshot for end-to-end smoke and diff guard
- `.github/workflows/v3-keep-path-rc-exploratory.yml`: hosted Windows `[exploratory]` lane that regenerates `rc_gate_keep_path_report.json`, `campaign_index.json`, and `release_packet_smoke_report.json` as CI artifacts; it is not part of the required matrix
- `tests/v3/fixtures/keep_path_rc_ci/runs`: fixed CI-sized run fixtures consumed by the hosted keep-path RC exploratory lane
- `release/evidence/keep_path_rc/<date>/keep_path_rc_history_report.json`: harvested hosted history evidence; non-authorizing and limited to keep-path stability facts
- `release/evidence/keep_path_rc/<date>/keep_path_rc_history_summary.md`: human-readable hosted history summary that must continue to state that `path_component_match_rate` is not a full verdict proxy
- `release/evidence/keep_path_rc/<date>/keep_path_rc_hostile_audit_report.json`: machine-audited hostile check that the current keep-path RC bundle does not cross authorization boundaries
- `release/evidence/keep_path_rc/<date>/keep_path_rc_hostile_audit_summary.md`: human-readable hostile-audit summary for third-party review
