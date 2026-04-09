# verdict_record.json Schema Freeze

Status: accepted
Date: 2026-04-09
Parent: `adr_v3_10_full_migration_contract.md`, `wp1_wp2_channel_contracts_schema_freeze.md`, `wp6_public_inclusion_decision_memo.md`
Scope: VN-06 close work に必要な `verdict_record.json` exact schema, M-1 dual-write authority fields, M-2 authority transfer trigger を固定する。

## Current Status

- current canonical Layer 0 authority is still `sidecar_run_record.json`
- `verdict_record.json` is active only in M-1 dual-write mode
- `v3_shadow_verdict` remains `None`
- public bridge inclusion is still not authorized

## M-1 Authority Fields

M-1 で `sidecar_run_record.json` と `verdict_record.json` を cross-check する authority field map は以下に固定する。`source field` が観測できない場合も `mismatch = 0` 扱いにしてはならず、source gap として hard block に含める。

| source field in `sidecar_run_record.json` | target field in `verdict_record.json` | comparison mode | mismatch severity |
| --- | --- | --- | --- |
| `run_id` | `run_id` | `exact` | `hard-block` |
| `output_root` | `output_root` | `exact` | `hard-block` |
| `semantic_policy_version` | `semantic_policy_version` | `exact` | `hard-block` |
| `comparator_scope` | `comparator_scope` | `exact` | `hard-block` |
| `comparable_channels` | `comparable_channels` | `set-equal` | `hard-block` |
| `v3_only_evidence_channels` | `v3_only_evidence_channels` | `set-equal` | `hard-block` |
| `channel_lifecycle_states` | `channel_lifecycle_states` | `exact` | `hard-block` |
| `bridge_diagnostics.bridge_comparison_summary.run_drift_report.full_verdict_computable` | `full_verdict_computable` | `exact` | `hard-block` |
| `bridge_diagnostics.bridge_comparison_summary.run_drift_report.full_verdict_comparable_count` | `full_verdict_comparable_count` | `exact` | `hard-block` |
| `bridge_diagnostics.bridge_comparison_summary.run_drift_report.verdict_match_rate` | `verdict_match_rate` | `nullable-exact` | `hard-block` |
| `bridge_diagnostics.bridge_comparison_summary.run_drift_report.verdict_mismatch_rate` | `verdict_mismatch_rate` | `nullable-exact` | `hard-block` |
| `bridge_diagnostics.bridge_comparison_summary.run_drift_report.path_component_match_rate` | `path_component_match_rate` | `nullable-exact` | `hard-block` |
| current-scope invariant: `v3_shadow_verdict` must remain null during M-1 | `v3_shadow_verdict` | `nullable-exact` | `hard-block` |
| current-scope invariant: authority transfer must remain not executed during M-1 | `authority_transfer_complete` | `exact` | `hard-block` |

M-1 では上記いずれかの mismatch、または authority source gap を hard block とする。

補足:

- `bridge_comparator` が disabled の run では `run_drift_report` 由来 field は current-scope default (`full_verdict_computable=false`, `full_verdict_comparable_count=0`, `verdict_match_rate=null`, `verdict_mismatch_rate=null`, `path_component_match_rate=null`) として扱う
- ただし、そのような run は VN-06 soak window の候補 run には数えない

## Frozen Schema Surface

`verdict_record.json` required schema fields は以下に固定する。

- `schema_version`
- `run_id`
- `output_root`
- `semantic_policy_version`
- `comparator_scope`
- `comparable_channels`
- `v3_only_evidence_channels`
- `channel_lifecycle_states`
- `full_verdict_computable`
- `full_verdict_comparable_count`
- `verdict_match_rate`
- `verdict_mismatch_rate`
- `path_component_match_rate`
- `v3_shadow_verdict`
- `authority_transfer_complete`
- `sidecar_run_record_artifact`
- `generator_manifest_artifact`

`schema_version` は `crisp.v3.verdict_record/v1` に固定する。

## M-2 Authority Transfer Trigger

`verdict_record.json` が Layer 0 authority に昇格してよい exact trigger は以下に固定する。

- `VN-01` through `VN-06` are all satisfied
- dual-write mismatch count = `0`
- manifest registration for `verdict_record.json` is complete
- human explicit decision is present

この trigger が閉じるまでは authority transfer を実行してはならない。

## VN-06 Close / M-1 Soak Success Criteria

VN-06 を ready-to-close と判定してよい M-1 soak success 条件は以下に固定する。

- consecutive window size = `30` runs
- dual-write mismatch count = `0` for all runs in the window
- manifest registration for `verdict_record.json` is complete for all runs in the window
- `schema_complete = true` for all runs in the window
- operator-facing surface remains inactive for all runs in the window

この文書でいう operator-facing inactive は少なくとも以下を意味する。

- `v3_shadow_verdict == null`
- `verdict_match_rate == null`
- `verdict_mismatch_rate == null`

VN-06 close work は authority transfer そのものではない。M-1 soak が成功しても `verdict_record.json` はなお non-authoritative であり、M-2 cutover は human explicit decision を伴う別 decision とする。

## Backward Compatibility

- M-1 では `sidecar_run_record.json` が canonical Layer 0 authority のまま残る
- M-2 cutover 後も `sidecar_run_record.json` は backward-compatible mirror として保持する
- `sidecar_run_record.json` の削除や optional 化は別 ADR がない限り行わない

*End of document*
