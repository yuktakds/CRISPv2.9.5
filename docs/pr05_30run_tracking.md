# PR-05: 30-run Accumulation Tracker

**Exact unit:** `crisp.v3.release_blocking` — `tests/v3/test_rp5_release_blocking.py`
**Target lane:** `exploratory / v3-release-blocking` on `main` (GitHub Actions `windows-latest`)
**Target:** 30 consecutive green runs

## Counting rules

| Rule | Definition |
|------|-----------|
| Eligible run | `exploratory / v3-release-blocking` job on a **main-branch** `v3 Readiness Exploratory` workflow run |
| +1 condition | job `conclusion == success` |
| Reset condition | job `conclusion != success` → count resets to 0; log failure point |
| Excluded | PR runs, local runs, other workflows, required matrix, any non-main branch |

Auxiliary column `req-matrix` records `v2.9.5 Required Matrix` conclusion for no-regression monitoring only — not part of the 30-run count.

### Counting rule supplements

| conclusion | action |
|------------|--------|
| `success` | +1, streak continues |
| `failure` / `timed_out` / `cancelled` | streak resets to 0; log as failure point with cause note |
| `skipped` / `neutral` | no addition, streak unchanged; log as excluded event (note only) |

**Rerun policy:** same main commit counts at most once; only the final terminal conclusion is adopted. Multiple job executions on the same commit are not double-counted.

## Run log

