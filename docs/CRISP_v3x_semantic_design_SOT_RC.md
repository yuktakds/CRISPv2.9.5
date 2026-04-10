# CRISP v3.x Semantic Objects 統合設計書

Status: Release-candidate Source of Truth for the v3.x semantic redesign track  
Date: 2026-04-06  
Authority note: this unversioned filename is the canonical repo-carried Semantic Core SoT for the current v3.x design track.  
Supersedes: `/mnt/data/CRISP_v3x_semantic_design_SOT_v4.md` (prior aligned draft)  
Frozen reference line: `v2.9.5-rc2`  
Applicable repo root (current): `D:\CRISPv2.9.5`

Scope note: This SoT is **not** the initial implementation contract. The minimum normative vocabulary for initial implementation is defined in `v3_initial_implementation_contract.md`.
Deferred note: Objects and integrations outside the initial contract are recorded in `v3_deferred_appendix.md` and are **not** required for initial implementation.

---

## 0. 要点

本設計書は、`v2.9.5-rc2` の frozen release line とは切り離された **v3.x semantic redesign** の Source of Truth（SoT）である。`rc2` は release hardening のために意味論境界が固定されており、object-logic reinterpretation、taxonomy/comparison semantics change、proposal-connected Rule 3、benchmark / production meaning change は `rc2` に戻さない。本書は、それらの deferred topic を **v3.x ADR / design track** として再設計するための正式設計書である。

本書の中心決定は以下の 6 点である。

1. Rule は observer ではなく **cross-object evaluator** とする。  
2. 観測は **compound-side / protein-side / cross-object** に層分離する。  
3. Rule 1–3 の入力 object として `PathReferenceField`、`CapPartitionObject`、`CatalyticFrameObject` を明示的に導入する。  
4. Rule 1 は「剛直性 rule」ではなく、**path obstruction** と **obstruction persistence** の複合 evidence に再定義する。  
5. Rule 2 は「曖昧な Cap motion」ではなく、**deterministic Cap identity** を前提にした **cap engagement / mobility** evidence に再定義する。  
6. Rule 3 は **anchoring evidence** と **catalytic-frame disruption evidence** に分離する。

本書は旧 `CRISP_v4.3.1` / `CRISP_v4.3.2` の中核原則、すなわち「SCV のみが最終判定器」「terminal policy は object logic の外側」「PASS/FAIL/UNCLEAR は証拠付き」「決定論的再現性」「staging-aware な replayability」を継承する。さらに `rc2` deferral index が要求する「semantic delta を coding 前に書く」「artifact / replay contract を先に列挙する」「v3.x branch / ADR track に隔離する」という entry rule を本書の運用規則とする。

本書の release-candidate 判定は、追加情報の有無ではなく、設計上の必要蓋然性で決める。すなわち、今後の情報追加は live-code alignment や migration convenience のためには有用でありうるが、v3.x semantic architecture を凍結するための前提条件ではない。

---

## 1. Authority / Scope / Non-goals

### 1.1 Authority

本書は v3.x semantic redesign の SoT であり、以下を拘束する。

- v3.x ADR / design note の上位規範
- v3.x 実装で導入してよい semantic object と evaluator の定義
- v3.x artifact / replay contract の規範
- v3.x repo structure の規範構造

### 1.2 Non-authority

本書は以下を拘束しない。

- `v2.9.5-rc2` line の object logic
- `rc2` benchmark / production separation の意味
- `rc2` comparison semantics (`same-config`, `cross-regime`) の再定義
- current repo の未確認実装詳細

### 1.3 Non-goals

本書は現段階で以下を採用しない。

- same-pose requirement の正式採用
- CoreSCV reverse-flow の正式採用
- benchmark / production taxonomy の再定義
- canonical schema の即時全面更新
- learned model を object logic の truth source に据えること

---

## 2. Normative references

本書は以下を上位 reference として継承・参照する。

1. `CRISP_v4.3.1.md`  
   - `SCV` が唯一の最終判定器であること  
   - `terminal policy` が object logic の外側に置かれること  
   - `Evidence Artifact` と replayability の重視  
   - `MEF -> CPG -> Sensors -> SCV -> Staging Policy` の責務分離  
2. `CRISP_v4.3.2.md`  
   - `path_blocking` の上位定義  
   - `path_model = TUNNEL / SURFACE_LIKE` の separation  
   - `PATGoalRegion` と `goal_precheck` の導入  
   - run-level PAT diagnostics の考え方  
3. `legacy/v2.9.5/v2.9.5_rc2_deferred_v3x_topics.md`  
   - `rc2` boundary の凍結  
   - v3.x でのみ扱う deferred semantic topics の隔離  
   - semantic delta / artifact contract 先出しの entry rule

---

## 3. Inherited invariants from v4.3.x

v3.x でも以下を継承する。

### 3.1 Invariants retained unchanged

- スコア最適化ではなく、証拠付きの existence / non-satisfaction 判定を行う。  
- `SCV` のみが `PASS / FAIL / UNCLEAR` を返す。  
- `terminal policy` は search-control logic として object logic の外側に置く。  
- `PASS` は必ず witness と観測量を伴う。  
- `FAIL / UNCLEAR` は理由コードと fail-certificate を伴う。  
- 各 evaluator / sensor は replay 可能で、deterministic provenance を持つ。  
- staging-aware artifact を保持する。  
- public verdict reason と run-level diagnostics を混同しない。

### 3.2 Scope-of-validity inherited unchanged

v4.3.x と同様、v3.x も「活性を予測する」系ではない。CRISP `PASS` は「阻害の十分条件」ではなく、モデル M の下で「阻害仮説に矛盾しない」ことを示す必要条件系の判定である。したがって、warhead coverage、α 校正、剛体タンパクモデルの妥当性が崩れると、soundness claim の射程は限定される。

---

## 4. rc2 frozen reference regime

### 4.1 Frozen boundary

`rc2` line では以下を変更しない。

- object-logic reinterpretation
- taxonomy / comparison semantics change
- proposal-connected Rule 3 behavior
- benchmark / production meaning change

### 4.2 Existing rc2 representative artifact freeze

`rc2` の representative full-run artifact family は、少なくとも次を含む。

- `run_manifest.json`
- `output_inventory.json`
- `run_monitor.json`
- `replay_audit.json`
- `mapping_table.parquet`
- `falsification_table.parquet`
- `theta_rule1_resolution.json`
- `rule3_trace_summary.json`

Representative metadata supplied for `rc2` shows that both benchmark and production full-contract reruns were `run_mode_complete=true`, `replay_audit.result=PASS`, `theta_rule1_resolution_status=exact_target`, and `rule3_trace_summary_available=true`, with `rule3_trace_ordering_distribution = [{ordering_label: "none", count: N}]`. This confirms that `rc2` Rule 3 remains observational only in the frozen reference line.

