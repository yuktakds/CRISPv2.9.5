# WP-1 / WP-2: Channel Formal Contracts, SCV Mapping Framework, and Schema Freeze

Status: accepted  
Date: 2026-04-09  
Parent: `adr_v3_10_full_migration_contract.md`  
Scope: ADR-V3-03 (Cap), ADR-V3-04 (Catalytic), channel-to-SCV-component mapping framework, verdict_record.json migration conditions, RunDriftReport canonical filename

---

## Part 1: WP-1 Deliverables

---

## ADR-V3-03: Cap Evidence Channel Formal Contract

### 1. Context

CapEvidenceChannel は SoT §11.2 Rule 2（cap engagement / mobility）の v3 実装であり、rev3.1 §F で二段階設計（propose / validate）が定義済みである。current status は materialized-but-not-comparable であり、`comparable_channels` への参加条件（P1 五条件）は未達である。

### 2. Semantic scope

CapEvidenceChannel は以下の evidence question に answer する。

> 「Cap 領域は pocket に対して安定的に engaged しているか、それとも mobile / escaping か？」

この question は rc2 の Anchoring Sensor や OffTarget Sensor とは**異なる evidence dimension** を扱う。rc2 には Cap engagement / mobility に相当する独立 sensor が存在しない。rc2 の Cap 解析（`cap/layer0`–`layer2`, `cap/scv`, `mapping.py`, `falsification.py`）は statistical evaluation であり、SCV の 3 component（scv_anchoring, scv_offtarget, scv_pat）のいずれにも直接対応しない。

### 3. Input contract

| input | source | deterministic? |
|---|---|---|
| molecular graph + warhead atoms | compound input | yes |
| pose set | CPG output | yes (given seeds) |
| pocket contact observations | cross-object (pose × protein) | yes (given pose) |
| pair_features (rc2 bridge mode) | rc2 artifact | yes |

applicability gate: `pair_features` が存在しない、または unusable な場合、CapEvidenceChannel は `None` を返す（APPLICABILITY_ONLY 状態）。これは compound-level verdict に押し込まず、run-level applicability diagnostic として記録する。

### 4. Output contract

#### 4.1 ChannelEvidence

| field | type | description |
|---|---|---|
| channel_id | `"cap"` | 固定 |
| state | EvidenceState | SUPPORTED / REFUTED / INSUFFICIENT |
| reason | str | 判定理由 |
| provenance | Provenance | builder / version / source_refs |
| payload | CapEvidencePayload | channel-private |

#### 4.2 CapEvidencePayload

```python
@dataclass(frozen=True, slots=True)
class CapEvidencePayload:
    partition_state: PartitionValidationState  # VALIDATED / PROVISIONAL / REJECTED
    accepted_partition: CapPartition | None
    engagement_topology: dict[str, object] | None
    mobility_assessment: str | None
```

#### 4.3 EvidenceState 決定規則

| partition_state の最良候補 | EvidenceState | 理由 |
|---|---|---|
| VALIDATED | SUPPORTED | engagement / mobility assessment に進む |
| PROVISIONAL | INSUFFICIENT | Cap identity 未確立 |
| 全候補 REJECTED | REFUTED | Cap identity 不成立 |

### 5. Two-stage partition contract

#### Stage A: PartitionCandidateSet（pre-pose, deterministic）

- 入力: molecular graph, warhead atoms のみ
- 出力: 1+ PartitionCandidate
- 不変条件: 同一分子 → 同一候補集合
- protein geometry は参照しない

#### Stage B: PartitionValidation（pose-dependent, channel-internal）

- 入力: PartitionCandidate + PocketContactObservation
- 出力: PartitionValidation (VALIDATED / PROVISIONAL / REJECTED)
- cap_contact_ratio に基づく判定
- VALIDATION_THRESHOLD は channel config で定義

### 6. Projector contract

CapChannelProjector は以下を SCVObservation に保持する。

