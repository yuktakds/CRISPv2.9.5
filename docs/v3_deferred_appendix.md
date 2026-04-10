# v3 Deferred Appendix (Allowed Future Extensions)

Status: deferred appendix  
Date: 2026-04-10  
Scope: objects and integrations that are **permitted as future extensions** but are **not required** for initial implementation.

This appendix does not authorize implementation. It only records allowed future extensions.

## Compound-side Objects (Deferred)

### `CompoundGraphCanonical`
Canonicalized molecule graph with explicit atom ordering, bond typing, stereochemical normalization policy, symmetry classes, and any protonation / tautomer policy used at v3.x semantic-policy level.

### `WarheadAnchorObject`
Defines the warhead or anchor-capable reaction center and the attachment vector(s) relevant to pathway-specific evaluation.

### `RigidityPersistenceObject`
Encodes persistence-side structural features (rotatable-bond burden, ring rigidity burden, torsion concentration, distal-body deformability). This object is **not** the path-blocking truth source.

### `BlockingBodyObject`
Represents the ligand sub-body capable of obstructing path families, including envelope geometry and projected cross-sections.

### `AnchorableMotifObject`
Represents the subset of the ligand capable of forming anchoring interactions or perturbing catalytic geometry.

## Protein-side Objects (Deferred)

### `PocketField`
Canonical decomposition of cavities, subpockets, local surface depressions, lining residues, and optional druggability descriptors.

### `ProteinFlexibilityField`
Protein-side flexibility summary derived from structure ensembles, homologs, or structural variability resources.

### `ResidueRoleMap`
Labels residues or residue groups as catalytic, gating, lining, auxiliary, cap-contact-prone, path-lining, or other evaluator-relevant roles.

### `HomologyContextObject`
Optional context object derived from homolog search or structure-alignment evidence. Auxiliary context only.

## External Tool Integration (Deferred)

External tools may be used as builder aids or auxiliary evidence sources. Their inclusion is deferred until a concrete implementation need exists.

- pocket/cavity tools (DoGSiteScorer, fpocket, mdpocket)
- contact tools (PLIP)
- homology tools (Foldseek)
- flexibility resources (PDBFlex or equivalent)
- tunnel/path tools (CAVER, MOLE)
- trajectory/solvent tools

## Notes

- None of the above objects are required by the initial implementation contract.
- If/when introduced, each object must define a builder contract, replay envelope, and validation rules before it can be used in public comparability.
