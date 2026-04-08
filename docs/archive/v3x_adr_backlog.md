# v3.x ADR Backlog Bootstrap

Date: 2026-04-06
Source: [../legacy/v2.9.5/v2.9.5_rc2_deferred_v3x_topics.md](../legacy/v2.9.5/v2.9.5_rc2_deferred_v3x_topics.md)
Status: initial backlog for `v3x/design-adr-bootstrap`

This file seeds the `v3.x` ADR backlog from the rc2 deferred-topic index.
It exists to keep semantic work off the `v2.9.5` release line.

## Backlog entries

| Backlog item | Problem to resolve | Minimum ADR output |
| --- | --- | --- |
| ADR-1. Rule3 proposal-connected semantics | Decide whether Rule3 stays observational or becomes execution-significant | semantic mode, policy version, replay evidence, regression envelope |
| ADR-2. same-pose style requirement | Decide whether a new same-pose requirement exists and where it lives | predicate definition, scope, validation plan, non-goals |
| ADR-3. CoreSCV backflow boundary | Decide whether shell diagnostics may influence CoreSCV or other object logic | boundary statement, allowed inputs, forbidden reverse flows |
| ADR-4. object-logic change process | Define how object-logic changes are proposed, reviewed, and versioned in `v3.x` | versioning rule, test expectations, migration rule |
| ADR-5. taxonomy / comparison semantics | Revisit the meaning of `same-config`, `cross-regime`, and related labels if needed | vocabulary, invariants, CI impact, operator wording |
| ADR-6. benchmark / production operating model | Decide whether benchmark and production definitions remain separate or are redesigned | role taxonomy, allowed comparisons, release-engineering impact |

## Suggested order

1. ADR-1 Rule3 proposal-connected semantics
2. ADR-3 CoreSCV backflow boundary
3. ADR-5 taxonomy / comparison semantics
4. ADR-6 benchmark / production operating model
5. ADR-2 same-pose style requirement
6. ADR-4 object-logic change process

## Entry rule

Before drafting any ADR above:

1. restate the rc2 frozen boundary that the proposal would cross
2. define the semantic delta before implementation
3. list artifact / replay / validator consequences up front
4. state what stays out of scope for the first `v3.x` cut

## Immediate next step

Open ADR-1 first and treat [../rule3_proposal_connected_adr.md](../rule3_proposal_connected_adr.md)
as predecessor context, not as permission to implement on the rc2 line.
