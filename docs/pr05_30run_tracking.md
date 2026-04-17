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

## Status

**Current count: 12 / 30**

Last updated: 2026-04-17
