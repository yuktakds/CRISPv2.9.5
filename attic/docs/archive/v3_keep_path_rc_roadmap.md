# v3 Keep-Path RC Roadmap

Status: accepted
Date: 2026-04-09
Parent: `adr_v3_10_full_migration_contract.md`, `adr_v3_11_m2_authority_transfer.md`, `wp6_public_inclusion_decision_memo.md`
Scope: define the current v3 keep-path RC as the current public-scope release candidate and separate it from full-migration completion.

## RC Definition

The current RC is the current public-scope release candidate:

- a public-scope release candidate
- current public scope is defined in `v3_current_boundary.md`

## Current Authority

The current authority set for this RC is:

- `adr_v3_10_full_migration_contract.md`
- `adr_v3_11_m2_authority_transfer.md`
- `verdict_record_schema_freeze.md`
- `wp6_public_inclusion_decision_memo.md`
- `comparable_channels_semantics.md`

## Current Keep Decision

The current keep decision is fixed as follows.

- keep current public scope unchanged (see `v3_current_boundary.md`)
- keep `Cap` and `Catalytic Rule3B` isolated as `[v3-only]`

## Archive Boundary

The following are not current RC authority.

- archived close memos under `archive/close_memos/`
- superseded pre-M-2 fragments
- historical Path-first supporting notes that still describe `sidecar_run_record.json` as canonical Layer 0 authority

If a document conflicts with this RC definition, the current authority set above wins.

*End of document*
