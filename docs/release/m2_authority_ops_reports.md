# M-2 Authority Ops Reports

Status: accepted
Date: 2026-04-09
Parent: `adr_v3_11_m2_authority_transfer.md`, `v3_current_boundary.md`
Scope: define the reusable rollback drill, rehearsal, and post-cutover monitoring report shapes for M-2 authority operations.

## Tooling

The reusable entry point is:

```text
python scripts/run_m2_authority_ops_package.py rollback-drill --run-dir <run> --output-dir <out>
python scripts/run_m2_authority_ops_package.py rehearsal --primary-run-dir <run-a> --rerun-run-dir <run-b> --output-dir <out>
python scripts/run_m2_authority_ops_package.py monitoring --readiness-files <vn06_readiness...> --output-dir <out>
```

## Rollback Drill Report

Artifact: `m2_rollback_drill_report.json`

Minimum contents:

- baseline hashes for `output_inventory.json` and core sidecar authority artifacts
- post-run hashes for the same artifact set
- `injected_fault_field`
- `injected_fault_mismatches`
- `injected_fault_detected`
- `dual_write_mismatch_count`
- `operator_surface_inactive`
- `output_inventory_unchanged`
- rollback projection fields
- `drill_passed`

## Rehearsal Report

Artifact: `m2_rehearsal_report.json`

Minimum contents:

- primary and rerun hash snapshots
- normalized digests for round-trip comparison
- `round_trip_mismatches`
- `round_trip_integrity`
- primary / rerun validator errors
- primary / rerun operator inactivity
- `rehearsal_passed`

## Post-Cutover Monitoring Report

Artifact: `m2_post_cutover_monitoring_report.json`

Minimum contents:

- `required_window_size`
- `observed_window_size`
- `authority_phase_m2_streak`
- `dual_write_mismatch_zero_streak`
- `operator_surface_inactive_streak`
- `manifest_registration_complete_streak`
- `schema_complete_streak`
- `window_passed`

## Audit Expectations

- rollback drill must detect an injected authority mismatch in the same run
- rehearsal must preserve round-trip integrity on the same fixture
- monitoring must keep `dual_write_mismatch_count = 0`
- monitoring must keep operator-facing verdict surfaces inactive until public inclusion is separately widened

*End of document*