### 4.3 Comparison semantics retained for reference only

For the frozen line:

- benchmark representative: `target_config_role = benchmark`, `comparison_type = same-config`
- production representative: `target_config_role = production`, `comparison_type = cross-regime`

v3.x may later redefine comparison semantics, but this document does **not** retroactively reinterpret the `rc2` meaning of those fields.

---

## 5. Semantic delta declared by v3.x

### 5.1 What changes semantically

v3.x changes the **referential semantics** of Rule 1–3.

- Rule 1 no longer treats rigidity as the rule itself; rigidity becomes a persistence-side evidence object.  
- Rule 2 no longer treats “Cap” as an implicit, pose-dependent intuition; Cap becomes a deterministic molecule-level partition.  
- Rule 3 no longer remains “anchoring only”; anchoring and catalytic-frame disruption become separate evidentiary channels.

### 5.2 What does not change

- `SCV` remains the only final verdict engine.  
- `terminal policy` remains search-control logic outside object logic.  
- `PASS / FAIL / UNCLEAR` remains the public verdict taxonomy, unless a later v3.x ADR explicitly changes it.  
- replayability and evidence-first operation remain mandatory.

### 5.3 What is explicitly deferred within v3.x

The following remain ADR-gated even inside v3.x:

- proposal-connected Rule 3 with execution-significant semantics
- any same-pose style requirement
- CoreSCV reverse-flow / backflow
- benchmark / production meaning redefinition
- taxonomy / comparison semantics redefinition

---

## 6. Design principles for v3.x

| Principle | Meaning |
|---|---|
| P-01 Semantic objects first | Rule redesign must start from object definition, not threshold tuning |
| P-02 Side-separated observations | compound-side and protein-side observations must be written separately |
| P-03 Cross-object evaluation only | Rule 1–3 are evaluators over objects, not raw observers |
| P-04 Truth-source explicitness | each evidence claim must name its artifact truth source |
| P-05 Replay before optimization | new semantics must be replayable before being optimized |
| P-06 Operator safety | public meanings must not drift silently across semantic-policy versions |
| P-07 Tool outputs are auxiliary | external tools support builders but do not automatically become truth sources |

---

## 7. v3.x layered architecture

```text
Input: CompoundSet + TargetCase + SemanticPolicyVersion
       │
       ├─ Compound-side Builders
       │    ├─ CompoundGraphCanonicalBuilder
       │    ├─ WarheadAnchorBuilder
       │    ├─ RigidityPersistenceBuilder
       │    ├─ CapPartitionBuilder
       │    ├─ BlockingBodyBuilder
       │    └─ AnchorableMotifBuilder
       │
       ├─ Protein-side Builders
       │    ├─ PathReferenceBuilder
       │    ├─ PocketFieldBuilder
       │    ├─ CatalyticFrameBuilder
       │    ├─ ProteinFlexibilityBuilder
       │    ├─ ResidueRoleMapBuilder
       │    └─ HomologyContextBuilder
       │
       ├─ Pose / Feasibility Shell
       │    ├─ MEF
       │    ├─ CPG
       │    └─ search-control staging
       │
       ├─ Cross-object Evaluators
       │    ├─ Rule1A PathObstructionEvaluator
       │    ├─ Rule1B ObstructionPersistenceEvaluator
       │    ├─ Rule2A CapEngagementEvaluator
       │    ├─ Rule2B CapMobilityEvaluator
       │    ├─ Rule3A AnchoringEvaluator
       │    └─ Rule3B CatalyticFrameDisruptionEvaluator
       │
       ├─ SCV core
       │
       └─ Final outputs: PASS / FAIL / UNCLEAR + evidence artifacts
```

Note: Builders and evaluators outside the initial implementation contract are deferred. See `v3_initial_implementation_contract.md` and `v3_deferred_appendix.md`.

### 7.1 Responsibility split

| Layer | Responsibility | Must not do |
|---|---|---|
| Compound builders | build compound-only semantic objects | use target-specific truth conditions |
| Protein builders | build protein-only semantic objects | use compound-specific truth conditions |
| Feasibility shell | generate feasible poses and exploration logs | reinterpret object logic |
| Cross-object evaluators | compute evidence over compound/protein objects | return final verdict |
| SCV | integrate evidence into PASS/FAIL/UNCLEAR | decide continuation policy |
| Staging policy | decide continue/finalize | alter object-logic meaning |

---

## 8. Compound-side semantic objects

### 8.4 `CapPartitionObject`

Deterministic molecule-level partition of the graph into:

- `warhead_region`
- `linker_region`
- `cap_primary`
- `cap_auxiliary[]`
- `ambiguous_nodes[]`

Rules:

1. Cap partition is computed before pose evaluation.  
2. Cap partition must not vary by proposal or pose.  
3. Ambiguity is represented explicitly, not silently collapsed.

### 8.x Deferred objects

Compound-side objects other than `CapPartitionObject` are deferred. See `v3_deferred_appendix.md`.

---

## 9. Protein-side semantic objects

### 9.1 `PathReferenceField`

Canonical representation of apo or ensemble-derived access / transport geometry.

#### 9.1.1 Path family taxonomy

v3.x formally recognizes at least the following path families:

- `TUNNEL`
- `SURFACE_LIKE`
- `PORE_CHANNEL`
- `TRANSIENT_GATED`
- `SOLVENT_TRACED`
- `CAVITY_RELAY`

`TUNNEL` and `SURFACE_LIKE` are inherited from v4.3.2. The other families are allowed in v3.x as semantic object categories, but they require builder-specific contracts before production use.

### 9.3 `CatalyticFrameObject`

Defines the functional geometry of the catalytic apparatus as a **constraint set**, not a single point pose.

Typical contents:

- catalytic residue set
- pairwise distance constraints
- angular constraints
- orientation / exposure constraints
- optional substrate-approach compatibility constraints

### 9.x Deferred objects

Protein-side objects other than `PathReferenceField` and `CatalyticFrameObject` are deferred. See `v3_deferred_appendix.md`.

---

## 10. External tool integration policy

External tools may be used **only** as builder aids or auxiliary evidence sources.
Note: external tool integration is deferred for initial implementation. See `v3_deferred_appendix.md`.

### 10.1 Allowed integration classes

| Tool class | Typical use in v3.x |
|---|---|
| DoGSiteScorer / fpocket / mdpocket | pocket and cavity field support |
| PLIP | cross-contact observation support |
| Foldseek | homology context support |
| PDBFlex or analogous ensemble resources | flexibility hints only |
| CAVER / MOLE | tunnel / channel / pore support |
| trajectory / solvent-tracking tools | transient or solvent-traced path support |

### 10.2 Restrictions

- tool output does not automatically become the truth source of a Rule  
- tool versions, parameters, and ingestion policy must be recorded in `tool_source_manifest`  
- external server volatility must not silently alter v3.x semantics  
- stale or weakly maintained resources may only be used as low-weight auxiliary evidence