| SCVObservation field | source |
|---|---|
| evaluable | partition_state != REJECTED for at least one candidate |
| observation_met | partition_state == VALIDATED for at least one candidate |
| reason | CapEvidencePayload-derived |
| quantitative_metrics | `cap_contact_ratio`, `engagement_score`, `mobility_score` |
| witness_bundle | `accepted_partition`, `best_candidate_id` |
| exploration_slice | `candidate_count`, `validated_count`, `provisional_count`, `rejected_count` |

### 7. Artifact contract

| artifact | layer | content |
|---|---|---|
| `channel_evidence_cap.jsonl` | 1 | compound-level CapEvidencePayload records |
| cap partition provenance | 1 (builder_provenance.json 内) | PartitionCandidateSet provenance + validation provenance |

### 8. Replay contract

- Stage A: 同一入力 → 同一 PartitionCandidateSet（deterministic）
- Stage B: 同一入力（candidate + pocket_contacts）→ 同一 PartitionValidation（deterministic）
- CapChannelProjector: 同一 ChannelEvidence → 同一 SCVObservation（deterministic）

### 9. rc2 adapter coverage（Cap scope）

Cap は rc2 SCV の 3 component のいずれにも直接対応しない。bridge comparison における Cap の位置づけは以下のとおり。

| comparison dimension | rc2 equivalent | status |
|---|---|---|
| Cap engagement / mobility | **なし** | rc2 に独立 sensor が存在しない |
| rc2 Cap 解析（mapping_table, falsification_table） | 統計的証拠 | Cap 自体は rc2 SCV component に直接入らない |

Cap が `comparable_channels` に入った場合、bridge comparator は Cap evidence を **v3-only evidence** として report する。rc2 との component-level match rate は定義しない。Cap drift は v3 internal drift（run 間の Cap evidence 安定性）として監視する。

### 10. Failure criteria

FB-CAP-01: PROVISIONAL 過半数問題（rev3.1 §F.6）
FB-CAP-02: threshold flip 問題（rev3.1 §F.6）

### 11. Remaining UNKNOWN

| topic | status |
|---|---|
| Cap → SCV component mapping | N/A（rc2 SCV component へ直接は入らない） |
| VALIDATION_THRESHOLD の校正値 | implementation 時に決定 |
| engagement_score / mobility_score の exact algorithm | implementation 時に決定 |

---

## ADR-V3-04: Catalytic Evidence Channel Formal Contract

### 1. Context

CatalyticEvidenceChannel は SoT §11.3 Rule 3（anchoring + catalytic-frame disruption）の v3 実装である。current status は materialized-but-not-comparable / observational only である。proposal-connected Rule 3 は引き続き forbidden（SoT §5.3, deferred index）。

### 2. Semantic scope

CatalyticEvidenceChannel は以下の evidence question に answer する。

> 「compound は anchoring interaction を形成するか？ independent に、catalytic geometry を disruption するか？」

このうち、anchoring sub-evidence（Rule3A）は rc2 の Anchoring Sensor（best_target_distance）と**部分的に重なる**。ただし v3 anchoring は motif-based であり、rc2 の distance-only measurement より rich である。catalytic-frame disruption sub-evidence（Rule3B）は rc2 に相当する sensor がない。

### 3. Input contract

| input | source | deterministic? |
|---|---|---|
| compound pose | CPG output | yes (given seeds) |
| anchorable motifs | compound-side builder | yes |
| catalytic residue set + constraint set | protein-side config | yes |
| local protein geometry | structure file | yes |

applicability gate: `evidence_core` が存在しない、または unreadable な場合、`None` を返す（APPLICABILITY_ONLY）。

### 4. Output contract

#### 4.1 ChannelEvidence

| field | type | description |
|---|---|---|
| channel_id | `"catalytic"` | 固定 |
| state | EvidenceState | SUPPORTED / REFUTED / INSUFFICIENT |
| reason | str | 判定理由 |
| provenance | Provenance | builder / version / source_refs |
| payload | CatalyticEvidencePayload | channel-private |

#### 4.2 CatalyticEvidencePayload

```python
@dataclass(frozen=True, slots=True)
class CatalyticEvidencePayload:
    anchoring_witness: dict[str, object] | None
    violated_constraints: tuple[str, ...] | None
    disruption_severity: float | None
```

