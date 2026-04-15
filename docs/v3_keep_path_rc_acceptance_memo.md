# v3 Keep-Path RC Acceptance Memo

Status: frozen compatibility reference
Date: 2026-04-15
Parent: `v3_current_boundary.md`, `release/evidence/keep_path_rc/2026-04-09/README.md`, `attic/docs/archive/v3_keep_path_rc_acceptance_memo.md`
Scope: preserve the fixed keep-path RC evidence-family contract consumed by the
offline keep-path gate and hostile-audit tooling. This file is not the current
public-scope boundary and does not reopen keep-path RC as the current repo
state.

This file must not restate, replace, or override the current boundary. Only
`v3_current_boundary.md` may do that.

## Compatibility Decision

- keep-path RC is accepted as the current public-scope release candidate within
  the frozen keep-path RC evidence family
- no widening is authorized
- no operator activation is authorized
- required promotion is not authorized by this compatibility memo
- automation alone remains insufficient for widening or requiredization

## Evidence Family

- `release/evidence/keep_path_rc/2026-04-09/rc_gate_keep_path_report.json`
- `release/evidence/keep_path_rc/2026-04-09/m2_rollback_drill_report.json`
- `release/evidence/keep_path_rc/2026-04-09/m2_rehearsal_report.json`
- `release/evidence/keep_path_rc/2026-04-09/m2_post_cutover_monitoring_report.json`

## Current Repo Boundary

The current repo boundary is defined only in `v3_current_boundary.md`.

This compatibility memo exists so the frozen keep-path RC evidence bundle
remains replayable and auditable after the repo-level current scope advanced to
`path_and_catalytic_partial`.

*End of document*
