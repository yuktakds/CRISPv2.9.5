# ADR-V3-11: M-2 Authority Transfer for `verdict_record.json`

Status: accepted  
Date: 2026-04-09  
Parent: `adr_v3_10_full_migration_contract.md`, `verdict_record_schema_freeze.md`, `archive/close_memos/vn06_m1_close_memo.md`  
Scope: define the exact M-2 Layer 0 authority transfer decision boundary, separately from public bridge inclusion.

---

## Context

Current state is fixed as follows.

- `verdict_record.json` is the canonical Layer 0 authority.
- `sidecar_run_record.json` is a backward-compatible mirror.
- VN-05 is closed.
- VN-06 M-1 schema-freeze + soak proof is closed.
- public bridge inclusion is still not authorized.

This ADR does not reopen those points. It only defines when M-2 authority transfer may occur, what changes at cutover, what must remain unchanged, and when rollback is mandatory.

---

## Decision

### 1. M-2 changes Layer 0 authority only

If this ADR is accepted and its trigger is satisfied, canonical Layer 0 authority moves from `sidecar_run_record.json` to `verdict_record.json`.

The following do not change as part of M-2:

- `output_inventory.json` remains rc2 authority and is not widened.
- `generator_manifest.json` remains the sidecar inventory / replay contract.
- `comparator_scope` does not widen automatically.
- `comparable_channels` do not widen automatically.
- `v3_shadow_verdict` does not activate automatically.
- operator-facing `verdict_match_rate` does not activate automatically.
- `Cap` remains outside `comparable_channels`.
- public bridge inclusion remains a separate decision.

### 2. Authority field set moved at cutover

M-2 transfers the following Layer 0 authority fields to `verdict_record.json`.

- `run_id`
- `output_root`
- `semantic_policy_version`
- `comparator_scope`
- `comparable_channels`
- `v3_only_evidence_channels`
- `channel_lifecycle_states`
- `full_verdict_computable`
- `full_verdict_comparable_count`
- `verdict_match_rate`
- `verdict_mismatch_rate`
- `path_component_match_rate`
- `v3_shadow_verdict`
- `authority_transfer_complete`

`schema_version`, `sidecar_run_record_artifact`, and `generator_manifest_artifact` remain required fixed provenance pointers in `verdict_record.json`, but they are not separate widening decisions.

### 3. Exact M-2 trigger

M-2 may execute only when all of the following are true.

1. `VN-01` through `VN-05` are satisfied under the current accepted authority set, and `VN-06 M-1 close` is satisfied as recorded in `archive/close_memos/vn06_m1_close_memo.md`.
2. The M-1 authority field map is fully defined and source-complete.
3. The 30-run M-1 soak window is green:
   - consecutive 30 runs
   - same `semantic_policy_version`
   - same `crisp.v3.vn06_readiness/v1`
   - same `crisp.v3.verdict_record/v1`
   - `dual_write_mismatch_count = 0` for every run
   - `schema_complete = true` for every run
   - `manifest_registration_complete = true` for every run
   - bridge comparator enabled for every soak candidate run
   - operator-facing surface inactive for every run
4. The current cutover candidate run still has `dual_write_mismatch_count = 0`.
5. The current cutover candidate run still has `authority_transfer_complete = false` before cutover.
6. Human explicit decision is recorded by merged repo documentation / PR review. Automation alone must not perform the promotion.

### 3A. Cutover preconditions table

Before M-2 cutover execution, the following gates must each be verified as YES. Any NO is a hard block.

| gate | requirement | evidence | fail action |
|---|---|---|---|
| M2-01 | VN-06 M-1 close complete | `archive/close_memos/vn06_m1_close_memo.md` merged and soak proof accepted | do not cut over |
| M2-02 | authority field map frozen | `verdict_record_schema_freeze.md` merged; all §2 fields present in schema | do not cut over |
| M2-03 | 30-run soak window green | CI history: 30 consecutive runs with `dual_write_mismatch_count = 0`, `schema_complete = true`, `manifest_registration_complete = true` | do not cut over |
| M2-04 | rollback procedure documented and tested | §5 rollback conditions documented in this ADR; rollback drill passed (§6) | do not cut over |
| M2-05 | `output_inventory.json` unchanged | artifact diff check between M-1 baseline and cutover candidate: zero diff on `output_inventory.json` | hard block; if diff detected, investigate before proceeding |
| M2-06 | operator-facing still inactive pre-cutover | report guards confirm: no `verdict_match_rate` numeric display, no `v3_shadow_verdict` activation, `[exploratory]` label present on all v3 sections | hard block |
| M2-07 | cutover candidate run is clean | current run: `dual_write_mismatch_count = 0`, `authority_transfer_complete = false` | do not cut over on this run |
| M2-08 | human explicit decision recorded | merged PR / repo documentation with cutover authorization | do not cut over; automation alone insufficient |
| M2-09 | rehearsal dry-run passed | rehearsal report available (§7); no anomalies | do not cut over without rehearsal |

