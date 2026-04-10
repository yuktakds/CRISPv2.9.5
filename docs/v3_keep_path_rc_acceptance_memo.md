# v3 Keep-Path RC Acceptance Memo

Status: accepted
Date: 2026-04-09
Parent: `v3_keep_path_rc_roadmap.md`, `wp6_public_inclusion_decision_memo.md`, `adr_v3_11_m2_authority_transfer.md`
Scope: bind the current keep-path RC definition, validator green state, and M-2 ops evidence into one acceptance record.

## Decision

- keep-path RC is accepted as the current public-scope release candidate
- current keep decision is unchanged
- no widening is authorized
- no operator activation is authorized
- exploratory-lane work may continue, but required promotion is not authorized

## Current State

- current public scope and authority layering are defined in `v3_current_boundary.md`

## Evidence

- docs routing updated in `README.md`
- keep-path RC glossary fixed in `v3_keep_path_rc_roadmap.md`
- validator green:
  `pytest tests/v3/test_public_scope_validator.py tests/v29/test_keep_path_rc_validator.py -q`
  result: `7 passed`
- ops package test green:
  `pytest tests/v3/test_m2_ops.py -q`
  result: `4 passed`
- keep-path RC gate report:
  `release/evidence/keep_path_rc/2026-04-09/rc_gate_keep_path_report.json`
  result: `gate_passed = true`
- rollback drill report:
  `release/evidence/keep_path_rc/2026-04-09/m2_rollback_drill_report.json`
  result: `drill_passed = true`
- rehearsal report:
  `release/evidence/keep_path_rc/2026-04-09/m2_rehearsal_report.json`
  result: `rehearsal_passed = true`
- post-cutover monitoring report:
  `release/evidence/keep_path_rc/2026-04-09/m2_post_cutover_monitoring_report.json`
  result: `window_passed = true`

## Provenance

- fixture run provenance root:
  `outputs/keep_path_rc_acceptance/2026-04-09/monitoring/runs`
- evidence index:
  `release/evidence/keep_path_rc/2026-04-09/README.md`

## Boundary

- this memo does not authorize comparator-scope widening
- this memo does not authorize `catalytic` entry into `comparable_channels`
- this memo does not authorize operator-facing `v3_shadow_verdict`
- this memo does not authorize numeric operator-facing `verdict_match_rate`
- this memo does not authorize required-CI promotion
- automation alone remains insufficient for widening or requiredization

*End of document*
