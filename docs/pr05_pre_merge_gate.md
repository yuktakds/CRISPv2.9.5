# PR-05 Pre-Merge Gate

Status: active — applies to every PR targeting main during PR-05 accumulation  
Scope: minimum verification before merging any branch to main. Does not count toward the 30-run streak; reduces the probability of an eligible run failing.

---

## Frozen Files (do not touch except for emergency fix)

These files are frozen for the duration of PR-05 accumulation. Any change — even cosmetic — requires explicit justification:

- `.github/workflows/v3-readiness-exploratory.yml`
- `.github/workflows/v3-keep-path-rc-exploratory.yml`
- `.github/workflows/v29-required-matrix.yml`
- `tests/v3/test_rp5_release_blocking.py`
- `tests/v3/test_exploratory_ci_separation.py`
- `tests/v3/test_keep_path_rc_exploratory_ci_workflow.py`

---

## Minimum Pre-Merge Checks

Run locally before opening a PR or pushing to main.

### 1. Three required tests

```
uv run pytest -q tests/v3/test_rp5_release_blocking.py tests/v3/test_exploratory_ci_separation.py tests/v3/test_keep_path_rc_exploratory_ci_workflow.py
```

All three must pass.

### 2. Workflow visual audit (30 seconds)

Open `.github/workflows/v3-readiness-exploratory.yml` and confirm:

- `exploratory / v3-release-blocking` job is still present with that exact name
- step runs `tests/v3/test_rp5_release_blocking.py` and nothing else

Open `.github/workflows/v3-keep-path-rc-exploratory.yml` and confirm:

- all job names start with `exploratory /`
- `required_promotion_authorized = $false` is still present in the metadata step
- `public_scope_widening_authorized = $false` is still present

Open `.github/workflows/v29-required-matrix.yml` and confirm:

- no new jobs reference `tests/v3/test_rp5_release_blocking.py` or keep-path-rc scripts

---

## Recording Rule (for each main run)

After each main-branch push completes on GitHub Actions:

1. Find the `v3 Readiness Exploratory` workflow run for that commit on main
2. Look up the `exploratory / v3-release-blocking` job conclusion only
3. Apply the rule:

| conclusion | action |
|---|---|
| `success` | +1; add row to run log |
| `failure` / `timed_out` / `cancelled` | reset to 0; add row with failure note |
| `skipped` / `neutral` | no change; log as excluded event (note only) |
| rerun | adopt final terminal conclusion only; same commit counts once |

4. Update `docs/pr05_30run_tracking.md`

---

## What Not To Do During Accumulation

- Do not change `comparator_scope` or `comparable_channels`
- Do not discuss or re-litigate `v3_shadow_verdict` or numeric verdict rates
- Do not add Cap / Rule3B comparable participation
- Do not generalize release semantics or expand WP-5 scope
- Do not touch the six frozen files without emergency justification
- Do not merge PRs to main that have not passed the three pre-merge tests

---

*End of document*
