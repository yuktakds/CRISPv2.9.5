# v3 Initial Implementation Contract (Normative Vocabulary)

Status: design-only contract note  
Date: 2026-04-10  
Scope: define the **minimum normative vocabulary** for initial implementation. Everything else in the SoT is deferred until first concrete use.

## Normative Vocabulary (Initial Implementation)

- Objects: `PathReferenceField`, `CapPartitionObject`, `CatalyticFrameObject`
- Channels: `path`, `cap`, `catalytic`
- Projectors: Path (`project_path_payload`), Cap (`project_cap_payload`), Catalytic (`project_catalytic_payload`)
- Bridge: `SCVBridge` routing + `BridgeComparator` in `path_only_partial` scope
- Retained rc2 authority artifacts: `output_inventory.json` (rc2 authority), rc2 primary outputs used for bridge comparison
- Authority layering: Layer 0 (`verdict_record.json`), Layer 1 replay/audit records, operator-facing secondary surfaces
- Artifact budget: `v3_artifact_budget.md`

## Deferred Until First Concrete Use

- Any additional object/builder/path families not required by the three channels above
- External tool slots or future component families not tied to a concrete, approved scope
- New public-scope concepts (e.g., new report surfaces or widened comparability) without an explicit human decision
- Deferred appendix: `v3_deferred_appendix.md`

## Non-Goals

- This note does not authorize scope widening, operator activation, or required CI promotion.
- This note does not redefine the current boundary; see `v3_current_boundary.md`.

## Metric

- 初期実装で必須な新規型は 10 未満に抑える。
