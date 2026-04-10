# CRISP v2.9.5 Issue Roadmap Status

Date: 2026-04-03

## Version note

The proposal title said `CRISP v2.5.1`, but the current repository, integrated shell,
CLI entrypoints, and manifest `spec_version` are all `v2.9.5`. This status sheet is
therefore normalized to `v2.9.5`.

## Verification basis

- Repository inspection of `crisp/`, `configs/`, `audit/`, and `tests/`
- `uv run pytest -q` on 2026-04-06: `136 passed`
- workflow-equivalent required-set dry-run on 2026-04-03: `35 passed` x3
- hosted required-matrix runs on 2026-04-06: `3 / 3` successful
- real-data full-library contract audit on 2026-04-06: `4 / 4` successful

## Repo-verified done

- Epic 0
  - 0-1. uv-based cross-platform development environment
  - 0-2. 9KR6 real-data smoke configs
- Epic 1
  - 1-1. CXSMILES parser bug fix
  - 1-2. input normalization audit matrix
    - normalization boundary fixed for `repro.hashing` vs `v29.inputs`
    - Evidence: `docs/legacy/v2.9.5/input_normalization_matrix.md`
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
  - 3-3. benchmark canonicalization contract document
    - benchmark same-config baseline contract and allowed drift documented
    - Evidence: `docs/legacy/v2.9.5/9kr6_benchmark_contract.md`
- Epic 4
  - 4-1. v29 shell package bootstrap
  - 4-2. integrated manifest / inventory / writer
  - 4-3. legacy / integrated writer separation
    - Evidence: `crisp/v29/writers.py`, `crisp/v29/validators.py`, `tests/v29/test_cap_writer.py`
- Epic 5
  - 5-1. core_bridge implementation
  - 5-2. Rule3 trace-only proposal policy
  - 5-3. Rule3 proposal-connected evolution ADR
    - `v2.9.5` keeps Rule3 at trace-only and defers proposal-connected semantics behind a new ADR boundary
    - Evidence: `docs/rule3_proposal_connected_adr.md`
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
- Epic 10
  - 10-1. 9KR6 benchmark integrated smoke
    - benchmark config runs through `core+rule1+cap` with a real-data library subset, managed theta table, PAT diagnostics, and replay-auditable outputs
    - Evidence: `tests/v29/test_9kr6_benchmark_smoke.py`
  - 10-2. 9KR6 production integrated smoke
    - production config defaults to `comparison_type="cross-regime"` across manifest, reports, and replay audit
    - `same-config` override is rejected for production runs
    - Evidence: `tests/v29/test_9kr6_production_smoke.py`
  - 10-3. minimal Cap / assay fixture package for CI-friendly full runs
    - shared smoke helpers provide minimal library, caps, assays, PAT diagnostics, and managed theta table fixtures
    - full mode smoke reuses the fixture bundle
    - Evidence: `tests/v29_smoke_helpers.py`, `tests/v29/test_cap_assay_fixtures.py`, `tests/v29/test_cli_full_smoke.py`
- Release engineering documentation
  - RC checklist and release judgement template
    - Evidence: `docs/legacy/v2.9.5/v2.9.5_rc_checklist.md`
  - manifest / inventory schema freeze
    - Evidence: `docs/legacy/v2.9.5/v2.9.5_manifest_inventory_schema_freeze.md`
  - CI required matrix proposal
    - Evidence: `.github/workflows/v29-required-matrix.yml`, `audit/v2.9.5_ci_required_matrix.md`
  - RC release audit memo
    - Evidence: `audit/v2.9.5_rc1_release_audit.md`

## Partially implemented / hardening still needed

- H-3. long-run robustness / performance envelope
  - Full-library contract audit now exists for `fACR2240` and `CYS3200`
  - Remaining gap: extend this into a more formal artifact-size / memory / runtime envelope note if needed

## Not started / documentation debt

- None on the original implementation roadmap.

## Recommended next order

1. Characterize `H-3` long-run robustness / performance envelope
2. Keep the required CI set running as RC maintenance telemetry
3. Hold semantic changes for `v3.x`

## Management update from the original proposal

- The proposal understates current repo progress.
- The following items should no longer be managed as merely "design complete":
  - `4-1`, `4-2`, `5-1`, `5-2`, `6-1`, `6-2`, `7-1` to `7-5`, `9-1`, `9-2`
- The following items should no longer be managed as "unstarted":
  - `2-3`, `2-4`, `4-3`, `8-3`
- The remaining roadmap is now release-engineering only:
  - `H-3`
- The `v2.9.5` line is now treated as `rc1` with frozen object logic.
- Semantic changes should not land on the `v2.9.5` line; they belong to `v3.x`.
