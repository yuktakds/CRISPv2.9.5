# [exploratory] Bridge Operator Summary

## Comparator Header

- semantic_policy_version: `crisp.v3.semantic_policy/rev3-sidecar-first`
- comparator_scope: `path_only_partial`
- verdict_comparability: `partially_comparable`
- comparable_channels: `path`
- v3_only_evidence_channels: `cap, catalytic`
- rc2_policy_version: `v2.9.5-rc2`
- verdict_match_rate: `N/A`
- path_component_match_rate: `1/1 (100.0%)`
- comparable_subset_size: `1`
- sidecar_inventory_source: `v3_sidecar/generator_manifest.json`
- sidecar_outputs_authority: `generator_manifest.outputs`
- rc2_inventory_source: `output_inventory.json`
- rc2_outputs_authority: `output_inventory.generated_outputs`

## Surface Contract

- rc2 display role: `primary`
- v3 display role: `[exploratory] secondary`

## Comparison Summary

- rc2_reference_kind: `rc2_path_diagnostics_input`
- v3_shadow_kind: `v3_sidecar_observation_bundle`
- unavailable_channels: `none`
- run_level_flags: `PATH_ONLY_PARTIAL, FINAL_VERDICT_NOT_COMPARABLE, PATH_COMPONENT_BRIDGE_CONSUMER_PRESENT, PATH_COMPONENT_VERDICT_COMPARABILITY_DEFINED`

This report is [exploratory] only. It does not publish a final verdict and it does not change rc2 meaning.
Cap / Catalytic sidecar materialization does not widen the current Path-only comparability claim.

## Channel Coverage

- path: `present_on_both_sides`

## V3-only Evidence

- [v3-only] cap: `observation_materialized`
- [v3-only] catalytic: `observation_materialized`

## Drift Counts

- total_drifts: `0`
- coverage_drift_count: `0`
- applicability_drift_count: `0`
- metrics_drift_count: `0`
- witness_drift_count: `0`