The cutover operator must verify all nine gates and record the gate status in the cutover commit message or accompanying memo. Gates M2-01 through M2-03 are pre-existing conditions from §3; gates M2-04 through M2-09 are additional operational readiness conditions added by this section.

### 4. Backward compatibility after cutover

After M-2 cutover:

- `sidecar_run_record.json` remains materialized.
- `sidecar_run_record.json` becomes a backward-compatible mirror, not the canonical authority.
- dual-write continues until a later explicit removal ADR says otherwise.
- Any transferred authority field that diverges between `verdict_record.json` and `sidecar_run_record.json` is a hard failure.

### 5. Rollback conditions

After M-2 cutover, rollback to M-1 is mandatory if any of the following occur.

- any transferred authority field mismatch between `verdict_record.json` and `sidecar_run_record.json`
- any authority source gap (a §2 field present in one file but absent or null in the other)
- `verdict_record.json` manifest registration failure (absent from `generator_manifest.json` or `expected_output_digest` mismatch)
- `schema_version` drift for `verdict_record.json` or `vn06_readiness.json`
- operator-facing verdict activation before separate public inclusion authorization
- `output_inventory.json` mutation to reflect v3 authority
- `Cap` appearing in `comparable_channels`

Rollback means:

- canonical Layer 0 authority returns to `sidecar_run_record.json`
- `verdict_record.json` returns to non-authoritative M-1 dual-write mode
- `output_inventory.json` remains untouched
- public inclusion decision remains blocked until a new explicit decision is merged
- rollback is recorded in repo documentation with the triggering condition

### 6. Rollback drill

A rollback drill must be executed and passed before M-2 cutover is authorized (gate M2-04). The drill verifies that the rollback path is mechanically sound and does not corrupt authority state.

#### 6.1 Drill procedure

The drill is performed on a non-production fixture run (benchmark smoke or CI-sized fixture).

```text
Step R-1: Start from M-1 dual-write state
  - sidecar_run_record.json is canonical authority
  - verdict_record.json is materialized, non-authoritative
  - dual_write_mismatch_count = 0

Step R-2: Simulate M-2 cutover
  - set authority_transfer_complete = true in verdict_record.json
  - designate verdict_record.json as canonical authority for this drill run
  - verify: all §2 fields readable from verdict_record.json
  - verify: sidecar_run_record.json still materialized with identical field values

Step R-3: Inject rollback trigger
  - introduce a controlled authority field mismatch:
    artificially set verdict_record.json.comparator_scope = "INJECTED_FAULT"
    while sidecar_run_record.json.comparator_scope = "path_only_partial"
  - verify: mismatch detection fires

Step R-4: Execute rollback
  - canonical authority returns to sidecar_run_record.json
  - verdict_record.json.authority_transfer_complete = false
  - verify: sidecar_run_record.json is readable as canonical authority
  - verify: all §2 fields in sidecar_run_record.json are intact and correct
  - verify: verdict_record.json is present but non-authoritative

Step R-5: Post-rollback validation
  - verify: output_inventory.json is unchanged (zero diff)
  - verify: generator_manifest.json still references both artifacts
  - verify: operator-facing surface remains inactive
  - verify: comparable_channels == ["path"]
  - verify: v3_shadow_verdict remains None
  - verify: no Cap in comparable_channels
```

#### 6.2 Drill pass criteria

| criterion | pass condition |
|---|---|
| mismatch detection | Step R-3 mismatch is detected within the same run, not deferred |
| rollback execution | Step R-4 completes without manual intervention beyond the trigger |
| authority restoration | post-rollback canonical reads come from `sidecar_run_record.json` |
| field integrity | all §2 fields in `sidecar_run_record.json` match pre-drill baseline values |
| no collateral damage | `output_inventory.json` unchanged; `generator_manifest.json` intact; operator surface inactive |
| no phantom authority | after rollback, no code path reads `verdict_record.json` as authoritative |

#### 6.3 Drill report

The drill produces a short report recording:

