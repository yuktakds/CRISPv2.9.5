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

M-1 で `sidecar_run_record.json` と field-by-field cross-check する authority fields は以下に固定する。

- `run_id`
- `output_root`
- `semantic_policy_version`
- `comparator_scope`
- `comparable_channels`
- `v3_only_evidence_channels`
- `channel_lifecycle_states`
- `path_component_match_rate`

M-1 では上記いずれかの mismatch を hard block とする。加えて以下も hard block とする。

- `authority_transfer_complete != false`
- `v3_shadow_verdict != null`
- `verdict_match_rate != null`

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

## Backward Compatibility

- M-1 では `sidecar_run_record.json` が canonical Layer 0 authority のまま残る
- M-2 cutover 後も `sidecar_run_record.json` は backward-compatible mirror として保持する
- `sidecar_run_record.json` の削除や optional 化は別 ADR がない限り行わない

*End of document*
