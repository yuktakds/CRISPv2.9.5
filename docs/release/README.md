# Release Docs

`docs/release/` contains operational release and audit templates that are meant
to be reused during fixture drills, rehearsals, and release-candidate checks.

- `m2_authority_ops_reports.md`: rollback drill, rehearsal, and post-cutover monitoring report contract
- `release/evidence/keep_path_rc/<date>/campaign_index.json`: keep-path RC campaign evidence pack; RC candidate approval requires a green aggregate index under the current keep decision
- `release/evidence/keep_path_rc/<date>/release_packet_smoke_snapshot.json`: fixed release packet snapshot for end-to-end smoke and diff guard