---

## 11. Cross-object evaluators (Rule redesign)

## 11.1 Rule 1: path-blocking

Rule 1 is split into two evaluators.

### 11.1.1 `Rule1A = PathObstructionEvaluator`

Input:

- `BlockingBodyObject`
- `PathReferenceField`
- pose geometry

Output:

- obstruction evidence by path family
- obstructed path-family IDs
- local obstruction witness geometry

Note: `BlockingBodyObject` is deferred for initial implementation (see `v3_deferred_appendix.md`).

### 11.1.2 `Rule1B = ObstructionPersistenceEvaluator`

Input:

- `RigidityPersistenceObject`
- Rule1A output

Output:

- persistence evidence
- confidence that obstruction is not merely transient or structurally fragile

Note: `RigidityPersistenceObject` is deferred for initial implementation (see `v3_deferred_appendix.md`).

#### 11.1.3 Semantic meaning

Rule 1 is no longer “molecule rigidity.” It is “does this molecule obstruct a canonical path family, and is that obstruction plausibly persistent under the current modeling assumptions?”

#### 11.1.4 Prohibitions

- rigidity must not be used as a silent proxy for path identity  
- path family must not be pose-defined after the fact  
- obstruction and persistence must not be collapsed into an opaque scalar without separate artifact fields

## 11.2 Rule 2: cap-interaction

Rule 2 is split into identity, engagement, and mobility semantics.

### 11.2.1 `Rule2A = CapIdentityEstablished`

This is a validation precondition over `CapPartitionObject`, not itself a public verdict rule.

### 11.2.2 `Rule2B = CapEngagementEvaluator`

Input:

- `CapPartitionObject`
- `PocketField`
- contact observations

Output:

- cap-to-pocket engagement evidence
- supporting contact topology

Note: `PocketField` is deferred for initial implementation (see `v3_deferred_appendix.md`).

### 11.2.3 `Rule2C = CapMobilityEvaluator`

Input:

- `CapPartitionObject`
- `ProteinFlexibilityField`
- pose contact regime

Output:

- mobility / wobble evidence
- likely constrained vs escaping cap behavior

Note: `ProteinFlexibilityField` is deferred for initial implementation (see `v3_deferred_appendix.md`).

#### 11.2.4 Semantic meaning

Rule 2 no longer means “an informal distal group motion guess.” It means “given a fixed Cap identity, what engagement and mobility evidence exists at the pocket / protein interface?”

## 11.3 Rule 3: anchoring and catalytic disruption

Rule 3 is split into two independent evidence channels.

### 11.3.1 `Rule3A = AnchoringEvaluator`

Input:

- `AnchorableMotifObject`
- local protein geometry
- pose geometry

Output:

- anchoring witness
- local interaction support

Note: `AnchorableMotifObject` is deferred for initial implementation (see `v3_deferred_appendix.md`).

### 11.3.2 `Rule3B = CatalyticFrameDisruptionEvaluator`

Input:

- compound pose
- `CatalyticFrameObject`

Output:

- catalytic-frame disruption evidence
- violated constraint subset
- severity / support metadata

#### 11.3.3 Semantic meaning

Rule 3 is not merely “did it anchor?” It becomes “did it anchor, and independently, did it perturb catalytic geometry relevant to function?”

#### 11.3.4 Same-pose policy

v3.0 does **not** require `Rule3A` and `Rule3B` to share the same pose witness. If a future ADR proposes same-pose or witness-equivalence requirements, that ADR must define:

- the execution-significant predicate
- the artifact contract
- the replay envelope
- the validation failures that would falsify the policy

---

## 12. SCV integration policy

### 12.1 Core rule

`SCV` remains the only component that returns public verdicts.

### 12.2 Inputs to SCV in v3.x

SCV receives evaluator outputs, not raw builder objects.

### 12.3 Search-control boundary retained

`terminal policy` remains outside object logic. Staging, budget continuation, and terminal normalization must not silently redefine Rule 1–3 semantics.

### 12.4 Reverse-flow policy

CoreSCV reverse-flow is **not allowed** in this SoT. A future ADR may propose an evidence-demand loop, but it must preserve the asymmetry that SCV does not become a proposal controller.

---

## 13. Artifact contract (v3.x)

### 13.1 Compound-side artifacts

- `compound_graph_canonical.json`
- `compound_warhead_anchor.json`
- `compound_rigidity_profile.json`
- `compound_cap_partition.json`
- `compound_blocking_body.json`
- `compound_anchorable_motifs.json`

### 13.2 Protein-side artifacts

- `protein_path_reference.json`
- `protein_pocket_field.json`
- `protein_catalytic_frame.json`
- `protein_flexibility_field.json`
- `protein_residue_role_map.json`
- `protein_homology_context.json` (optional)

### 13.3 Cross-object evaluation artifacts

- `rule1_path_obstruction_eval.jsonl`
- `rule1_obstruction_persistence_eval.jsonl`
- `rule2_cap_engagement_eval.jsonl`
- `rule2_cap_mobility_eval.jsonl`
- `rule3_anchoring_eval.jsonl`
- `rule3_catalytic_frame_disruption_eval.jsonl`

### 13.4 Governance / replay artifacts

- `semantic_policy_version.json`
- `replay_contract_version.json`
- `comparison_semantics_descriptor.json`
- `builder_provenance.json`
- `tool_source_manifest.json`
- `migration_map.json` (if bridge mode is active)

### 13.5 Retained rc2 bridge artifacts

When running in bridge / shadow mode against the frozen line, the following rc2 artifacts remain required for comparability:

- `run_manifest.json`
- `output_inventory.json`
- `run_monitor.json`
- `replay_audit.json`
- `mapping_table.parquet`
- `falsification_table.parquet`
- `theta_rule1_resolution.json`
- `rule3_trace_summary.json`

### 13.6 Current rc2 representative top-level schemas (frozen reference)

The following run-level JSON families are confirmed from benchmark and production representative runs and are treated as the minimum bridge-aware schema surface for v3.x migration tooling.

#### 13.6.1 `run_manifest.json`

Top-level keys confirmed in both representative benchmark and production runs:

- `bootstrap_seed`
- `completion_basis_json`
- `compound_order_hash`
- `config_hash`
- `cv_seed`
- `donor_plan_hash`
- `functional_score_dictionary_id`
- `generated_outputs`
- `implemented_branches`
- `input_hash`
- `label_shuffle_seed`
- `library_hash`
- `library_path`
- `repo_root_resolved_path`
- `repo_root_source`
- `requested_branches`
- `requirements_hash`
- `resource_profile`
- `rotation_seed`
- `run_id`
- `run_mode`
- `shuffle_donor_pool_hash`
- `shuffle_seed`
- `shuffle_universe_scope`
- `spec_version`
- `stageplan_path`
- `staging_plan_hash`
- `structure_file_digest`
- `structure_path`
- `target_case_id`
- `target_config_allowed_comparisons`
- `target_config_expected_use`
- `target_config_frozen_for_regression`
- `target_config_path`
- `target_config_role`
- `theta_rule1_runtime_contract`
- `theta_rule1_table_digest`
- `theta_rule1_table_id`
- `theta_rule1_table_source`
- `theta_rule1_table_version`

