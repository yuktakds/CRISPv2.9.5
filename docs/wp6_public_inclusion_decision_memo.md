# WP-6 Public Inclusion Decision Memo

Status: accepted
Date: 2026-04-09
Parent: `adr_v3_10_full_migration_contract.md`, `wp4_wp5_audit_criteria.md`, `archive/close_memos/wp4_close_memo.md`, `archive/close_memos/wp5_close_memo.md`, `adr_v3_11_m2_authority_transfer.md`
Scope: WP-6D は public bridge inclusion を yes/no で閉じ、current state と guard を固定する。

## Current State After M-2

- `verdict_record.json` is canonical Layer 0 authority.
- `sidecar_run_record.json` is the backward-compatible mirror.
- operator-facing surface is inactive.
- `output_inventory.json` is unchanged and remains rc2 authority.

## Inclusion Decision

- comparator_scope: keep `path_only_partial`
- comparable_channels: keep `["path"]`
- `v3_shadow_verdict`: inactive
- `verdict_match_rate`: `N/A`

This memo closes the current public inclusion decision as `keep`, not `widen`.

## Guard If `keep`

- no operator activation
- no scope widening
- no `comparable_channels` widening
- keep `[exploratory]` labeling on v3 operator surfaces
- `Catalytic Rule3A` mapping/source freeze does not authorize public comparable inclusion
- `Cap` remains outside `comparable_channels`
- `Cap` and `Catalytic Rule3B` remain `[v3-only]`

## Guard If `widen`

- explicit human decision is required
- rollback path must reuse `adr_v3_11_m2_authority_transfer.md`
- no `Cap` in `comparable_channels`
- operator surface activation may occur only after the scope change is separately committed
- `comparator_scope` widening and `comparable_channels` widening must be atomic
- catalytic public comparable representation must be defined explicitly before activation

## Boundary

- internal full-SCV readiness alone does not authorize public inclusion
- convenience 実装で hybrid passthrough を入れて `scv_offtarget` 未確定経路を再導入してはならない
- pre-freeze fragments are superseded and non-authoritative

*End of document*
