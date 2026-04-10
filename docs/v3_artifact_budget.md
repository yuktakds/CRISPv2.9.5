# v3 Sidecar Artifact Budget (RP-1 / RP-2 Default)

Status: active design note  
Date: 2026-04-10  
Scope: `v3_sidecar` default output policy and opt-in artifacts.

## Budget Summary

Base budget (comparator disabled):

- **≤ 9 artifacts** for path-only sidecar runs (Layer 0 authority + minimal Layer 1 replay/audit)

Comparator enabled adds:

- **+4 operator-facing artifacts** (bridge summary + drift attribution + operator summary + required CI candidacy)

Channel opt-ins add:

- `channel_evidence_cap.jsonl` when Cap is enabled
- `channel_evidence_catalytic.jsonl` when Catalytic is enabled

## Default Output (ArtifactPolicy.DEFAULT)

Layer 0 authority:

- `semantic_policy_version.json`
- `preconditions_readiness.json`
- `sidecar_run_record.json`
- `verdict_record.json`
- `vn06_readiness.json`
- `generator_manifest.json` (sidecar inventory + replay contract)

Layer 1 replay/audit (minimal):

- `observation_bundle.json`
- `channel_evidence_path.jsonl`
- `channel_evidence_cap.jsonl` (only if Cap enabled)
- `channel_evidence_catalytic.jsonl` (only if Catalytic enabled)
- `builder_provenance.json`

Operator-facing secondary (comparator enabled):

- `bridge_comparison_summary.json`
- `bridge_drift_attribution.jsonl`
- `bridge_operator_summary.md`
- `required_ci_candidacy_report.json`

## Opt-in Debug / Calibration Output (ArtifactPolicy.FULL)

These artifacts are **not** part of the default budget:

- `internal_full_scv_observation_bundle.json`
- `run_drift_report.json`
- `shadow_stability_campaign.json`
- `sidecar_invariant_history.json`
- `metrics_drift_history.json`
- `windows_streak_history.json`

## Configuration

Use the integrated config to select the policy:

```yaml
v3_sidecar:
  enabled: true
  artifact_policy: default  # default | full
```

Notes:

- `default` is the budgeted output set (authority + minimal replay/audit + operator secondary).
- `full` enables all debug / calibration artifacts for auditing or campaign runs.
