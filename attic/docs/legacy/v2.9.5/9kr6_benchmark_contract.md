# 9KR6 Benchmark Contract

Date: 2026-04-03

This document fixes the canonical benchmark contract for
[`configs/9kr6_cys328.benchmark.yaml`](D:/CRISPv2.9.5/configs/9kr6_cys328.benchmark.yaml).

It is the `v2.9.5` frozen regression baseline for parser, search, and reason-taxonomy changes.
It is not the smoke regime and it is not the production regime.

## Contract scope

The benchmark contract applies when all of the following hold:

1. `config_role == "benchmark"`
2. `frozen_for_regression == true`
3. `comparison_type == "same-config"` unless a deliberate cross-regime study is being run
4. identical structure file digest, library hash, stageplan hash, and seed set
5. for publishable Rule1 runs, `pathyes_mode == "pat-backed"` and a managed `theta_rule1_table.parquet` is present

If any of those are false, the run is not a canonical same-config benchmark regression.

## Frozen config fields

The following benchmark properties are frozen and baseline-significant:

| Contract field | Expected value |
| --- | --- |
| `config_role` | `benchmark` |
| `expected_use` | `Frozen regression baseline for parser, search, and reason-taxonomy changes.` |
| `allowed_comparisons` | `same-config`, `cross-regime` |
| `frozen_for_regression` | `true` |
| `pathway` | `covalent` |
| `target_name` | `9KR6_CYS328` |
| `sampling.n_conformers` | `4` |
| `sampling.n_rotations` | `16` |
| `sampling.n_translations` | `8` |
| `sampling.alpha` | `0.4` |
| `random_seed` | `42` |
| default comparison type | `same-config` |

The remaining geometry, anchoring, offtarget, staging, translation, and PAT fields
are also part of the frozen config payload because `same-config` requires canonical
config equality, not only sampling equality.

## Runtime companions that are part of the benchmark contract

The benchmark config alone is not sufficient for a publishable integrated run.
The following runtime companions are part of the managed contract:

- managed `theta_rule1_table.parquet`
- PAT run-level diagnostics providing `goal_precheck_passed`
- deterministic seed set in the manifest
- stageplan path and digest
- structure file digest

Required manifest fields for publishable Rule1 benchmark runs:

- `theta_rule1_table_id`
- `theta_rule1_table_version`
- `theta_rule1_table_digest`
- `theta_rule1_table_source`
- `theta_rule1_runtime_contract`
- `completion_basis_json.pathyes_mode_requested`
- `completion_basis_json.pathyes_mode_resolved`
- `completion_basis_json.pathyes_diagnostics_status`
- `completion_basis_json.pathyes_rule1_applicability`

If those are absent or inconsistent, the run is not benchmark-contract-complete.

## Comparison policy

Allowed:

- benchmark vs benchmark with `comparison_type: same-config`
- benchmark vs lowsampling/smoke/production with `comparison_type: cross-regime`

Disallowed:

- smoke or production treated as regression baselines
- benchmark verdict distributions compared directly against smoke/production as if they were same-config baselines
- same-config comparisons across distinct config roles

Operational rule:

- same-config is for regression baselines
- cross-regime is for regime interpretation, not regression acceptance

## What must be stable

For a same-config benchmark regression, the following are expected to remain stable:

- config taxonomy metadata
- structure digest
- library hash and compound order hash
- stageplan hash
- seed values
- `comparison_type == same-config`
- `comparison_type_source == config_role_default` unless a deliberate override is documented
- managed theta table metadata
- replay-audit readiness and pass state
- completion-basis semantics and required outputs

For publishable Rule1 benchmark runs, the following must also remain stable:

- `pathyes_mode_resolved == "pat-backed"`
- `pathyes_diagnostics_status == "loaded"`
- `pathyes_rule1_applicability == "PATH_EVALUABLE"`

## What may drift without invalidating the contract

These fields may change without implying chemistry or taxonomy drift:

- `run_id`
- creation timestamps
- resolved output paths
- materialized output format when `.parquet` falls back to `.jsonl`, provided the fallback is recorded in `output_materialization_events`
- PAT diagnostics source path strings that are run-local but semantically equivalent

These are execution-environment drifts, not benchmark-meaning drifts.

## Acceptance order for benchmark smoke and regression review

When a benchmark smoke or regression run looks wrong, review in this order:

1. `output_inventory.json`
2. `replay_audit.json`
3. `completion_basis_json`
4. managed theta table metadata
5. PathYes diagnostics status
6. only then verdict / reason distribution

This ordering is intentional. Contract and replay failures are higher-priority than
verdict deltas because they can invalidate the comparison itself.

## Cross-regime interpretation boundary

The benchmark contract does not authorize direct interpretation of smoke or production
behavior as benchmark drift. The audited low-sampling vs smoke findings already showed:

- low-sampling collapse is dominated by sampling budget
- smoke can flip the same molecules from `FAIL_NO_FEASIBLE` to `PASS`
- off-target taxonomy stayed stable while operating regime changed

Therefore:

- benchmark drift must be judged against the benchmark itself
- smoke and production runs are for operating-regime checks, not same-config regression gates

## Release-candidate implication

For `v2.9.5` to be treated as a release candidate, the benchmark contract should be
considered fixed unless a deliberate benchmark reset is documented. Any reset should
change at least one of:

- benchmark config file
- managed theta table version/digest/source
- accepted same-config regression baseline note