#### 13.6.2 `output_inventory.json`

Top-level keys confirmed in both representative benchmark and production runs:

- `branch_status_json`
- `completion_basis_json`
- `completion_checks_json`
- `generated_outputs`
- `implemented_branches`
- `missing_outputs`
- `repo_root_resolved_path`
- `repo_root_source`
- `requested_branches`
- `run_id`
- `run_mode`
- `run_mode_complete`
- `schema_validation`
- `warnings`

#### 13.6.3 `run_monitor.json`

Top-level keys confirmed in both representative benchmark and production runs:

- `artifacts`
- `command`
- `elapsed_s`
- `end_utc`
- `exit_code`
- `output_inventory`
- `replay_audit`
- `run_id`
- `run_manifest`
- `start_utc`

#### 13.6.4 `replay_audit.json`

Top-level keys confirmed in both representative benchmark and production runs:

- `cap_invariant_consistency`
- `cap_invariant_errors`
- `cap_invariant_warnings`
- `cap_truth_source_consistency`
- `cap_truth_source_digest`
- `cap_truth_source_keys`
- `cap_truth_source_layer_consistency`
- `cap_truth_source_path`
- `cap_truth_source_reconciliation_consistency`
- `cap_truth_source_reconciliation_errors`
- `cap_truth_source_reconciliation_warnings`
- `cap_truth_source_run_id`
- `cap_truth_source_status`
- `comparison_type`
- `comparison_type_source`
- `donor_plan_consistency`
- `fold_map_consistency`
- `hash_consistency`
- `inventory_branch_status_consistency`
- `inventory_completion_basis_consistency`
- `inventory_completion_checks_consistency`
- `inventory_completion_checks_schema_errors`
- `inventory_completion_consistency`
- `inventory_consistency`
- `inventory_drift_reason_codes`
- `inventory_generated_outputs_consistency`
- `inventory_json_audit_status`
- `inventory_json_errors`
- `inventory_json_max_severity`
- `inventory_missing_outputs_consistency`
- `inventory_run_mode_complete`
- `manifest_missing_generated_outputs`
- `manifest_missing_required_outputs`
- `missing_generated_outputs`
- `pathyes_diagnostics_error_code`
- `pathyes_diagnostics_source`
- `pathyes_diagnostics_status`
- `pathyes_goal_precheck_passed`
- `pathyes_mode_requested`
- `pathyes_mode_resolved`
- `pathyes_rule1_applicability`
- `pathyes_skip_code`
- `pathyes_state_source`
- `result`
- `rule3_trace_ordering_distribution`
- `rule3_trace_proposal_handling_totals`
- `rule3_trace_summary_available`
- `rule3_trace_summary_record_count`
- `rule3_trace_summary_top_n_limit`
- `run_id`
- `seed_consistency`
- `skip_reason_codes`
- `spec_version`
- `stage_history_recorded`
- `stale_manifest_detected`
- `theta_rule1_consistency`
- `theta_rule1_resolution_available`
- `theta_rule1_resolution_status`
- `theta_rule1_resolved_lookup_key`
- `theta_rule1_validator_errors`
- `theta_rule1_validator_warning`

These keys are normative for bridge compatibility at the migration boundary, even if v3.x adds side-separated artifacts and semantic-policy governance files.


#### 13.6.5 `mapping_table.parquet` (confirmed rc2 schema)

Confirmed columns in the representative rc2 runs, all nullable:

- `canonical_link_id: string`
- `molecule_id: string`
- `target_id: string`
- `condition_hash: string`
- `functional_score_raw: double`
- `assay_type: string`
- `direction: string`
- `unit: string`
- `functional_score: double`
- `comb: double`
- `P_hit: double`
- `PAS: double`
- `dist: double`
- `LPCS: double`
- `PCF: double`
- `pairing_role: string`
- `functional_score_dictionary_id: string`

`mapping_table.parquet` is therefore the minimal rc2 assay-link mapping surface that v3.x bridge tooling must continue to read.

#### 13.6.6 `falsification_table.parquet` (confirmed rc2 schema)

Confirmed columns in the representative rc2 runs, all nullable:

- `canonical_link_id: string`
- `molecule_id: string`
- `target_id: string`
- `condition_hash: string`
- `functional_score_raw: double`
- `assay_type: string`
- `direction: string`
- `unit: string`
- `functional_score: double`
- `comb: double`
- `P_hit: double`
- `PAS: double`
- `dist: double`
- `LPCS: double`
- `PCF: double`
- `pairing_role: string`
- `shuffle_donor_pool_hash: string`
- `donor_plan_hash: string`
- `functional_score_dictionary_id: string`

Relative to `mapping_table.parquet`, the confirmed additional bridge-relevant columns are:

- `shuffle_donor_pool_hash`
- `donor_plan_hash`

These fields are normative for replay-aware falsification comparison in v3.x bridge mode.

#### 13.6.6A Confirmed rc2 row-generation rules for `mapping_table.parquet`

Current generation is reported to come from `crisp/v29/cap/mapping.py` and to be invoked from integrated execution via `crisp/v29/cli.py`. The confirmed row-level rules are:

- input sources are `pair_features_rows` and `assays_rows`
- keep only rows with `pairing_role == "native"`
- group by `canonical_link_id`
- assay rows are joined by `canonical_link_id`; if no assay exists, that link is dropped
- `functional_score_raw` is converted to `functional_score` via the dictionary rule in `mapping.py`; precedence is `direction` first, then `assay_type`
- raw rows that do not match the dictionary rule are dropped
- `comb`, `P_hit`, `PAS`, `dist`, `LPCS`, and `PCF` are averaged within group
- `molecule_id` and `target_id` are taken from the first row in the group
- output `pairing_role` is always `"native"`
- output `functional_score_dictionary_id` is always `"functional-score-dict-v1"`

Implication for v3.x: bridge tooling must preserve both the grouping grain (`canonical_link_id`) and the functional-score dictionary identity. Silent reinterpretation of score aggregation would be a semantic drift, not a reporting change.

#### 13.6.6B Confirmed rc2 row-generation rules for `falsification_table.parquet`

Current generation is reported to come from `crisp/v29/cap/falsification.py` and to be invoked from integrated execution via `crisp/v29/cli.py`. The confirmed row-level rules are:

- keep only rows with `pairing_role == "matched_falsification"`
- output `pairing_role` is always `"matched_falsification"`
- score conversion and within-group averaging follow the same rules as `mapping_table.parquet`
- if `donor_plan` is present, `shuffle_donor_pool_hash` and `donor_plan_hash` are attached to all output rows

