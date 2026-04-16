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

## Status

**Current count: 4 / 30**

Last updated: 2026-04-16