#### 4.3 EvidenceState 決定規則

| condition | EvidenceState | 理由 |
|---|---|---|
| anchoring witness exists AND disruption severity > threshold | SUPPORTED | 両 sub-evidence 成立 |
| anchoring witness exists AND disruption evidence insufficient | INSUFFICIENT | 片方の evidence のみ |
| no anchoring witness | REFUTED | anchoring 不成立 |

注記: Rule3A（anchoring）と Rule3B（catalytic-frame disruption）は same-pose を要求しない（SoT §11.3.4）。

### 5. Sub-evidence 分離

#### Rule3A: Anchoring sub-evidence

- 入力: AnchorableMotifObject + local protein geometry + pose
- 出力: anchoring witness（motif, interaction type, distance, pose_id）
- rc2 analogue: Anchoring Sensor の best_target_distance

#### Rule3B: Catalytic-frame disruption sub-evidence

- 入力: compound pose + CatalyticFrameObject（constraint set）
- 出力: violated constraints + severity
- rc2 analogue: **なし**

### 6. Projector contract

CatalyticChannelProjector は以下を SCVObservation に保持する。

| SCVObservation field | source |
|---|---|
| evaluable | anchoring evidence 計算可能 |
| observation_met | anchoring witness exists |
| reason | CatalyticEvidencePayload-derived |
| quantitative_metrics | `best_target_distance` (anchoring witness から射影), `disruption_severity`, `violated_constraint_count` |
| witness_bundle | `anchoring_witness`, `best_pose_id` |
| exploration_slice | `motif_count`, `constraint_count` |

重要: `quantitative_metrics["best_target_distance"]` は Catalytic channel の anchoring sub-evidence から**射影**した値であり、rc2 Anchoring Sensor の出力と同一 semantics ではない。v3 anchoring は motif-based distance であり、rc2 は warhead-atom-based distance である。この semantic gap は bridge 比較時に `metrics_drift` として検出されうるが、gap 自体は正当な semantic delta である。

### 7. Artifact contract

| artifact | layer | content |
|---|---|---|
| `channel_evidence_catalytic.jsonl` | 1 | compound-level CatalyticEvidencePayload records |
| catalytic provenance | 1 (builder_provenance.json 内) | CatalyticFrameObject provenance |

### 8. Replay contract

- anchoring sub-evidence: 同一入力 → 同一 witness（deterministic）
- disruption sub-evidence: 同一入力 → 同一 violated constraints（deterministic）
- CatalyticChannelProjector: 同一 ChannelEvidence → 同一 SCVObservation（deterministic）

### 9. Prohibitions

- proposal-connected Rule 3 は forbidden（SoT §5.3, deferred index）
- Catalytic channel は execution-significant semantics を持たない（current は observational only）
- Catalytic comparability の authorization は本 ADR の Rule3A/3B 分離が implementation で検証された後にのみ検討する

### 10. rc2 adapter coverage（Catalytic scope）

| comparison dimension | rc2 equivalent | mapping status |
|---|---|---|
| anchoring sub-evidence (Rule3A) | Anchoring Sensor (best_target_distance) | candidate mapping（後述 §mapping framework） |
| catalytic-frame disruption (Rule3B) | **なし** | v3-only evidence, rc2 比較対象外 |
| offtarget safety | OffTarget Sensor (best_offtarget_distance) | thin OffTarget wrapper source（後述 §mapping framework） |

### 11. Failure criteria

- anchoring sub-evidence の distance projection が rc2 Anchoring Sensor と systematic に乖離する場合、projector の semantic narrowing rule を見直す
- disruption_severity が全化合物で 0.0 になる場合、constraint set の定義が不十分

### 12. Remaining UNKNOWN

| topic | status |
|---|---|
| Catalytic → scv_anchoring mapping の exact projection rule | deterministic projector + semantic narrowing rule で freeze 済み |
| scv_offtarget の v3 source | Option B thin OffTarget wrapper で freeze 済み |
| disruption_severity の exact algorithm | implementation 時に決定 |
| proposal-connected Rule 3 の将来解禁条件 | 専用 ADR に委ねる |

