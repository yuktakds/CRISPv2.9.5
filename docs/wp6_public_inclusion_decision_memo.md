# WP-6 Public Inclusion Decision Memo

Status: accepted
Date: 2026-04-09
Parent: `adr_v3_10_full_migration_contract.md`, `wp4_wp5_audit_criteria.md`, `wp4_close_memo.md`, `wp5_close_memo.md`
Scope: WP-6D は public inclusion の実施ではなく、internal readiness と公開判断条件を固定する。

## Current Internal Readiness

- `shadow_stability_campaign.json` を追加し、30-run window の sidecar invariant / metrics_drift / Windows streak / `run_drift_report.json` digest 安定を評価可能にした。
- `verdict_record.json` は M-1 dual-write として追加したが、authority はなお `sidecar_run_record.json` に残る。
- `internal_full_scv_observation_bundle.json` は internal-only artifact として生成され、Path / `scv_anchoring` / `scv_offtarget` の deterministic replay を検証できる。
- operator-facing `v3_shadow_verdict` と `verdict_match_rate` は依然 inactive であり、public comparator scope は `path_only_partial` のままである。

## Remaining Blockers To Public Inclusion

- 30-run shadow stabilization campaign を実 run history で green にすること。
- `verdict_record.json` の authority transfer を完了し、VN-06 を close すること。
- `comparator_scope` widening と `comparable_channels` widening を atomic に扱う public decision を先に確定すること。
- catalytic を channel-level comparable と表現するのか、`Rule3A comparable / Rule3B v3-only` の mixed-channel 表現を別途定義するのかを曖昧なまま残さないこと。

## Current Decision

- public inclusion は未承認のまま据え置く。
- `comparator_scope` は `path_only_partial` から widen しない。
- `Catalytic Rule3A` の mapping/source freeze は public comparable inclusion authorization を意味しない。
- `Cap` と `Catalytic Rule3B` は引き続き `[v3-only]` evidence として隔離する。
- pre-freeze fragments are superseded and non-authoritative.

## Guard Expectations

- internal full-SCV readiness が green でも、operator summary の primary verdict section を変えてはならない。
- `verdict_match_rate` は `v3_shadow_verdict` non-None と full verdict computability の両方が成立するまで `N/A` を維持する。
- convenience 実装で hybrid passthrough を入れて `scv_offtarget` 未確定経路を再導入してはならない。

*End of document*