- drill date and fixture run identifier
- each step outcome (pass / fail / skip with reason)
- each pass criterion (met / not met)
- any anomalies observed

This report is the evidence for gate M2-04.

### 7. M-2 rehearsal plan

The rehearsal is a full dry-run of the cutover sequence on a non-production fixture, with operator-facing surface kept inactive. It is distinct from the rollback drill: the drill tests the failure path; the rehearsal tests the success path.

#### 7.1 Rehearsal scope

- fixture: benchmark smoke fixture or CI-sized full fixture
- operator-facing: inactive throughout (no `verdict_match_rate` numeric, no `v3_shadow_verdict` activation, `[exploratory]` labels present)
- bridge comparator: enabled
- dual-write: active

#### 7.2 Rehearsal procedure

```text
Step H-1: Pre-rehearsal snapshot
  - record sidecar_run_record.json content hash
  - record verdict_record.json content hash
  - record output_inventory.json content hash
  - record generator_manifest.json entry list
  - record comparable_channels value
  - record operator-facing surface state

Step H-2: Verify all cutover preconditions (§3A table)
  - walk M2-01 through M2-08 (M2-09 is this rehearsal itself; mark as "in progress")
  - record each gate as YES / NO / N/A

Step H-3: Execute cutover on fixture
  - set authority_transfer_complete = true in verdict_record.json
  - designate verdict_record.json as canonical Layer 0 authority
  - execute one full sidecar run against the fixture

Step H-4: Post-cutover validation
  - verify: verdict_record.json contains all §2 fields with correct values
  - verify: sidecar_run_record.json is materialized with identical field values
  - verify: dual_write_mismatch_count = 0
  - verify: output_inventory.json content hash unchanged from H-1
  - verify: generator_manifest.json references verdict_record.json with
    correct expected_output_digest
  - verify: operator-facing surface remains inactive
  - verify: comparable_channels == ["path"] (no widening)
  - verify: v3_shadow_verdict == None (no activation)
  - verify: Cap ∉ comparable_channels

Step H-5: Execute rollback on fixture
  - perform the rollback procedure from §5
  - verify: canonical authority returns to sidecar_run_record.json
  - verify: all post-rollback conditions from §6.2 are met

Step H-6: Post-rollback re-run
  - execute one more sidecar run against the same fixture
  - verify: sidecar_run_record.json is used as authority
  - verify: verdict_record.json is present but non-authoritative
  - verify: dual_write_mismatch_count = 0
  - verify: all outputs match pre-rehearsal baseline
```

#### 7.3 Rehearsal pass criteria

| criterion | pass condition |
|---|---|
| cutover succeeds | H-3 + H-4 all pass |
| rollback succeeds | H-5 all pass (reuses §6.2 criteria) |
| round-trip integrity | H-6 outputs match H-1 baseline |
| no authority leak | at no point during H-3–H-6 does any unexpected authority change occur |
| no operator surface activation | operator-facing surface remains inactive throughout H-1–H-6 |
| no collateral widening | comparable_channels, comparator_scope, v3_shadow_verdict unchanged throughout |

#### 7.4 Rehearsal report

The rehearsal produces a report recording:

- rehearsal date and fixture identifier
- each step outcome (pass / fail)
- each pass criterion (met / not met)
- content hashes from H-1 and H-4 for diff verification
- any anomalies observed

This report is the evidence for gate M2-09.

---

## Non-goals

This ADR does not decide:

- public bridge inclusion yes/no
- comparator scope widening yes/no
- catalytic channel public comparable representation
- operator-facing activation yes/no

Those remain separate follow-on decisions.

---

## Implementation Gate

If this ADR is accepted, M-2 implementation work may begin. Implementation must produce the rollback drill (§6) and rehearsal (§7) tooling before the first production cutover attempt.

If this ADR is not accepted, repository state stays at M-1:

- `sidecar_run_record.json` canonical
- `verdict_record.json` non-authoritative
- public inclusion unapproved

---

## Execution sequence summary

```text
1. Verify M2-01 through M2-08          ← preconditions
2. Execute rollback drill (§6)          ← gate M2-04
3. Execute rehearsal dry-run (§7)       ← gate M2-09
4. Record all gate statuses             ← M2-01 through M2-09 all YES
5. Human explicit decision (PR merge)   ← gate M2-08
6. Production cutover                   ← authority_transfer_complete = true
7. Post-cutover monitoring              ← §5 rollback conditions watched
```

Steps 2 and 3 are non-production. Step 6 is production. Step 5 must precede step 6 and cannot be automated.

*End of document*
