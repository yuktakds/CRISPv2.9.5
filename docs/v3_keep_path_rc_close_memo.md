# v3 Keep-Path RC Close Memo

Status: accepted
Date: 2026-04-09
Parent: `v3_keep_path_rc_roadmap.md`, `v3_keep_path_rc_acceptance_memo.md`, `wp6_public_inclusion_decision_memo.md`, `release/evidence/keep_path_rc/2026-04-09/keep_path_rc_hostile_audit_report.json`
Scope: close the keep-path RC track under the current public scope and freeze the acceptance evidence bundle.

## Decision

- the keep-path RC bundle is complete under the current public scope
- the current public-scope keep decision remains closed as `keep`
- `verdict_record.json` remains canonical Layer 0 authority
- `sidecar_run_record.json` remains the backward-compatible mirror
- `output_inventory.json` remains unchanged rc2 authority

This close applies only to the current public-scope keep-path track.
It is not a full-migration declaration, not a full-verdict comparability declaration, and not a reopen-path authorization.

## Frozen Bundle

The closed bundle consists of:

- current routing and authority docs in `README.md`, `v3_keep_path_rc_roadmap.md`, `v3_keep_path_rc_acceptance_memo.md`, and `wp6_public_inclusion_decision_memo.md`
- M-2 ops evidence:
  `m2_rollback_drill_report.json`, `m2_rehearsal_report.json`, `m2_post_cutover_monitoring_report.json`
- keep-path RC gate artifact:
  `release/evidence/keep_path_rc/2026-04-09/rc_gate_keep_path_report.json`
- keep-path campaign artifact:
  `release/evidence/keep_path_rc/2026-04-09/campaign_index.json`
- keep-path release packet smoke artifacts:
  `release/evidence/keep_path_rc/2026-04-09/release_packet_smoke_snapshot.json`,
  `release/evidence/keep_path_rc/2026-04-09/release_packet_smoke_report.json`
- hosted history evidence:
  `release/evidence/keep_path_rc/2026-04-09/keep_path_rc_history_report.json`
- hostile audit evidence:
  `release/evidence/keep_path_rc/2026-04-09/keep_path_rc_hostile_audit_report.json`
- freeze manifest:
  `release/evidence/keep_path_rc/2026-04-09/keep_path_rc_freeze_manifest.json`

## What Is Closed

- current public-scope keep-path RC definition
- current keep decision:
  `comparator_scope = path_only_partial`,
  `comparable_channels = ["path"]`,
  `v3_shadow_verdict = None`,
  operator-facing `verdict_match_rate = N/A`
- current authority / inventory boundary:
  `verdict_record.json` canonical, `sidecar_run_record.json` mirror, `output_inventory.json` unchanged
- current exploratory hosted evidence pack and hostile audit boundary checks

## What Remains Open

- full migration
- full verdict comparability
- comparator-scope widening
- `comparable_channels` widening
- public inclusion of `catalytic`
- operator-facing activation of `v3_shadow_verdict`
- numeric operator-facing `verdict_match_rate`
- required-CI promotion

## Boundary

- `path_component_match_rate` remains a Path-only component metric and is not a full verdict proxy
- `Cap` remains outside `comparable_channels`
- `Cap` and `Catalytic` remain observational / `[v3-only]` surfaces under the current public scope
- automation alone remains insufficient for widening, activation, or required promotion

*End of document*