---

## Channel-to-SCV-Component Mapping Framework

### 1. Problem

rc2 SCV は 3 component の Kleene 強三値 AND で verdict を生成する（v4.3.2 §9.4–§9.5）。

```text
rc2_verdict = scv_integrate(scv_anchoring, scv_offtarget, scv_pat)
```

v3 の 3 channel（Path, Cap, Catalytic）は rc2 の 3 component と**1:1 対応しない**。

| rc2 SCV component | v3 channel | 対応の性質 |
|---|---|---|
| scv_pat | Path | **direct**: 同一 evidence dimension, projector で lossless 射影可能 |
| scv_anchoring | Catalytic (Rule3A) | **partial**: v3 は motif-based, rc2 は distance-only. semantic narrowing で射影可能だが lossy |
| scv_offtarget | thin OffTarget channel wrapper | read-only `core_compounds` snapshot から projector 経由で構成 |
| (なし) | Cap (engagement/mobility) | **new**: rc2 に相当する SCV component がない |
| (なし) | Catalytic (Rule3B disruption) | **new**: rc2 に相当する SCV component がない |

### 2. Design decision

channel-to-SCV-component mapping は以下の三段階で管理する。

```text
CANDIDATE → VALIDATED → FROZEN
```

- **CANDIDATE**: mapping の direction と projection method が提案されているが、implementation 検証がない
- **VALIDATED**: implementation test で projection の determinism と rc2 との drift 特性が確認された
- **FROZEN**: ADR で凍結され、bridge comparator が公式に使用してよい

### 3. Current mapping status

| mapping | direction | status | freeze gate |
|---|---|---|---|
| Path → scv_pat | Path channel → PathChannelProjector → scv_pat input | **FROZEN** | Path P6 closed |
| Catalytic (Rule3A) → scv_anchoring | anchoring sub-evidence → best_target_distance projection | **FROZEN** | projector deterministic, semantic narrowing fixed, implementation gate closed |
| Thin OffTarget channel wrapper → scv_offtarget | read-only `core_compounds` snapshot → best_offtarget_distance projection | **FROZEN** | Option B selected and implemented |
| Cap → (new component) | v3-only evidence, rc2 SCV に入らない | **N/A** | Cap は bridge comparison では v3-only drift として扱う |
| Catalytic (Rule3B) → (new component) | v3-only evidence, rc2 SCV に入らない | **N/A** | 同上 |

### 4. scv_offtarget source の選択肢と決定

scv_offtarget の v3 source 候補は以下の三案だった。

**Option A: shell-level passthrough**

OffTarget は v3 の semantic redesign 対象ではなく、rc2 の OffTarget Sensor（v4.3.2 §8.3–§8.4）がそのまま有効である。v3 sidecar 実行時に rc2 OffTarget observation を shell-level で取得し、SCVObservationBundle に直接注入する。

利点: 実装が最小。OffTarget semantics を変えない。
欠点: v3 channel architecture の一貫性が弱まる。OffTarget だけ channel protocol に従わない。

**Option B: thin OffTarget channel wrapper**

OffTarget Sensor を thin EvidenceChannel でラップし、ChannelEvidence + projector の protocol に載せる。内部ロジックは rc2 と同一。

利点: architecture 一貫性。channel lifecycle state が使える。
欠点: 実質的に何も redesign していない wrapper。

**Option C: Catalytic channel に OffTarget sub-evidence を統合**

Catalytic channel の evaluate 内で OffTarget distance も計算し、CatalyticEvidencePayload に含める。

利点: channel 数を増やさない。
欠点: Catalytic の evidence question が「anchoring + disruption + offtarget safety」に膨張し、single-question channel の原則に反する。

**Decision**: **Option B を採用する。** OffTarget Sensor を thin EvidenceChannel wrapper で包み、read-only `core_compounds` snapshot から `best_offtarget_distance` を projector 経由で `scv_offtarget` 入力へ載せる。

### 5. Candidate mapping の検証条件

Catalytic (Rule3A) → scv_anchoring の candidate mapping が VALIDATED に進む条件:

