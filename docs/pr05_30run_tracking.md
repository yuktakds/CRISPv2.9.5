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
| 2 | 2026-04-16 | 37797ce5dec772379ce4413073bfafd86e23fb14 | TBD | TBD | green | 2 | success | Merged 4 branches; exploratory / v3-release-blocking green |

## Status

**Current count: 2 / 30**

Last updated: 2026-04-16
