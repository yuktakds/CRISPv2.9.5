# Input Normalization Matrix

Date: 2026-04-03

This document fixes the normalization boundary for input libraries in `v2.9.5`.
It covers two distinct layers that intentionally do not behave identically:

1. `crisp.repro.hashing` and `crisp.cli.phase1`
2. `crisp.v29.inputs` and the integrated shell

The distinction matters because the CXSMILES fix closed a raw-library hashing bug,
while the integrated shell also applies a row-level normalization step before
serializing inputs back to the frozen core.

## Scope

Supported source formats for the integrated shell:

- `.smi`
- `.smiles`
- `.parquet`
- `.jsonl`
- `.json`
- `.csv`
- `.tsv`
- `.txt`

Supported source formats for the raw Phase1 / repro hashing path:

- line-based SMILES libraries parsed by `parse_smiles_library()` / `read_smiles_file()`

## Canonical boundaries

### Layer A: raw library hashing and Phase1 library parsing

Entry points:

- `crisp.repro.hashing.read_smiles_file`
- `crisp.repro.hashing.parse_smiles_library`
- `crisp.cli.phase1.run_phase1_library`

Invariants:

- CXSMILES `|...|` blocks are preserved as part of the SMILES token.
- The identifier is taken after the preserved CXSMILES block.
- `read_smiles_file()` returns preserved SMILES strings and is used by run-manifest hashing.
- `parse_smiles_library()` returns preserved `(smiles, compound_name)` tuples and is used by Phase1 CLI library execution.

Implication:

- A CXSMILES edit can change `library_hash`, `compound_order_hash`, or raw-input hashes even when RDKit canonical SMILES and verdicts do not change.

### Layer B: integrated-shell row normalization

Entry points:

- `crisp.v29.inputs.load_molecule_rows`
- `crisp.v29.inputs.to_core_library_text`
- `crisp.v29.core_bridge.run_core_bridge`

Invariants:

- `.smi` / `.smiles` inputs are normalized into rows with `molecule_id`, `smiles`, `library_id`, `input_order`.
- For `.smi` / `.smiles`, RDKit extension syntax appended as ` |...|` is stripped from the SMILES field before row materialization.
- For table formats, the `smiles` cell is preserved as supplied; no automatic CXSMILES stripping is applied there.
- `molecule_id` is taken from `molecule_id`, `name`, `compound_id`, or synthesized as `compound_00001`, etc.
- `input_order` is preserved if present for table formats; otherwise it is assigned sequentially from file order.

Implication:

- The integrated shell hashes normalized joined SMILES, not raw source bytes.
- For `.smi` / `.smiles`, a CXSMILES block can be present in the raw file and still be removed before the frozen core sees the row-normalized library text.

## Format matrix

| Source format | Parser path | SMILES normalization | Identifier source | `input_order` source | Hash-sensitive fields |
| --- | --- | --- | --- | --- | --- |
| `.smi` / `.smiles` via `repro.hashing` | `read_smiles_file` / `parse_smiles_library` | Preserve CXSMILES `|...|` | token after preserved CX block, else synthesized | file order | raw SMILES token, library bytes |
| `.smi` / `.smiles` via `v29.inputs` | `load_molecule_rows` | Strip trailing ` |...|` RDKit extension | col1, or col2 if col1 is `|...|`, else synthesized | sequential | normalized SMILES, row order |
| `.parquet` | `read_records_table` -> `_normalize_table_rows` | Preserve `smiles` cell as supplied | `molecule_id` / `name` / `compound_id` / synthesized | preserved `input_order` or sequential | row values after normalization |
| `.jsonl` / `.json` | `read_records_table` -> `_normalize_table_rows` | Preserve `smiles` cell as supplied | `molecule_id` / `name` / `compound_id` / synthesized | preserved `input_order` or sequential | row values after normalization |
| `.csv` / `.tsv` / `.txt` table path | `read_records_table` -> `_normalize_table_rows` | Preserve `smiles` cell as supplied | `molecule_id` / `name` / `compound_id` / synthesized | preserved `input_order` or sequential | row values after normalization |
| unknown text suffix | `load_molecule_rows` SMI fallback | Same as `.smi` / `.smiles` in Layer B | Same as `.smi` / `.smiles` in Layer B | sequential | normalized SMILES, row order |

## Expected normalization table

These fixture-style examples define the expected outputs for audit and regression review.

| Raw input | Loader | Expected `smiles` | Expected `molecule_id` | Canonical SMILES drift | Hash drift expectation |
| --- | --- | --- | --- | --- | --- |
| `CCO mol_001` | Layer A and Layer B | `CCO` | `mol_001` | none | none if bytes unchanged |
| `C=CC(=O)N[C@H]1CO |&1:5,r| mol_001` | Layer A | `C=CC(=O)N[C@H]1CO |&1:5,r|` | `mol_001` | none expected after RDKit parse | raw hash changes if CX block changes |
| `C=CC(=O)N[C@H]1CO |&1:5,r|\tmol_001` | Layer B | `C=CC(=O)N[C@H]1CO` | `mol_001` | none expected after RDKit parse | integrated `input_hash` changes if normalized SMILES changes |
| `{"name": "mol_a", "smiles": "CCN"}` | Layer B table path | `CCN` | `mol_a` | none | row-value hash changes if `name`/`smiles` changes |
| parquet row with `input_order=7` | Layer B table path | preserve supplied `smiles` | preserve supplied `molecule_id` | none unless `smiles` cell changes | `input_order` contributes to row order, not SMILES canonicalization |

## Hash and name change rules

The following are the stable expectations for review:

- `library_hash` changes on any byte-level library edit.
- Raw Phase1 / repro `compound_order_hash` changes when the preserved SMILES token sequence changes.
- Integrated-shell `input_hash` changes when normalized joined SMILES changes.
- `compound_name` / `molecule_id` changes if the identifier token changes or fallback synthesis changes.
- RDKit canonical SMILES drift is not implied by CXSMILES token drift.

## CXSMILES audit result carried forward

Observed in the audited `fACR2240.smiles` sample:

- CXSMILES rows audited: `66`
- compound-name changes: `66`
- input-hash changes: `66`
- canonical SMILES changes: `0`
- verdict changes: `0`
- reason changes: `0`

Interpretation:

- The parser fix closed raw identifier and hash corruption.
- The pass-heavy smoke distribution was not caused by CXSMILES corruption.
- Operating regime changes, not canonical chemistry drift, dominated the observed verdict drift.

## Review checklist

Before treating an input-related change as a chemistry regression, check in this order:

1. Which layer changed: raw hashing / Phase1 parsing, or integrated-shell row normalization.
2. Whether the edit changed raw bytes only, normalized SMILES only, or both.
3. Whether `molecule_id` or fallback ID assignment changed.
4. Whether canonical SMILES changed after RDKit parse.
5. Whether verdict / reason drift remains after controlling for config regime and comparison type.