| # | date | main sha | wf run id | job id | v3-release-blocking | count | req-matrix | note |
|---|------|----------|-----------|--------|---------------------|-------|------------|------|
| 1 | 2026-04-15 | cf5049483bae | 24446171060 | 71423006525 | green | 1 | success | PR #8 merge; initial hosted operational evidence established |
| 2 | 2026-04-16 | 6ad7d4ee347e | 24498478575 | 71598996370 | green | 2 | success | docs(v3): add v0.1.0 release roadmap and update README index |
| 3 | 2026-04-16 | 8cdb058855a4 | 24498919462 | 71600452454 | green | 3 | success | test(v3): add migration_scope unit tests — scope constants and PR-03 |
| 4 | 2026-04-16 | cdf4ef3e327a | 24501917940 | 71610615806 | green | 4 | success | Merge branch 'docs/v3-rp5-release-blocking-gate-plan' |
| 5 | 2026-04-16 | f08431539933 | 24502404672 | 71612282678 | green | 5 | success | test(v3): add layer0_authority payload unit tests — M2 fields, mirror, accessor |
| 6 | 2026-04-16 | e6fb40330760 | 24502657826 | 71613143938 | green | 6 | success | test(v3): add shadow_stability unit tests — campaign pass/fail, trim, digest stability |
| 7 | 2026-04-16 | 608d983a926c | 24502835154 | 71613751532 | green | 7 | success | test(v3): add current_public_scope unit tests — boundary constants and derive function |
| 8 | 2026-04-16 | dc5c9b592d10 | 24503248531 | 71615172088 | green | 8 | success | test(v3): add leaf unit tests for verdict_record schema checks and suppression_reason accessor |
| 9 | 2026-04-16 | 796457110030 | 24503515969 | 71616074256 | green | 9 | success | test(v3): add direct unit tests for rp3_activation pure functions |
| 10 | 2026-04-16 | cba36896ee7b | 24503693814 | 71616673091 | green | 10 | success | docs(v3): update clean code audit — record step-9 test additions |
| 11 | 2026-04-16 | 6410155daede | 24502116261 | 71611299965 | green | 11 | success | chore(tracker): record PR-05 run log entries 2–4 (2026-04-16) |
| 12 | 2026-04-16 | e579864ce9cc | 24504022046 | 71617822843 | green | 12 | success | chore(tracker): record PR-05 run log entries 5–10 (2026-04-16) |
| 13 | 2026-04-17 | 9b33f770d21a | 24541121051 | 71746936786 | green | 13 | success | chore(tracker): record PR-05 run log — 2026-04-17 [automated] |
| 14 | 2026-04-17 | edf4606a0822 | 24541379504 | 71747731633 | green | 14 | success | chore(tracker): record PR-05 run log entry 13 (2026-04-17) |
| 15 | 2026-04-17 | 1cea680618da | 24541450192 | 71747943905 | green | 15 | success | test(v3): add vn06_authority unit tests — determine_authority_phase, field_map_payload |
| 16 | 2026-04-17 | 2f980c28c781 | 24541801827 | 71749024838 | green | 16 | success | test: add canonical_json_bytes and sha256_bytes/json unit tests; update clean code audit |
| 17 | 2026-04-17 | ec2287e9ad4d | 24541982292 | 71749576739 | green | 17 | success | test(config): add config_models unit tests — ComparisonType, supported sets |
| 18 | 2026-04-17 | e6bf5c1cde58 | 24542065474 | 71749823997 | green | 18 | success | test(v3): add preconditions_types unit tests — enums, schema version, artifact ids |
| 19 | 2026-04-17 | 530765a5d6e6 | 24542161191 | 71750112171 | green | 19 | success | test(v3): add policy_options unit tests — parse_bridge_comparator_options |
| 20 | 2026-04-17 | e949279694f7 | 24542223602 | 71750312093 | green | 20 | success | test(v3): add bridge/path_view normalizer unit tests — bool/int edge cases |
| 21 | 2026-04-17 | 4797d56a7d10 | 24542597870 | 71751434202 | green | 21 | success | chore(tracker): record PR-05 run log entries 14–20 (2026-04-17) |
| 22 | 2026-04-17 | 5cdbf7662f6f | 24543143088 | 71753040238 | green | 22 | success | test(v3): add bridge/run_report unit tests — resolve_denominators and guard_no_full_aggregation |
| 23 | 2026-04-17 | 5f7a08f63633 | 24543185363 | 71753165229 | green | 23 | success | test(v3): add shadow_stability campaign guard unit tests — window size and sub-field violations |
| 24 | 2026-04-17 | a8274e6f41dc | 24543304569 | 71753527308 | green | 24 | success | test(v3): add readiness/consistency unit tests — build_inventory_authority_payload, find_truth_source_stage |
| 25 | 2026-04-17 | 9f9d0b188958 | 24543344542 | 71753653342 | green | 25 | success | test(v3): add keep_path_rc_audit_io unit tests — load_json_object, load_text, hash_loaded_files |
| 26 | 2026-04-17 | 6fa3c88e2b91 | 24543502879 | 71754118535 | green | 26 | success | test(v3): add preconditions_format unit tests — _parse_operator_summary_fields parser |
| 27 | 2026-04-17 | aa724030bf21 | 24543550268 | 71754253676 | green | 27 | success | test(v3): add preconditions_records unit tests — artifact_generator_id, artifact_ref, validate, descriptor_claim |
| 28 | 2026-04-17 | 01d61e19c4cb | 24543633986 | 71754504246 | green | 28 | success | test(v3): add bridge/path_comparison unit tests — derive_evidence_state, derive_verdict, bundle_index |
| 29 | 2026-04-17 | 1e917fa81aca | 24543686562 | 71754654013 | green | 29 | success | test(config): add config_loader unit tests — _require_mapping, _require_exact_keys, _require_string_list, _atom_from_dict |
| 30 | 2026-04-17 | e2190e14406a | 24543703527 | 71754702516 | green | 30 | success | test(v3): add runner_comparator unit tests — empty_comparator_execution defaults and _default_activation_decisions |
| 31 | 2026-04-17 | e521ebbded0d | 24543745536 | 71754832427 | green | 31 | success | test(v3): add operator_surface_state pure unit tests — suppression_reason, normalize helpers, _first_unmet_vn |
| 32 | 2026-04-17 | 4320c86c21ee | 24543780775 | 71754940503 | green | 32 | success | test(v3): add BridgeHeader unit tests — construction, defaults, to_dict field preservation |
| 33 | 2026-04-17 | a08e630464c6 | 24544015228 | 71755650670 | green | 33 | success | test(v3): add pathyes pure unit tests — pathyes_contract_fields fields and skip-code constants |

## Status

**Current count: 33 / 30 — 30/30 reached at run #30 (2026-04-17, SHA e2190e14406a)**

Last updated: 2026-04-17