| condition | verification |
|---|---|
| projector が best_target_distance を deterministic に出力する | unit test |
| rc2 Anchoring Sensor の best_target_distance との systematic deviation が特性化されている | benchmark comparison |
| deviation の原因（motif-based vs warhead-atom-based）が documented | ADR-V3-04 supplement |
| metrics_drift として検出される deviation が expected range 内 | 30 run baseline |

VALIDATED → FROZEN の条件: 上記全て + bridge_ci_contracts PR-01–PR-06 の Catalytic 版が全達成。

Implementation note (2026-04-09): deterministic projector and narrowing rule are now repo-implemented, and mapping registry marks Rule3A → `scv_anchoring` as FROZEN. Public comparator scope is still `path_only_partial`; this closure does not itself activate full verdict publication.

### 6. Full-SCV input coverage の成立条件

v3_shadow_verdict を non-None にするには、以下の mapping が全て FROZEN でなければならない。

| SCV component | required mapping status |
|---|---|
| scv_pat | FROZEN（current） |
| scv_anchoring | FROZEN |
| scv_offtarget | FROZEN |

Cap (engagement/mobility) と Catalytic (Rule3B disruption) は rc2 SCV に入らないため、full-SCV input coverage の条件には含まれない。ただし、将来 v3 SCV が rc2 と異なる formula を採用する場合は、別途 ADR で定義する。

---

## Part 2: WP-2 Deliverables

---

## verdict_record.json Authority Migration Conditions

### 1. Current state

| artifact | role | authority status |
|---|---|---|
| `sidecar_run_record.json` | backward-compatible Layer 0 mirror | **non-canonical current** |
| `verdict_record.json` | canonical full verdict record | **current authority** |
| `output_inventory.json` | rc2 inventory | **rc2 authority, unchanged** |

### 2. Migration trigger

`verdict_record.json` が Layer 0 authority に昇格する条件は以下の全てを満たす場合のみであり、この trigger set は `adr_v3_11_m2_authority_transfer.md` で accepted となった。

| condition | verification |
|---|---|
| VN-01–VN-06 が全て satisfied | `v3x_path_verdict_comparability.md` §2.4 |
| v3_shadow_verdict が non-None で安定（30 run 連続） | CI history |
| `verdict_record.json` の schema が ADR で freeze 済み | schema ADR merged |
| `sidecar_run_record.json` の全 authority field が `verdict_record.json` に包含されている | schema comparison |
| migration の exact field mapping が documented | migration ADR |

### 3. Migration mechanics

migration は atomic ではなく段階的に行う。current runtime は Phase M-2 にある。

```text
Phase M-0: schema reservation only (historical)
  - verdict_record.json は optional
  - sidecar_run_record.json が canonical authority
  - verdict_record.json を書いても authority としては参照しない

Phase M-1: dual-write (historical)
  - sidecar_run_record.json と verdict_record.json を両方書く
  - authority は sidecar_run_record.json のまま
  - verdict_record.json の content を sidecar_run_record.json と cross-check
  - 不一致は hard block

Phase M-2: authority transfer (current)
  - verdict_record.json が canonical authority になる
  - sidecar_run_record.json は backward-compatibility のために保持するが authority ではない
  - output_inventory.json は依然として rc2 authority のまま不変
```

### 4. Schema freeze requirements

`verdict_record.json` の schema を freeze する前に、以下が確定していなければならない。

| field group | 確定条件 |
|---|---|
| v3_shadow_verdict / v3_shadow_reason | full-SCV input coverage 成立 |
| v3_shadow_composition | v3 SCV formula の確定 |
| channel_evidence_states | 全 channel の formal contract complete |
| channel_comparability | comparability 三段階の全 channel 版定義 |
| component_matches | channel-to-SCV-component mapping 全て FROZEN |

### 5. output_inventory.json への影響

`verdict_record.json` が authority に昇格しても、`output_inventory.json` は rc2 authority のまま変更しない。v3 sidecar artifact は `generator_manifest.json` で管理し続ける。`output_inventory.json` への v3 artifact 統合は、本 ADR の scope 外であり、将来の repo-level inventory ADR で扱う。