Implication for v3.x: falsification rows carry donor-plan provenance as part of the replay boundary. Any redesign of Cap evidence that still claims bridge comparability must preserve this provenance or declare an explicit incompatibility.

Confirmed related current tests supplied by the user:

- `test_mapping_table.py`
- `test_falsification_table.py`
- `test_cap_invariants.py`

#### 13.6.7 `theta_rule1_resolution.json` (confirmed rc2 schema and meaning)

Confirmed keys in both representative benchmark and production runs:

- `benchmark_config_hash_observed`
- `benchmark_config_loaded`
- `benchmark_config_path_resolved`
- `benchmark_config_role_observed`
- `calibration_metadata`
- `current_config_path`
- `current_config_role`
- `current_pathway`
- `current_target_name`
- `resolution_candidates`
- `resolution_status`
- `resolved_lookup_key`
- `run_id`
- `runtime_contract`
- `scope_mismatch_fields`
- `table_digest`
- `table_id`
- `table_source`
- `table_status`
- `table_version`
- `theta_rule1`
- `theta_runtime_fallback_used`
- `theta_runtime_policy`
- `theta_runtime_policy_reason`
- `validator_errors`
- `validator_warnings`

Confirmed representative values show the following frozen rc2 meaning surface:

- `runtime_contract = "crisp.v29.theta_rule1.runtime/v1"`
- `resolution_status = "exact_target"`
- `resolved_lookup_key = "9KR6_CYS328"`
- `table_version = "2026-04-03"`
- `theta_rule1 = 0.8`
- `theta_runtime_fallback_used = false`
- `theta_runtime_policy = "required"`

Implication for v3.x: the bridge must treat rc2 `theta_rule1_resolution.json` as a **resolved-threshold provenance artifact**, not as evidence that Rule 1 already encoded path obstruction semantics.

#### 13.6.8 `rule3_trace_summary.json` (confirmed rc2 schema and meaning)

Confirmed top-level keys in both representative benchmark and production runs:

- `summary_version: string`
- `record_count: integer`
- `top_n_limit: integer`
- `run_summary: object`
- `compound_summaries: array<object>`

Confirmed `run_summary` keys:

- `candidate_order_hash_distribution`
- `ordering_distribution`
- `proposal_handling_totals`
- `proposal_policy_version_counts`
- `semantic_mode_counts`
- `source_presence_counts`

Confirmed `compound_summaries[]` keys:

- `candidate_count`
- `candidate_order_hash`
- `molecule_id`
- `near_band_triggered`
- `ordering_label`
- `ordering_sources`
- `proposal_handling_counts`
- `proposal_handling_trace`
- `proposal_policy_version`
- `semantic_mode`
- `source_count_by_type`
- `struct_conn_status`
- `target_id`
- `top_n_limit`
- `top_n_proposals`
- `unique_candidate_count`

Confirmed representative values show the current rc2 semantic state:

- `summary_version = "rule3_trace_summary/v1"`
- `top_n_limit = 3`
- `ordering_distribution = [{"ordering_label":"none","count":N}]`
- `proposal_handling_totals = {"skip_no_candidates": N}`
- representative `proposal_policy_version = "v29.trace-only.noop"`
- representative `semantic_mode = "trace-only-noop"`

Implication for v3.x: `rule3_trace_summary.json` is a **trace-only observational artifact** in rc2. Any proposal-connected Rule 3 evolution must therefore be treated as a semantic delta with a new artifact / replay contract, not as a minor extension of an already execution-significant contract.

#### 13.6.8A Confirmed `rule3_trace_summary.json` field semantics

Current source assignment is reported in `crisp/v29/anchor_proposal/candidate_sources.py`, proposal trace capture in `crisp/v29/anchor_proposal/trace.py`, and summary generation in `crisp/v29/rule3_trace.py`. Confirmed meanings include:

- `summary_version`: current trace summary schema version; representative runs use `rule3_trace_summary/v1`
- `top_n_limit`: summary top-N window; representative runs use `3`
- `record_count`: number of compounds summarized
- `run_summary.ordering_distribution`: aggregate distribution of source-ordering patterns
- `run_summary.proposal_handling_totals`: aggregate handling reasons across compounds
- `candidate_order_hash`: stable hash over candidate atom order
- `ordering_sources`: per-candidate source labels
- `ordering_label`: `ordering_sources` joined by `>`; empty source list becomes `none`
- `candidate_count`: ordered candidate count
- `unique_candidate_count`: deduplicated candidate count
- `struct_conn_status`: whether a `struct_conn` source was present
- `near_band_triggered`: whether a `near_band` source was present
- `proposal_policy_version`: current representative value is `v29.trace-only.noop`
- `semantic_mode`: current representative value is `trace-only-noop`
- `top_n_proposals`: diagnostics for proposals inside the summary top-N window
- `proposal_handling_trace`: per-proposal handling history
- `proposal_handling_counts`: aggregated counts over that history

Confirmed handling-status meanings:

- `selected_top_n`: selected within the top-N window
- `pruned_duplicate_atom`: pruned because the atom was already selected
- `exhausted_top_n_window`: non-duplicate but outside the top-N window
- `skip_no_candidates`: no candidates existed

Normative bridge interpretation: these are **trace-only diagnostics** and do not flow back into verdicts or SCV on the rc2 line. v3.x must preserve that interpretation unless and until a dedicated ADR defines a new execution-significant proposal policy.

Confirmed related current tests supplied by the user:

- `test_rule3_trace.py`
- `test_replay_audit.py`

---

## 14. Replay contract

### 14.1 General rule

No v3.x semantic change is eligible for merge unless the affected artifact and replay contract are enumerated before coding.

### 14.2 Minimum replay checks

A v3.x replay must verify at least:

- semantic-policy version match
- builder provenance match
- tool-source manifest match or allowed-drift declaration
- deterministic regeneration of compound-side objects
- deterministic regeneration of protein-side objects under the declared source set
- evaluator output reproducibility under the declared contract

### 14.3 Bridge comparator

During migration, a dual-run comparator must support:

- `rc2 frozen reference` vs `v3.x shadow`
- run-level semantic drift summaries
- evidence-level drift attribution
- operator-facing separation of `frozen` and `exploratory` verdict claims

---

## 15. Repo structure

### 15.1 Current repo root supplied for alignment

Current repo root supplied by the user:

```text
D:\CRISPv2.9.5
├─ .git/
├─ .github/
├─ .pytest_cache/
├─ .uv-cache/
├─ .uv-verify/
├─ .venv/
├─ audit/
├─ configs/
├─ crisp/
├─ crisp.egg-info/
├─ data/
├─ docs/
├─ manifests/
├─ outputs/
├─ scripts/
├─ tests/
├─ .editorconfig
├─ .gitattributes
├─ .gitignore
├─ .python-version
├─ attic/
├─ pyproject.toml
├─ README.md
├─ uv.lock
└─ uv.toml
```

