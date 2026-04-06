# 9KR6 Real-Data Full-Run Contract Check

Date: 2026-04-06
Scope: full-library integrated runs for `9KR6_CYS328`

This audit checks operational contract stability, not chemistry quality.
The monitored questions were:

1. do `run_manifest.json`, `output_inventory.json`, and `replay_audit.json` survive full runs
2. do `comparison_type` and `skip_reason_codes` stay stable across manifest and reports
3. does `cap_batch_eval.json` remain the Cap truth source
4. do full runs stay inside a practical runtime envelope

## Inputs

- benchmark config: `configs/9kr6_cys328.benchmark.yaml`
- production config: `configs/9kr6_cys328.production.yaml`
- stageplan: `configs/stageplan.empty.json`
- benchmark integrated companion: `outputs/realdata_v29_local_checks/2026-04-06/integrated/benchmark.json`
- production integrated companion: `outputs/realdata_v29_local_checks/2026-04-06/integrated/production.json`
- shared fixtures:
  - PAT diagnostics: `outputs/realdata_v29_local_checks/2026-04-06/fixtures/pat.json`
  - managed theta table: `outputs/realdata_v29_local_checks/2026-04-06/fixtures/theta_rule1_table.parquet`
  - Cap fixture: `outputs/realdata_v29_local_checks/2026-04-06/fixtures/caps.parquet`

Libraries:

- `data/libraries/fACR2240.smiles`: `2240` rows
- `data/libraries/CYS-3200.smiles`: `3200` rows

## Run order

1. `fACR2240 benchmark full`
2. `CYS3200 benchmark full`
3. `fACR2240 production full`
4. `CYS3200 production full`

## Required artifact contract

Each run was checked for existence and non-empty materialization of:

- `run_manifest.json`
- `output_inventory.json`
- `core_compounds.parquet`
- `rule1_assessments.parquet`
- `cap_batch_eval.json`
- `qc_report.json`
- `eval_report.json`
- `collapse_figure_spec.json`
- `replay_audit.json`

## Results

| Run | Elapsed | comparison_type | replay_audit | inventory_complete | skip_reason_codes | Cap truth source | Cap verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fACR2240-benchmark-full` | `283.92s` | `same-config` | `PASS` | `true` | `[]` | `true` | `FAIL / FAIL_L0_SHUFFLE_INSENSITIVE` |
| `CYS3200-benchmark-full` | `379.05s` | `same-config` | `PASS` | `true` | `[]` | `true` | `FAIL / FAIL_L0_SHUFFLE_INSENSITIVE` |
| `fACR2240-production-full` | `2838.76s` | `cross-regime` | `PASS` | `true` | `[]` | `true` | `FAIL / FAIL_L0_SHUFFLE_INSENSITIVE` |
| `CYS3200-production-full` | `3977.96s` | `cross-regime` | `PASS` | `true` | `[]` | `true` | `FAIL / FAIL_L0_SHUFFLE_INSENSITIVE` |

Interpretation:

- all four full runs completed with required artifacts present and non-empty
- `replay_audit.result` stayed `PASS` on every run
- benchmark runs preserved `same-config`
- production runs preserved `cross-regime`
- `skip_reason_codes` stayed empty and consistent across manifest, QC, eval, collapse, and replay
- `cap_batch_eval.json` remained the Cap truth source on every run

The production runs were not compared numerically against benchmark runs.
The only production-specific contract check was `cross-regime` consistency.

## First-run timing trace

The first full run, `fACR2240-benchmark-full`, was used as the operational timing baseline.

| Artifact / event | UTC |
| --- | --- |
| start | `2026-04-06T01:46:35.0439889Z` |
| `core_compounds.parquet` | `2026-04-06T01:51:14.3347207Z` |
| `rule1_assessments.parquet` | `2026-04-06T01:51:16.2212765Z` |
| `cap_batch_eval.json` | `2026-04-06T01:51:18.5050029Z` |
| `qc_report.json` | `2026-04-06T01:51:18.5070237Z` |
| `eval_report.json` | `2026-04-06T01:51:18.5060037Z` |
| `collapse_figure_spec.json` | `2026-04-06T01:51:18.5092337Z` |
| `run_manifest.json` | `2026-04-06T01:51:18.5326900Z` |
| `output_inventory.json` | `2026-04-06T01:51:18.5366893Z` |
| `replay_audit.json` | `2026-04-06T01:51:18.6094084Z` |
| end | `2026-04-06T01:51:18.9730364Z` |

This gives a practical ordering estimate:

- Core bridge dominates the early wall time
- Rule1 materializes shortly after Core
- Cap, reports, manifest/inventory, and replay audit cluster at the end

## Output locations

Per-run monitoring logs:

- `outputs/realdata_v29_local_checks/2026-04-06/runs/fACR2240-benchmark-full/run_monitor.json`
- `outputs/realdata_v29_local_checks/2026-04-06/runs/CYS3200-benchmark-full/run_monitor.json`
- `outputs/realdata_v29_local_checks/2026-04-06/runs/fACR2240-production-full/run_monitor.json`
- `outputs/realdata_v29_local_checks/2026-04-06/runs/CYS3200-production-full/run_monitor.json`

Primary run directories:

- `outputs/realdata_v29_local_checks/2026-04-06/runs/fACR2240-benchmark-full`
- `outputs/realdata_v29_local_checks/2026-04-06/runs/CYS3200-benchmark-full`
- `outputs/realdata_v29_local_checks/2026-04-06/runs/fACR2240-production-full`
- `outputs/realdata_v29_local_checks/2026-04-06/runs/CYS3200-production-full`

## Limits of this audit

This audit did not intentionally interrupt a full run.
Therefore, the specific condition "partial artifact must not be treated as complete after interruption"
was not exercised here. That contract remains covered by the existing replay/inventory hardening and tests,
but not by a deliberate full-run kill test in this audit.