---

## RunDriftReport Canonical Filename Freeze

### 1. Decision

RunDriftReport の canonical filename を以下のとおり凍結する。

```text
run_drift_report.json
```

### 2. Rationale

- P7 が canonical authority filename の凍結を precondition としている
- ADR-V3-10 artifact authority table が「class defined, canonical filename not yet frozen」と記載しており、本 WP-2 で解消する
- filename は machine-readable JSON であり、operator-facing summary（`bridge_operator_summary.md`）とは別 artifact

### 3. Artifact specification

| property | value |
|---|---|
| filename | `run_drift_report.json` |
| layer | 1 |
| format | JSON（RunDriftReport dataclass の serialization） |
| authority | Layer 1 machine-readable bridge report |
| generation condition | bridge comparison run（`--bridge-compare` flag）時に materialize |
| generator_manifest 登録 | always（bridge comparison flag の有無に依存せず generator entry を登録し expected_output_digest を記録） |

### 4. Schema reference

RunDriftReport の schema は `v3x_bridge_ci_contracts.md` ADR-V3-05 §4 で定義済みである（CompoundDriftReport, RunDriftReport dataclass）。本 freeze は filename のみを確定し、schema 自体は bridge_ci_contracts の authority に従う。

---

## Cross-document consistency

| this document | authority reference | consistency |
|---|---|---|
| Cap CapEvidencePayload | rev3.1 §C.4 | field 名一致 |
| Cap PartitionValidationState | rev3.1 §F.1 | 三値一致 |
| Cap two-stage design | rev3.1 §F.2–§F.3 | Stage A/B 一致 |
| Cap EvidenceState 決定規則 | rev3.1 §F.4 | 一致 |
| Cap failure criteria FB-CAP-01/02 | rev3.1 §F.6 | 一致 |
| Catalytic CatalyticEvidencePayload | rev3.1 §C.4 | field 名一致 |
| Catalytic Rule3A/3B split | SoT §11.3 | 一致 |
| Catalytic same-pose not required | SoT §11.3.4 | 一致 |
| Catalytic proposal-connected forbidden | SoT §5.3, deferred index | 一致 |
| Path → scv_pat | path_comparability §3.1 | FROZEN status 一致 |
| channel-to-SCV mapping freeze | path_comparability §2.2 | current repo freeze が path-only 文書の open state を supersede |
| VN-01–VN-06 by reference | path_comparability §2.4 | by reference 採用 |
| verdict_record.json authority | path_comparability §2.5 | post-M-2: canonical authority (see `adr_v3_11_m2_authority_transfer.md`) |
| sidecar_run_record.json authority | rev3.1 §D implementation note | 一致 |
| RunDriftReport Layer 1 | bridge_ci_contracts §6 | 一致 |
| P6 Cap blockers | preconditions P6 | 対応 |
| P6 Catalytic blockers | preconditions P6 | 対応 |
| P7 filename freeze | preconditions P7 | RunDriftReport filename 凍結で P7 部分解消 |

---

## What this document closes

| WP deliverable | status |
|---|---|
| ADR-V3-03 Cap formal contract | closed |
| ADR-V3-04 Catalytic formal contract | closed |
| channel-to-SCV-component mapping framework | closed (Path FROZEN, Catalytic Rule3A FROZEN, OffTarget thin wrapper FROZEN, Cap N/A) |
| verdict_record.json migration conditions | closed |
| RunDriftReport canonical filename | closed (`run_drift_report.json`) |

## What this document does not close

| topic | reason |
|---|---|
| scv_offtarget の v3 source | closed (Option B thin OffTarget wrapper) |
| Cap → SCV component mapping | Cap は rc2 SCV に対応 component がないため N/A |
| Catalytic → scv_anchoring mapping の FROZEN 化 | closed (repo implementation + deterministic projector freeze) |
| verdict_record.json の exact final schema | full-SCV input coverage 成立後に freeze |
| v3 SCV formula の確定（rc2 と異なる場合） | 別途 ADR |

---

*End of document*