### 15.2 Current `crisp/` module tree supplied for alignment

```text
crisp/
  __init__.py
  reason_codes.py

  cli/
    __init__.py
    main.py
    mef.py
    phase1.py
    regression.py
    v29.py

  config/
    __init__.py
    loader.py
    models.py

  cpg/
    __init__.py
    engine.py
    geometry.py
    structure.py

  evidence/
    __init__.py
    writer.py

  mef/
    __init__.py
    filter.py
    warheads.py

  models/
    __init__.py
    runtime.py

  repro/
    __init__.py
    hashing.py
    manifest.py

  scv/
    __init__.py
    core.py

  sensors/
    __init__.py
    anchoring.py
    offtarget.py

  staging/
    __init__.py
    policy.py

  utils/
    jsonx.py

  v29/
    __init__.py
    cap_reporting.py
    cap_truth.py
    cli.py
    console.py
    contracts.py
    core_bridge.py
    inputs.py
    manifest.py
    ops_guard.py
    pathyes.py
    repo.py
    rule1.py
    rule1_theta.py
    rule3_trace.py
    runtime_contract.py
    sidecar_policy.py
    tableio.py
    validation.py
    validators.py
    writers.py

    anchor_proposal/
      __init__.py
      candidate_sources.py
      policy.py
      trace.py

    cap/
      __init__.py
      falsification.py
      layer0.py
      layer1.py
      layer2.py
      mapping.py
      scv.py

    planning/
      __init__.py
      donor_plan.py
      pair_plan.py

    reports/
      __init__.py
      collapse_figure_spec.py
      contract.py
      eval_report.py
      qc_report.py
      replay_audit.py
```

### 15.3 Current CLI entry points supplied for alignment

`pyproject.toml` currently exposes the following console scripts:

- `crisp = "crisp.cli.main:main"`
- `crisp-regression = "crisp.cli.regression:main"`
- `crisp-v29 = "crisp.cli.v29:main"`

Current command surface supplied by the user:

- `crisp` subcommands: `doctor`, `validate-target-config`, `assert-regression-config`, `assert-config-comparison`, `print-hashes`, `write-run-manifest`, `run-phase1-single`, `run-mef-library`, `run-phase1-library`, `run-integrated-v29`, `run-replay-audit-v29`, `run-validation-v29`
- `crisp-regression` subcommands: `run-mef-library`, `run-phase1-single`, `run-phase1-library`, `run-integrated-v29`
- `crisp-v29` subcommands: `benchmark`, `smoke`, `production`, `lowsampling`

The current integrated v2.9.5 execution entry is reported to be `crisp/v29/cli.py:run_integrated_v29`.

#### 15.3.1 Confirmed comparison taxonomy in current config layer

The current comparison enum supplied by the user is:

- `none`
- `same-config`
- `cross-regime`

Implication for v3.x: any redesign of comparison semantics remains ADR-gated and must not silently overload the current enum meanings inherited from `rc2`.

#### 15.3.2 Confirmed `crisp-v29` contract surface

Shared arguments:

- `--repo-root?`
- `--config`
- `--library`
- `--stageplan`
- `--integrated?`
- `--out`
- `--caps?`
- `--assays?`
- `--run-mode {core-only, core+rule1, core+rule1+cap, full, rule1-bootstrap}`
- `--comparison-type?`

Confirmed operational contract:

- `--config` must match the subcommand role
- `--caps` is required for `core+rule1+cap` and `full`
- `--assays` is required for `full`
- `full` is treated as a local heavy-run
- `--comparison-type` must fail fast if it conflicts with the role policy

Implication for v3.x: role-safe CLI behavior is part of the frozen operator boundary and should be preserved or versioned explicitly, not weakened informally.

#### 15.3.3 Confirmed `crisp-regression` contract surface

`crisp-regression` is a regression-ready wrapper over benchmark-safe execution. Confirmed subcommands and contracts:

- `run-mef-library --config --library --run-id`
- `run-phase1-single --config --smiles`
- `run-phase1-library --config --library --run-id --stageplan [--prefilter-report] [--progress-every] [--progress-seconds] [--no-progress]`
- `run-integrated-v29 --repo-root? --config --library --stageplan --integrated? --out --caps? --assays? --run-mode {...}`

Benchmark-external configs are rejected before execution. This confirms that regression wrappers are part of the current role-safe boundary.

#### 15.3.4 Confirmed `crisp` contract surface

The general CLI currently exposes:

- `doctor`
- `validate-target-config --config`
- `assert-regression-config --config`
- `assert-config-comparison --lhs-config --rhs-config --comparison-type`
- `print-hashes --config --smiles`
- `write-run-manifest --config --stageplan --library --run-id --out`
- `run-phase1-single --config --smiles [--require-frozen-for-regression]`
- `run-mef-library --config --library --run-id [--require-frozen-for-regression]`
- `run-phase1-library --config --library --run-id --stageplan [--prefilter-report] [--progress-every] [--progress-seconds] [--no-progress] [--require-frozen-for-regression]`
- `run-integrated-v29 --repo-root? --config --library --stageplan --integrated? --out --caps? --assays? --run-mode {...} [--require-frozen-for-regression]`
- `run-replay-audit-v29 --manifest`
- `run-validation-v29 --manifest [--profile=smoke] --out`

Implication for v3.x: replay audit and validation are first-class CLI surfaces already, so migration should extend them rather than burying replay under ad hoc scripts.

### 15.4 v3.x canonical repo structure (normative)

```text
D:\CRISPv3x
├─ .github/
├─ audit/
│  ├─ adr/
│  ├─ reviews/
│  └─ migration/
├─ configs/
│  ├─ targets/
│  ├─ semantic_policies/
│  ├─ benchmark_panels/
│  └─ toolchains/
├─ crisp/
│  ├─ builders/
│  │  ├─ compound/
│  │  ├─ protein/
│  │  └─ shared/
│  ├─ evaluators/
│  │  ├─ rule1/
│  │  ├─ rule2/
│  │  ├─ rule3/
│  │  └─ shared/
│  ├─ shell/
│  │  ├─ mef/
│  │  ├─ cpg/
│  │  ├─ staging/
│  │  └─ replay/
│  ├─ scv/
│  ├─ artifacts/
│  ├─ io/
│  ├─ bench/
│  └─ cli/
├─ data/
│  ├─ structures/
│  ├─ libraries/
│  ├─ benchmark_panels/
│  └─ tool_cache/
├─ docs/
│  ├─ sot/
│  ├─ adr/
│  ├─ schemas/
│  └─ operator/
├─ manifests/
│  ├─ runs/
│  ├─ migrations/
│  └─ benchmark_suites/
├─ outputs/
│  ├─ compound_observations/
│  ├─ protein_observations/
│  ├─ cross_evaluations/
│  ├─ scv_runs/
│  ├─ replay_audits/
│  └─ bridge_comparisons/
├─ scripts/
│  ├─ migration/
│  ├─ benchmarking/
│  └─ audits/
├─ tests/
│  ├─ unit/
│  ├─ smoke/
│  ├─ integration/
│  ├─ replay/
│  ├─ migration/
│  └─ benchmark/
├─ pyproject.toml
├─ uv.lock
├─ uv.toml
└─ README.md
```

