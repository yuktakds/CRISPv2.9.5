# Docs Index

`docs/` root contains the current canonical v3 authority set.

Current migration-contract authority:

- `adr_v3_10_full_migration_contract.md`: full migration contract boundary and promotion policy
- `adr_v3_11_m2_authority_transfer.md`: accepted M-2 authority transfer decision
- `wp1_wp2_channel_contracts_schema_freeze.md`: WP-1 / WP-2 freeze deliverables
- `comparable_channels_semantics.md`: WP-3 gate for `comparable_channels` semantics
- `wp4_wp5_audit_criteria.md`: WP-4 / WP-5 implementation audit criteria
- `verdict_record_schema_freeze.md`: VN-06 exact schema and authority-transfer contract

Current public-scope decision:

- `wp6_public_inclusion_decision_memo.md`: public bridge inclusion is currently closed as `keep`

Current keep-path RC definition:

- `v3_keep_path_rc_roadmap.md`: defines RC as the current public-scope release candidate, not as full-migration-ready
- `v3_keep_path_rc_acceptance_memo.md`: acceptance record binding the current keep decision, validator green state, and ops evidence

Pending reopen-path work:

- comparator_scope widening remains a separate human decision
- `comparable_channels` widening remains closed until a new accepted decision explicitly reopens it
- operator-facing `v3_shadow_verdict` and numeric `verdict_match_rate` remain inactive until that reopen path is accepted and implemented

Archived close memos:

- [`archive/close_memos/README.md`](/d:/CRISPv2.9.5/docs/archive/close_memos/README.md)

Current ops evidence:

- [`release/evidence/keep_path_rc/2026-04-09/README.md`](/d:/CRISPv2.9.5/docs/release/evidence/keep_path_rc/2026-04-09/README.md)
  includes `rc_gate_keep_path_report.json` as the bundled keep-path RC gate artifact

Supporting current v3 design authority:

- `CRISP_v3x_semantic_design_SOT_RC.md`
- `CRISP_v4.3.2.md`
- `v3x_evidence_channel_kernel_architecture.md`
- `v3x_bridge_ci_contracts.md`
- `v3x_path_verdict_comparability.md`
- `v3_05_bridge_drift_policy.md`
- `v3_07_rule3_catalytic_contract_freeze.md`
- `v3_full_migration_preconditions.md`

Supporting-note boundary:

- several supporting design docs were written pre-M-2
- any statement that `sidecar_run_record.json` is the current canonical Layer 0 authority is superseded by `adr_v3_11_m2_authority_transfer.md`
- pre-freeze / pre-M-2 fragments are non-authoritative for current Layer 0 authority state
- stale / superseded fragments must not be read as the current RC definition; `v3_keep_path_rc_roadmap.md` is the active RC glossary for public scope

Historical material is separated:

- [`archive/README.md`](/d:/CRISPv2.9.5/docs/archive/README.md)
- [`legacy/README.md`](/d:/CRISPv2.9.5/docs/legacy/README.md)

Archived examples:

- `archive/adr_v3_10_audit_report.md`: audit/handoff note, not current authority
- `archive/rule3_proposal_connected_adr.md`: deferred historical ADR draft, not current authority
