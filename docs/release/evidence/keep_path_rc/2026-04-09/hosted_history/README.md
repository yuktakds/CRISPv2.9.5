# Keep-Path RC Hosted History Source

Status: fixed offline source for `keep_path_rc_history_report.json`
Date: 2026-04-09
Scope: extracted hosted-lane artifact bundles used by the offline history harvester.

## Contents

- `hosted-run-01`
- `hosted-run-02`
- `hosted-run-03`

Each run contains:

- `hosted_run_metadata.json`
- `gate/rc_gate_keep_path_report.json`
- `campaign/campaign_index.json`
- `release_packet/release_packet_smoke_report.json`

## Boundary

- this source is non-authorizing evidence only
- it does not authorize required promotion
- it does not authorize public scope widening
- `path_component_match_rate` remains a Path-only component metric, not a full verdict proxy

*End of document*