### 15.5 Mapping principle

The current v2.9.5 repo may remain in place physically, but v3.x design work should converge toward the canonical separation above. In particular, side-separated outputs and builder/evaluator separation are normative, even if initial prototypes are implemented as sidecars within the current tree.

A conservative migration mapping from the supplied current tree is:

- `crisp.mef.*`, `crisp.cpg.*`, `crisp.staging.*`, `crisp.scv.core` remain the shell/core backbone
- `crisp.sensors.*` and `crisp.v29.rule1`, `crisp.v29.cap.*`, `crisp.v29.rule3_trace` are current semantic-adjacent entry points that should be decomposed into builders and evaluators rather than extended in place semantically
- `crisp.v29.cap_truth`, `crisp.v29.cap_reporting`, `crisp.v29.reports.replay_audit`, `crisp.v29.manifest`, `crisp.v29.writers`, and `crisp.evidence.writer` are current artifact/reporting-adjacent modules that should inform v3.x artifact governance and migration tooling
- `crisp.repro.*` and `crisp.v29.runtime_contract` should seed `semantic_policy_version`, replay contracts, and bridge comparator provenance handling
- `crisp.v29.anchor_proposal.*` should remain shell-side unless and until a dedicated ADR reclassifies proposal-connected behavior as execution-significant object logic

This mapping is design guidance only; it is not permission to reinterpret current `v2.9.5` module semantics retroactively.

---

## 16. Benchmark and validation hierarchy

### 16.1 Tiering

- `Tier 0`: rc2 frozen reference suite  
- `Tier 1`: SARS-CoV-2 Mpro semantic-object benchmark panel  
- `Tier 2`: SARS-CoV-2 PLpro semantic-object benchmark panel  
- `Tier 3`: target-specific deployment panels (e.g. orthopox I7L or analogous systems)

### 16.2 Purpose of the external benchmark tiers

The role of Mpro / PLpro in v3.x is not to redefine CRISP’s clinical meaning. Their role is to supply data-rich, structurally rich, falsification-friendly systems for semantic-object validation.

### 16.3 Validation categories

- deterministic builder tests  
- evaluator truth-condition tests  
- replay audit tests  
- bridge comparator tests  
- benchmark full shadow runs  
- production full shadow runs  
- artifact migration tests

---

## 17. Migration strategy from rc2

### 17.1 Stage 1: ADR lock

Before any coding, define:

- semantic delta
- affected artifacts
- replay contract
- benchmark / cross-regime guard implications

### 17.2 Stage 2: sidecar builders

Introduce compound-side and protein-side builders as sidecars without changing public rc2 verdict semantics.

### 17.3 Stage 3: shadow evaluators

Run Rule 1–3 v3 evaluators in shadow mode alongside the frozen rc2 line.

### 17.4 Stage 4: bridge comparator

Generate per-run drift reports, evidence-level drift attribution, and operator-facing explanatory summaries. Current implementation status may legitimately be **Path-only partial comparator** rather than full-channel migration comparator, provided the report explicitly marks `path_only_partial` / `partially_comparable` and does not claim full verdict comparability.

Implementation note for the current Path-first milestone:
- `output_inventory.json` remains an rc2-frozen artifact and is not extended by v3 sidecar artifacts at this stage.
- The canonical sidecar inventory source is `v3_sidecar/generator_manifest.json`.
- `verdict_record.json` and comprehensive migration inventory remain deferred until full-channel bridge semantics are defined.
- When `rc2_bridge_pointers.json` is not materialized, bridge comparison artifacts must still record rc2 source paths and digests in `sidecar_run_record.json` or `bridge_comparison_summary.json`.

### 17.5 Stage 5: selective promotion

Only after replay and falsification thresholds are met may individual v3 evaluators be proposed for first-class SCV integration.

---

## 18. Operator model / CI model

### 18.1 Split suites

CI must keep two clearly separated suites:

- `rc2-frozen`
- `v3x-exploratory`

### 18.2 Current `.github/` alignment supplied for the frozen line

The current repository is reported to contain one workflow:

```text
.github/
  workflows/
    v29-required-matrix.yml
```

Confirmed current required jobs:

- `required / benchmark-integrated-smoke` -> `tests/v29/test_9kr6_benchmark_smoke.py`
- `required / production-integrated-smoke` -> `tests/v29/test_9kr6_production_smoke.py`
- `required / ci-sized-full-fixture` -> `tests/v29/test_cli_full_smoke.py`, `tests/v29/test_cap_assay_fixtures.py`
- `required / config-guard-matrix` -> `tests/test_cli_config_guards.py`, `tests/test_config_taxonomy.py`
- `required / replay-inventory-crosscheck` -> `tests/v29/test_replay_audit.py`, `tests/v29/test_manifest_inventory.py`, `tests/v29/test_report_contract_matrix.py`
- `required / cap-artifact-invariants` -> `tests/v29/test_cap_invariants.py`
- `required / v2.9.5-matrix` -> aggregate gate

Confirmed shared execution environment for all jobs:

- `windows-latest`
- `actions/checkout@v4`
- `actions/setup-python@v5`
- `astral-sh/setup-uv@v6`
- `uv sync --frozen`

Implication for v3.x: Windows-based role-safe and replay-safe CI is part of the frozen operational boundary. A v3.x workflow may add exploratory jobs, but must not silently weaken the frozen matrix.

### 18.3 Current `tests/` alignment supplied for the frozen line

Confirmed current test tree:

```text
tests/
  conftest.py
  v29_smoke_helpers.py
  test_cli_config_guards.py
  test_config_taxonomy.py
  test_manifest_config_metadata.py
  test_reason_codes.py
  test_regression_wrapper.py
  test_repro_hashing.py
  test_role_safe_cli.py
  test_role_safe_cli_help.py
  v29/
    test_9kr6_benchmark_smoke.py
    test_9kr6_production_smoke.py
    test_batch_scv.py
    test_cap_assay_fixtures.py
    test_cap_invariants.py
    test_cap_layer0_layer1.py
    test_cap_reporting.py
    test_cap_writer.py
    test_cli_full_smoke.py
    test_cli_modes.py
    test_falsification_table.py
    test_inputs_and_modes.py
    test_layer2_models.py
    test_manifest_inventory.py
    test_mapping_table.py
    test_ops_guards.py
    test_pathyes_adapter.py
    test_pathyes_pat_backed.py
    test_replay_audit.py
    test_repo.py
    test_report_contract_matrix.py
    test_reports.py
    test_rule1_sensor.py
    test_rule1_theta_runtime.py
    test_rule3_trace.py
    test_sidecar_policy.py
    test_validation_batch.py
```

