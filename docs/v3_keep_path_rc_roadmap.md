# v3 Keep-Path RC Roadmap

Status: accepted
Date: 2026-04-09
Parent: `adr_v3_10_full_migration_contract.md`, `adr_v3_11_m2_authority_transfer.md`, `wp6_public_inclusion_decision_memo.md`
Scope: define the current v3 keep-path RC as a public-scope release candidate and separate it from full-migration completion.

## RC Definition

The current RC is:

- a public-scope release candidate
- `comparator_scope = path_only_partial`
- `comparable_channels = ["path"]`
- `verdict_record.json` canonical at Layer 0
- `sidecar_run_record.json` retained as the backward-compatible mirror
- operator-facing `v3_shadow_verdict` inactive
- operator-facing `verdict_match_rate` fixed to `N/A`

The current RC is not:

- a full-migration-ready declaration
- a public full-SCV inclusion decision
- a comparator-scope widening decision
- a channel-widening decision

## Current Authority

The current authority set for this RC is:

- `adr_v3_10_full_migration_contract.md`
- `adr_v3_11_m2_authority_transfer.md`
- `verdict_record_schema_freeze.md`
- `wp6_public_inclusion_decision_memo.md`
- `comparable_channels_semantics.md`

## Current Keep Decision

The current keep decision is fixed as follows.

- keep `comparator_scope = path_only_partial`
- keep `comparable_channels = ["path"]`
- keep operator-facing `v3_shadow_verdict` inactive
- keep operator-facing `verdict_match_rate = N/A`
- keep `Cap` outside `comparable_channels`
- keep `Cap` and `Catalytic Rule3B` isolated as `[v3-only]`

## Pending Reopen Path

The following remain pending and are not part of the current RC.

- reopening comparator scope beyond `path_only_partial`
- adding `catalytic` to `comparable_channels`
- activating operator-facing `v3_shadow_verdict`
- activating numeric operator-facing `verdict_match_rate`
- defining a non-ambiguous public representation for `Catalytic Rule3A comparable / Rule3B v3-only`

Any reopen path requires:

- explicit human decision in docs / merged PR
- atomic scope and comparability change
- reuse of ADR-V3-11 rollback expectations
- continued exclusion of `Cap` from `comparable_channels`

## Archive Boundary

The following are not current RC authority.

- archived close memos under `archive/close_memos/`
- superseded pre-M-2 fragments
- historical Path-first supporting notes that still describe `sidecar_run_record.json` as canonical Layer 0 authority

If a document conflicts with this RC definition, the current authority set above wins.

*End of document*
