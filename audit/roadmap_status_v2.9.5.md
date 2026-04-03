# CRISP v2.9.5 Issue Roadmap Status

Date: 2026-04-03

## Version note

The proposal title said `CRISP v2.5.1`, but the current repository, integrated shell,
CLI entrypoints, and manifest `spec_version` are all `v2.9.5`. This status sheet is
therefore normalized to `v2.9.5`.

## Verification basis

- Repository inspection of `crisp/`, `configs/`, `audit/`, and `tests/`
- `uv run pytest -q` on 2026-04-03: `132 passed`

## Repo-verified done

- Epic 0
  - 0-1. uv-based cross-platform development environment
  - 0-2. 9KR6 real-data smoke configs
- Epic 1
  - 1-1. CXSMILES parser bug fix
- Epic 2
  - 2-1. 9KR6 config taxonomy metadata
  - 2-2. config comparison / regression guards
  - 2-3. regression-only CLI wrappers
    - Implemented as the `crisp-regression` entrypoint, not as `crisp run-regression-*`
    - Evidence: `crisp/cli/regression.py`, `tests/test_regression_wrapper.py`
  - 2-4. config guard matrix tests
    - Evidence: `tests/test_config_taxonomy.py`, `tests/test_cli_config_guards.py`
- Epic 3
  - 3-1. smoke config semantic drift audit
  - 3-2. 9KR6 config role institutionalization
- Epic 4
  - 4-1. v29 shell package bootstrap
  - 4-2. integrated manifest / inventory / writer
  - 4-3. legacy / integrated writer separation
    - Evidence: `crisp/v29/writers.py`, `crisp/v29/validators.py`, `tests/v29/test_cap_writer.py`
- Epic 5
  - 5-1. core_bridge implementation
  - 5-2. Rule3 trace-only proposal policy
- Epic 6
  - 6-1. PathYesAdapter bootstrap
  - 6-2. Rule1 sensor / SCV
  - 6-3. PathYesAdapter pat-backed connection
    - PAT diagnostics are read as run-level gating input only
    - Missing / invalid diagnostics degrade to `PATH_NOT_EVALUABLE` with explicit skip codes
    - Manifest, inventory, validation reports, and replay audit all record requested/resolved PathYes state
    - Evidence: `crisp/v29/pathyes.py`, `crisp/v29/cli.py`, `crisp/v29/validation.py`, `crisp/v29/reports/replay_audit.py`, `tests/v29/test_pathyes_pat_backed.py`
  - 6-4. theta_rule1 frozen table operation
    - Managed `theta_rule1_table.parquet` runtime contract added
    - pat-backed Rule1 runs now require a managed theta table and fail fast on missing / stale / incompatible tables
    - Manifest records theta table id, version, digest, source, and runtime contract
    - Calibration-table writer and runtime loader are separated in `crisp/v29/rule1_theta.py`
    - Evidence: `crisp/v29/rule1_theta.py`, `crisp/v29/cli.py`, `tests/v29/test_rule1_theta_runtime.py`
- Epic 7
  - 7-1. pair planning / donor plan
  - 7-2. Layer0 / Layer1 observations
  - 7-3. mapping / falsification builders
  - 7-4. Layer2
  - 7-5. CapBatchSCV
  - 7-6. Cap invariants validator
    - Dedicated validators for mapping / falsification / cap_batch_eval invariants
    - Wired into integrated CLI schema hard-errors and replay audit
- Epic 8
  - 8-1. validation batch
    - `qc_report.json`, `eval_report.json`, `collapse_figure_spec.json` を出力
    - `comparison_type`, `comparison_type_source`, `skip_reason_codes`, `inventory_json_errors` を machine-readable field として report に記録
  - 8-2. replay audit hardening
  - 8-3. completion_checks_json schema freeze
    - Evidence: `crisp/v29/manifest.py`, `tests/v29/test_manifest_inventory.py`, `tests/v29/test_replay_audit.py`
- Epic 9
  - 9-1. integrated CLI basic implementation
  - 9-2. repo-root contract

## Partially implemented / hardening still needed

- Epic 8
  - 8-4. output_inventory cross-check hardening
    - Completion recomputation, empty-file detection, unreadable inventory detection, completion-basis drift checks, severity-classified inventory JSON issues, and drift reason codes exist
    - Remaining gap: isolate this as a clearer cross-component invariant suite if it is to remain a roadmap item

## Not started / documentation debt

- Epic 1
  - 1-2. input normalization audit matrix
- Epic 3
  - 3-3. benchmark canonicalization contract document
- Epic 5
  - 5-3. Rule3 proposal-connected evolution ADR
- Epic 10
  - 10-1. 9KR6 benchmark integrated smoke
  - 10-2. 9KR6 production integrated smoke
  - 10-3. minimal Cap / assay fixture package for CI-friendly full runs

## Recommended next order

1. Close Epic 8 hardening items: `8-1`, `8-4`
2. Add real-data integrated verification: `10-1`, `10-2`, `10-3`
3. Backfill documentation debt: `1-2`, `3-3`, `5-3`

## Management update from the original proposal

- The proposal understates current repo progress.
- The following items should no longer be managed as merely "design complete":
  - `4-1`, `4-2`, `5-1`, `5-2`, `6-1`, `6-2`, `7-1` to `7-5`, `9-1`, `9-2`
- The following items should no longer be managed as "unstarted":
  - `2-3`, `2-4`, `4-3`, `8-3`