Confirmed current grouping:

- config / taxonomy / CLI guard
- core repro / manifest
- v29 smoke / integration
- Cap / Layer2 / invariants
- replay / reports / sidecars
- Rule1 / PathYes / ops
- Rule3

Representative test names supplied by the user confirm frozen-line intent:

- `test_mapping_table_contains_native_only`
- `test_mapping_table_averages_multiple_pairs_per_link`
- `test_falsification_table_records_donor_plan_hashes`
- `test_summarize_proposal_trace_distinguishes_selected_pruned_and_exhausted`
- `test_build_rule3_trace_summary_reports_run_level_ordering_distribution`
- `test_run_integrated_v29_requires_managed_theta_table_for_pat_backed_rule1`
- `test_replay_audit_reads_rule3_trace_summary_sidecar`
- `test_validate_cap_truth_source_reconciliation_rejects_report_digest_drift`

Implication for v3.x: migration must preserve not only artifact presence but also the invariant intent encoded by these tests.

### 18.4 Display rule

Operator-facing reports must always show `semantic_policy_version` and must never silently commingle verdicts produced under different semantic-policy versions.

For the current Path-first milestone, this requirement applies at minimum to:
- `semantic_policy_version.json`
- `sidecar_run_record.json`
- `builder_provenance.json`
- `bridge_operator_summary.md`
- any `eval_report` / `qc_report` section that renders v3 exploratory content

Current display freeze:
- any rendered v3 sidecar summary must visibly include `[exploratory]`
- Cap / Catalytic sidecar materialization must not be displayed as full verdict comparability
- current Rule 3 Catalytic handling remains a sidecar observational constraint set, not a new object-logic predicate

### 18.5 Safety rule

A passing v3.x exploratory suite does not redefine the meaning of an rc2 PASS or FAIL.

---

## 19. Explicit prohibitions

The following are prohibited under this SoT unless a later ADR overrides them explicitly.

1. Reinterpreting rc2 artifacts as though they already encode v3.x semantics  
2. Smuggling object-logic change into search-control tuning  
3. Treating external tool output as an unqualified truth source  
4. Introducing same-pose requirement without a dedicated predicate and replay envelope  
5. Introducing CoreSCV reverse-flow without a dedicated architecture ADR  
6. Redefining benchmark / production semantics without an operator-model ADR

---

## 20. Required follow-up ADRs

The following ADRs are required before v3.x semantic coding is complete.

- ADR: semantic-policy versioning
- ADR: side-separated observation contract
- ADR: Rule 1 path obstruction / persistence split
- ADR: Rule 2 deterministic Cap partition and engagement / mobility split
- ADR: Rule 3 anchoring vs catalytic-frame disruption split
- ADR: bridge comparator and migration contract
- ADR: operator / CI semantic-policy separation

Status note (Path-first milestone): the bridge comparator / migration contract ADR and the operator / CI semantic-policy separation ADR may be treated as **resolved for Path-only partial comparator scope**. Full-channel migration contract, full verdict comparability, and promotion criteria remain open until Cap/Catalytic coverage and final bridge semantics are completed.

Current-sidecar freeze note:
- [v3_07_rule3_catalytic_contract_freeze.md](v3_07_rule3_catalytic_contract_freeze.md) freezes the present `Path + Cap + Catalytic` sidecar boundary without authorizing proposal-connected Rule 3 or full migration claims

Optional but likely later:

- ADR: witness equivalence vs same-pose requirement
- ADR: evidence-demand loop without SCV reverse-flow
- ADR: taxonomy / comparison semantics redesign

---

## 21. Release-candidate readiness judgment

This SoT is judged **release-candidate complete at the architecture level**. No additional repository information is required to freeze the semantic design itself. The currently confirmed inputs already cover the design-critical surfaces:

- inherited v4.3.1 / v4.3.2 invariants and responsibility split
- rc2 boundary and deferred-topic entry rules
- current repo root, `crisp/` module tree, CLI entry points, workflow, and tests
- rc2 representative run-level JSON schemas
- rc2 Cap table schemas and row-generation rules
- rc2 `theta_rule1_resolution.json` semantics
- rc2 `rule3_trace_summary.json` semantics and trace-only non-backflow contract

Accordingly, the architecture is now fixed enough to serve as the v3.x Source of Truth. Additional live-repo inventory may still improve implementation convenience, but it is **not** a prerequisite for adopting this document as the governing design reference.

The RC judgment rests on the following satisfied conditions.

1. Each semantic object has a schema and provenance rule.  
2. Each cross-object evaluator has defined inputs, outputs, and prohibitions.  
3. Artifact truth sources are enumerated.  
4. Replay checks are enumerated.  
5. CI / operator separation is declared.  
6. Repo structure is mapped to the current codebase.  
7. Migration from rc2 is staged and role-safe.  
8. Deferred semantic topics remain deferred unless raised through explicit ADR gates.

This document therefore qualifies as the **release-candidate v3.x semantic design SoT**. What remains after this point is primarily implementation alignment, not architecture discovery.

---

## 22. Non-blocking implementation notes

The following items may matter during coding or migration hardening, but they are **not** required to freeze the design. They are listed here to prevent them from being misread as missing architectural prerequisites.

- parser-level defaults, coercions, and backward-compatibility behavior for CLI flags beyond the confirmed contract surface
- exact validator severity policy inside `schema_validation`, `completion_checks_json`, and replay-audit validation paths
- exact row-order determinism policy for `mapping_table.parquet` and `falsification_table.parquet` after grouping when tie situations occur
- nested diagnostic detail for `top_n_proposals`, `source_count_by_type`, and any deeper Rule 3 trace objects not needed by the current replay contract
- whether selected `crisp.v29.*` modules can be lifted into v3.x builders/evaluators without semantic leakage
- current contents of `scripts/` and any local automation that may affect migration tooling

These are implementation-planning details, not reasons to reopen the semantic design.

Implementation status note: a current Path-first milestone may legitimately materialize `sidecar_run_record.json`, `observation_bundle.json`, and Path-only bridge comparison artifacts before any full-channel `verdict_record.json` or comprehensive migration inventory is introduced. Such staging does not weaken the semantic SoT as long as `semantic_policy_version` remains explicit and rc2 frozen outputs remain untouched.

---

## 23. Recommended working branch and seed commit

Recommended branch: `v3x/sot-semantic-objects-rc2-bridge-and-ci-contracts`  
Recommended seed commit message: `docs: finalize v3.x semantic objects SoT with rc2 bridge and CI contracts`
