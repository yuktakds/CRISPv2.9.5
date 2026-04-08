# CRISP v3.x Evidence-Channel Kernel Architecture

Status: Ready-to-Go — v3 implementation supplement  
Date: 2026-04-07 rev.3  
Authority note: this unversioned filename is the canonical repo-carried implementation supplement for the current sidecar scope.  
Authority: 本文書は `CRISP_v3x_semantic_design_SOT_RC.md` の Semantic Core を継承し、その Implementation Architecture のみを再設計する。Semantic Core の再解釈権は持たない。  
Inputs: `CRISP_v4.3.2.md`, `CRISP_v3x_semantic_design_SOT_RC.md`, `legacy/v2.9.5/v2.9.5_rc2_deferred_v3x_topics.md`, 実装計画書（§1–§9）

---

## A. 継承する不変条件（Semantic Core）

本節は再設計の対象外である。以下の条件は v4.3.2 および v3 SoT から変更なく継承する。

### A.1 判定責務の不変条件

| ID | 不変条件 | 出典 |
|---|---|---|
| SC-01 | SCV のみが PASS / FAIL / UNCLEAR を返す | v4.3.2 §9.1, SoT §3.1 |
| SC-02 | terminal policy は object logic の外側に置く | v4.3.2 §2.3, SoT §3.1 |
| SC-03 | PASS は必ず witness と観測量を伴う | v4.3.2 §12.1, SoT §3.1 |
| SC-04 | FAIL / UNCLEAR は必ず理由コードと fail-certificate を伴う | v4.3.2 §12.1, SoT §3.1 |
| SC-05 | 各 evaluator / sensor は replay 可能で deterministic provenance を持つ | v4.3.2 §13, SoT §3.1 |
| SC-06 | staging-aware artifact を保持する | v4.3.2 §7.8, SoT §3.1 |
| SC-07 | public verdict reason と run-level diagnostics を混同しない | v4.3.2 §10.5, SoT §3.1 |

### A.2 semantic meaning の不変条件

| ID | 不変条件 | 出典 |
|---|---|---|
| SM-01 | CRISP PASS は「モデル M の下で阻害仮説に矛盾しない」を意味する | v4.3.2 §0.1 |
| SM-02 | PASS / FAIL / UNCLEAR は public taxonomy として直ちに変えない | SoT §5.2 |
| SM-03 | SCV の統合は Kleene 強三値論理の AND と同型 | v4.3.2 §9.5 |
| SM-04 | path_model は SCV の内部実装差であり、SCV は最終 observation のみを受け取る | v4.3.2 §8.5.7 |

### A.3 rc2 frozen boundary の不変条件

| ID | 不変条件 | 出典 |
|---|---|---|
| FB-01 | object-logic reinterpretation を rc2 に戻さない | deferred index §rc2 boundary |
| FB-02 | rc2 の retained artifacts（8 種）を削除しない | SoT §4.2 |
| FB-03 | benchmark / production separation の意味を変えない | deferred index table |
| FB-04 | semantic delta を coding 前に書く | deferred index §entry rule |
| FB-05 | artifact / replay contract を先に列挙する | deferred index §entry rule |
| FB-06 | v3.x branch / ADR track に隔離する | deferred index §entry rule |

### A.4 ADR-gated items（本文書でも触れない）

以下は本文書の scope 外であり、専用 ADR なしには着手しない。

- proposal-connected Rule 3 with execution-significant semantics
- any same-pose style requirement
- CoreSCV reverse-flow / backflow
- benchmark / production meaning redefinition
- taxonomy / comparison semantics redefinition

---

## B. 現 SoT の実装上の破綻点

本節は SoT の semantic design を否定するものではない。SoT が RC complete と判定した architecture level の判断は尊重する。本節が指摘するのは、SoT を忠実に implementation へ落とした場合に生じる構造的不整合である。

### B.1 過剰分解：18 型の初期導入

SoT §7–§11 は compound-side 6 builders、protein-side 6 builders、cross-object 6 evaluators を定義する。合計 18 の新規型のうち、現時点で実装動機が確認されているのは以下の 6 型のみ。

確認済み:
- `PathReferenceField` — v4.3.2 §8.5 PAT が前提とする protein-side geometry
- `CapPartitionObject` — SoT §8.4 Rule 2 の入力
- `CatalyticFrameObject` — SoT §9.3 Rule 3B の入力
- `Rule1A PathObstructionEvaluator` — SoT §11.1.1
- `Rule2B CapEngagementEvaluator` — SoT §11.2.2
- `Rule3B CatalyticFrameDisruptionEvaluator` — SoT §11.3.2

未確認（具体的な使用シナリオが SoT Must/Should/Could のいずれにも記述されていない）:
- `ProteinFlexibilityField`, `HomologyContextObject`, `ResidueRoleMap`, `PocketField`, `AnchorableMotifObject`, `CompoundGraphCanonical`

未確認の型を初期導入すると interface の早期凍結を強いられ、実使用時の contract 変更コストが二重に発生する。

### B.2 CapPartitionObject の pre-pose 矛盾

SoT §8.4 は「Cap partition は pose 前に計算し、proposal や pose で変化してはならない」と規定する。しかし v2.9.5 の Cap 解析（cap/layer0–layer2）は本質的に pose-dependent であり、graph-topology-only の partition は物理的に不安定な定義になりうる。

実装計画も「推論アルゴリズム自体は SoT だけでは未確定」と認識しているが、これは「未確定」ではなく「pre-pose deterministic の要求と pocket-dependent reality の矛盾」である。

### B.3 artifact 爆発と replay overhead

rc2 の 8 artifact families に対し、SoT §13 は compound-side 6 + protein-side 6 + cross-object 6 + governance 6 + retained 8 = 32 artifact families を定義する。全 artifact を常時書き出すと I/O overhead が 4 倍以上になり、artifact 間の replay audit の combinatorial complexity も急増する。

### B.4 移行の過剰直列化

実装計画 §6 の 5-step sequence は各 step が前 step の完了を要求する。3 builders は互いに独立であるにもかかわらず直列化されており、bridge adapter の着手も最終 step まで遅延する。

### B.5 side separation と cross-reference の緊張

SoT §7.1 は「compound builders は target-specific truth conditions を使ってはならない」と規定するが、`BlockingBodyObject` の定義には path geometry（protein-side）が必要であり、`CapPartitionObject` の物理的妥当性は pocket geometry に依存する。

---

## C. Evidence-Channel Kernel Architecture

### C.1 設計原理

SoT の builder/evaluator 格子を全面否定するのではなく、**channel façade の背後に internal builders / evaluators を隠す**設計とする。

public architecture は 3 本の Evidence Channel で構成する。各 channel は「一つの evidence question に対して、入力収集→観測→評価→artifact 出力を一貫して行う自己完結的パイプライン」である。channel 内部では SoT が要求する object boundary を補助的に保持する。

```text
┌───────────────────────────────────────────────────────────┐
│                   public architecture                     │
│                                                           │
│  PathEvidence      CapEvidence       CatalyticEvidence     │
│  Channel           Channel           Channel              │
│      │                 │                  │               │
│      ▼                 ▼                  ▼               │
│  ┌─────────┐     ┌─────────┐       ┌─────────┐           │
│  │ channel  │     │ channel │       │ channel │           │
│  │ internal │     │ internal│       │ internal│           │
│  │ builders │     │ builders│       │ builders│           │
│  │   +      │     │   +     │       │   +     │           │
│  │evaluators│     │evaluators│      │evaluators│          │
│  └────┬─────┘     └────┬────┘       └────┬────┘           │
│       │                │                 │                │
│       ▼                ▼                 ▼                │
│  ChannelEvidence  ChannelEvidence   ChannelEvidence        │
│  + PathProjector  + CapProjector   + CatalyticProjector   │
│       │                │                 │                │
│       └───────┬────────┘─────────────────┘                │
│               ▼                                           │
│          SCVBridge（routing only）                         │
│               │                                           │
│               ▼                                           │
│   SCVObservationBundle（quantitative metrics 保持）        │
│               │                                           │
│               ▼                                           │
│        SCV core（既存）                                    │
│               │                                           │
│               ▼                                           │
│     PASS / FAIL / UNCLEAR                                 │
└───────────────────────────────────────────────────────────┘
```

### C.2 channel は verdict を返さない

channel が返すのは **evidence state** であり、public verdict ではない。これは v4.3.2 §8.1 の「Sensor は観測量を返し、SCV が判定する」原理と同型である。

```python
class EvidenceState(str, Enum):
    """各 channel が返す evidence-level 状態。verdict ではない。"""
    SUPPORTED = "supported"       # 当該 evidence が成立する
    REFUTED = "refuted"           # 当該 evidence が不在と判定
    INSUFFICIENT = "insufficient" # 判定に十分な情報がない
```

SCV との対応は SCVBridge 内の channel-owned projector が担う（§E で定義）。channel が直接 PASS/FAIL/UNCLEAR を返すことは禁止する。これにより SC-01（SCV のみが verdict を返す）を保証する。

### C.3 channel 内部の構造

各 channel の内部は以下の段階で構成する。channel 間での構造の共有は強制しない。

```text
channel internal structure:
  0. applicability gate — channel 前提条件の検証
  1. setup              — protein-side / compound-side の context 準備
  2. observe            — pose-level or compound-level の観測
  3. assess             — 観測からの evidence 評価
  4. package            — ChannelEvidence + projector bundle の構築
```

channel 内部では compound-side step と protein-side step を分けることを推奨するが、cross-reference は許可する。ただし、**artifact namespace と truth-source accounting では side separation を維持する**。

具体的には:
- channel 内部の関数が protein geometry と compound geometry を同時に参照することは許可する（channel 内の実装選択）
- artifact 出力において compound-side evidence と protein-side evidence は別の namespace に書き出す（truth-source の auditability 維持）
- builder provenance record において、各 evidence claim の truth source は明示する（SoT P-04 truth-source explicitness の継承）

### C.4 公開型と channel-private 型の分離

```python
# === 公開型（全 channel 共通） ===

@dataclass(frozen=True, slots=True)
class Provenance:
    """計算の出自を追跡する最小 record"""
    source_name: str
    source_version: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChannelEvidence:
    """全 channel が返す共通 envelope"""
    channel_id: str
    state: EvidenceState
    reason: str
    provenance: Provenance
    payload: EvidencePayload   # channel 固有の型（下記参照）


# === channel 固有型（channel-private だが型安全） ===

@dataclass(frozen=True, slots=True)
class PathEvidencePayload:
    """PathEvidenceChannel が返す evidence 内容"""
    path_family: str
    blockage_ratio: float | None
    witness_pose_id: int | None
    obstruction_path_ids: tuple[str, ...] | None
    persistence_confidence: float | None
    numeric_resolution_limited: bool
    # projector が SCVObservation を構築するために参照する補助量
    apo_accessible_goal_voxels: int | None
    goal_voxel_count: int | None
    top_k_blockage_ratios: tuple[float, ...] | None


@dataclass(frozen=True, slots=True)
class CapEvidencePayload:
    """CapEvidenceChannel が返す evidence 内容"""
    partition_state: PartitionValidationState
    accepted_partition: CapPartition | None
    engagement_topology: dict[str, object] | None
    mobility_assessment: str | None


@dataclass(frozen=True, slots=True)
class CatalyticEvidencePayload:
    """CatalyticEvidenceChannel が返す evidence 内容"""
    anchoring_witness: dict[str, object] | None
    violated_constraints: tuple[str, ...] | None
    disruption_severity: float | None
```

`EvidencePayload` は Union type として定義する。SCV / SCVBridge core は payload を直接参照しない。payload は channel-owned projector（§E.2）と artifact materialization のためだけに存在する。

```python
EvidencePayload = PathEvidencePayload | CapEvidencePayload | CatalyticEvidencePayload
```

### C.5 EvidenceChannel Protocol

```python
@runtime_checkable
class EvidenceChannel(Protocol):
    """全 channel が実装すべき contract"""

    @property
    def channel_id(self) -> str: ...

    def required_inputs(self) -> frozenset[str]: ...

    def evaluate(self, context: EvaluationContext) -> ChannelEvidence | None: ...
        # None を返す場合: channel の前提条件が不成立
        # （run-level applicability diagnostic として記録）

    def projector(self) -> ChannelProjector: ...

    def artifact_generators(self, evidence: ChannelEvidence) -> ArtifactGeneratorSet: ...
```

`evaluate` が `None` を返す場合は、channel の前提条件（例: goal_precheck）が不成立であることを意味する。この場合、caller は compound-level verdict に押し込まず、run-level applicability diagnostic として記録する（§G.4 参照）。

`artifact_generators` は artifact の実体ではなく、**generator（遅延生成関数）の集合** を返す。materialization は ArtifactSink の policy に委ねる（§D で定義）。

### C.6 channel が ChannelEvidence を返さないケース

channel の前提条件不成立は、channel-level の evidence 状態（SUPPORTED / REFUTED / INSUFFICIENT）のいずれでもない。v4.3.2 が `goal_precheck` 不成立を run-level failure として compound-level verdict から分離した設計（v4.3.2 §8.5.8）と同型である。

したがって、前提条件不成立時は:
- `evaluate()` は `None` を返す
- caller（sidecar runner）は `RunApplicabilityRecord` を記録する
- SCV は当該 channel の observation を受け取らない
- 他の channel の evidence のみで SCV が判定を行う（当該 channel は評価対象外）

---

## D. Artifact Governance

### D.1 三層 materialization model

```text
Layer 0: 常時出力（Path-first milestone では sidecar state + replay 再具象化契約）
  - semantic_policy_version.json   — 実行時 policy version
  - sidecar_run_record.json        — current Path-first canonical Layer 0 record（channel states / applicability / comparator status を含む）
  - generator_manifest.json        — 各 artifact の再具象化契約（§D.2）
  - rc2_bridge_pointers.json       — retained rc2 artifact へのポインタ（full bridge mode 時。Path-first milestone では省略可）

Layer 1: replay / audit 要求時に materialize
  - channel_evidence_path.jsonl    — PathEvidence の detailed evidence
  - channel_evidence_cap.jsonl     — CapEvidence の detailed evidence
  - channel_evidence_catalytic.jsonl — CatalyticEvidence の detailed evidence
  - builder_provenance.json        — 各 builder の truth-source chain

Layer 2: debug / research（explicit opt-in）
  - path_voxel_grids/              — PAT の voxel-level 生データ
  - full_contact_trace/            — cap-to-pocket 接触の生データ
  - tool_source_manifest.json      — 外部ツール出所
```

Implementation note:
`observation_bundle.json` and `channel_evidence_path.jsonl` remain Layer 1-class artifacts even when a run policy elects to materialize them in a given execution. Their presence does not rename the canonical Layer 0 record. Path-first milestone does not mutate rc2 `output_inventory.json`; sidecar artifact enumeration is carried by `generator_manifest.json`.

Current-sidecar display note:
- any rendered summary derived from these artifacts must show `semantic_policy_version`
- any rendered summary derived from these artifacts must carry an explicit `[exploratory]` label
- `channel_evidence_cap.jsonl` and `channel_evidence_catalytic.jsonl` record materialized evidence, not full verdict comparability
- `builder_provenance.json` is the current operator-facing truth-source-chain record for all three channels

### D.2 generator_manifest.json と replay-first の保全

Layer 0 に `generator_manifest.json` を必ず含める。ただし、Layer 0 だけで replay 再具象化の**十分条件**を主張するには、未 materialize artifact に対しても「この run が期待する正準出力は何か」を manifest 上で固定しておく必要がある。したがって `generator_manifest.json` は、単なる入出力記録ではなく、**再具象化契約そのもの**として扱う。

```python
@dataclass(frozen=True, slots=True)
class GeneratorEntry:
    """一つの artifact を再具象化するために必要な契約 record"""
    artifact_name: str
    generator_id: str              # generator 関数の一意識別子
    input_content_digest: str      # generator への入力の content hash
    expected_output_digest: str    # 正準出力の期待 digest（materialized の有無に依存しない）
    output_content_digest: str | None  # 今回実際に書き出した bytes の digest（未出力時は None）
    materialized: bool             # 今回の run で実際に書き出したか
    layer: int                     # 0, 1, or 2


@dataclass(frozen=True, slots=True)
class GeneratorManifest:
    """run-level の artifact 再具象化 manifest"""
    policy_version: str
    entries: tuple[GeneratorEntry, ...]
```

`expected_output_digest` は、generator が約束する**正準 serialized output** の digest である。Layer 1/2 artifact を今回 materialize しない場合でも、この値は必ず埋める。逆に、generator が `expected_output_digest` を安定に定義できない artifact は `ON_DEMAND` の対象にしてはならず、少なくとも Layer 1 常時出力へ昇格する。

replay checker は以下を検証する:
1. 同一入力（`input_content_digest` 一致）で generator を再実行し、再生成 output の digest が `expected_output_digest` と一致すること
2. `materialized=True` の artifact では、実際に書き出した `output_content_digest` も `expected_output_digest` と一致すること
3. `materialized=False` の artifact であっても、generator 再実行により `expected_output_digest` を満たす output が得られること
4. Layer 0 artifact は常に `materialized=True` であること

Path-first milestone の実装では、final SCV verdict を Layer 0 に要求しない。したがって current canonical Layer 0 record は `verdict_record.json` ではなく `sidecar_run_record.json` とし、`SCVObservationBundle` は `observation_bundle.json` として Layer 1 に置く。`verdict_record.json` は full-channel bridge により v3 shadow verdict が正規定義された後の canonical 名として予約してよいが、Path-first 段階で必須としない。

### D.3 ArtifactSink の設計

```python
class MaterializePolicy(str, Enum):
    """artifact materialization の policy"""
    ALWAYS = "always"         # Layer 0: 常時出力
    ON_DEMAND = "on_demand"   # Layer 1: replay/audit 要求時
    OPT_IN = "opt_in"        # Layer 2: explicit flag が必要


class ArtifactSink:
    """artifact の lazy writer with digest tracking"""

    def __init__(self, output_dir: Path, run_policy: MaterializePolicy):
        self._output_dir = output_dir
        self._run_policy = run_policy
        self._generators: dict[str, ArtifactGenerator] = {}

    def register(self, gen: ArtifactGenerator) -> None:
        """generator を登録する（まだ書き出さない）"""
        self._generators[gen.artifact_name] = gen

    def flush(self, force_all: bool = False) -> GeneratorManifest:
        """policy に従って materialization を実行し、manifest を返す

        全 generator について expected_output_digest を計算する。
        materialization 対象の artifact のみ実際に書き出し、
        output_content_digest を記録する。
        """
        entries: list[GeneratorEntry] = []
        for name, gen in self._generators.items():
            digest_in = gen.input_digest()

            # expected_output_digest は materialization の有無に依存せず
            # 常に計算する（再具象化契約の核）
            canonical_output = gen.generate()
            digest_expected = _content_hash(canonical_output)

            should_write = self._should_materialize(gen.layer, force_all)
            if should_write:
                (self._output_dir / name).write_bytes(canonical_output)
                digest_out: str | None = digest_expected
            else:
                digest_out = None

            entries.append(GeneratorEntry(
                artifact_name=name,
                generator_id=gen.generator_id,
                input_content_digest=digest_in,
                expected_output_digest=digest_expected,
                output_content_digest=digest_out,
                materialized=should_write,
                layer=gen.layer,
            ))

        return GeneratorManifest(
            policy_version=self._run_policy.value,
            entries=tuple(entries),
        )

    def _should_materialize(self, layer: int, force_all: bool) -> bool:
        if force_all:
            return True
        if layer == 0:
            return True  # Layer 0 は常時出力
        if self._run_policy == MaterializePolicy.ALWAYS:
            return True
        if self._run_policy == MaterializePolicy.ON_DEMAND and layer <= 1:
            return True
        return False
```

実装注記: `flush` は全 generator に対して `generate()` を呼び出し、`expected_output_digest` を計算する。これは「digest 計算のために一度は生成する」ことを意味する。生成コストが高い Layer 2 artifact に対して計算コストが問題になる場合は、generator 側で `expected_digest_only()` のような軽量パスを提供するか、当該 artifact を `ON_DEMAND` 不適格とし Layer 1 常時出力に昇格する。

### D.4 rc2 bridge 互換性

bridge mode 時は Layer 0 の `rc2_bridge_pointers.json` が rc2 retained artifacts（8 種）の場所と digest を記録する。v3.x artifact 構造そのものを rc2 format に合わせることはしない。bridge compatibility は adapter（§E.3）で吸収する。

Path-first milestone では rc2 schema 非侵襲を優先し、`rc2_bridge_pointers.json` は full bridge/comparator mode まで省略可能とする。ただし bridge comparison を実行する場合、`sidecar_run_record.json` または `bridge_comparison_summary.json` のいずれかに、比較に用いた rc2 source path と digest を必須記録しなければならない。

### D.5 失敗基準

**FB-ART-01**: replay test で `generator_manifest.json` の `input_content_digest` から generator を再実行し、再生成 output の digest が `expected_output_digest` と一致しない artifact が 1 件でも存在する場合、当該 generator は deterministic ではない。対処は二つ: (a) generator の non-determinism を除去する、(b) 除去不能なら当該 artifact を `ON_DEMAND` 不適格とし Layer 1 常時出力に昇格する。

**FB-ART-02**: `expected_output_digest` の計算コストが run time の 20% を超える generator が存在する場合、`expected_digest_only()` 軽量パスを実装するか、Layer 2 から Layer 1 に昇格して常時出力とする。

---

## E. SCVBridge と rc2 Adapter

### E.1 SCVBridge の責務

SCVBridge は channel evidence を SCV input に射影する**routing 層**である。SCVBridge core 自体は channel-private payload の意味を解釈しない。射影ロジックは各 channel が所有する **channel-owned projector** に委譲する。

```text
ChannelEvidence (×N)  →  channel-owned projectors  →  SCVObservationBundle  →  SCV core  →  verdict
                                ↑
                        SCVBridge は routing のみ
```

SCVBridge core の責務:
- 各 channel の projector を呼び出し、`SCVObservation` を収集する
- `SCVObservationBundle` を SCV core に渡す
- channel が `None`（前提条件不成立）を返した場合、当該 channel を bundle から除外する

SCVBridge core が行わないこと:
- verdict の生成（SC-01 違反になる）
- channel evidence の再評価や再解釈
- channel-private payload への直接アクセス

### E.2 射影ルール

SCVBridge の射影は、`EvidenceState` の三値だけに潰してはならない。v4.3.2 の SCV と terminal policy は、PAT の `max_blockage_ratio` と `numeric_resolution_limited`、Anchoring / OffTarget の距離・ε-band・`feasible_count`、staging の NearBand / FarBand など、**連続量と exploration 情報**を使って挙動を決める。state / reason のみへの圧縮は SCV input contract の情報損失を招く。

同時に、SCVBridge core が channel-private payload の意味を解釈し始めると、bridge が第二 evaluator 化する。これを避けるため、射影は **channel-owned projector** に委譲する。SCVBridge core は routing のみを担当し、各 projector は versioned contract として当該 channel package 側に属する。

```python
@dataclass(frozen=True, slots=True)
class SCVObservation:
    """SCV が受け取る bridge 後の観測 bundle"""
    evaluable: bool
    observation_met: bool | None
    reason: str
    witness_bundle: Mapping[str, object]
    quantitative_metrics: Mapping[str, float | int | bool | None]
    exploration_slice: Mapping[str, float | int | bool | None]


@runtime_checkable
class ChannelProjector(Protocol):
    """channel-owned projector: payload を bridge bundle に射影する"""

    @property
    def channel_id(self) -> str: ...

    def project(self, ev: ChannelEvidence) -> SCVObservation: ...


class SCVBridge:
    """channel evidence → SCV observation bundle への routing bridge"""

    def __init__(self, projectors: Mapping[str, ChannelProjector]):
        self._projectors = dict(projectors)

    def project(self, evidences: Sequence[ChannelEvidence]) -> SCVObservationBundle:
        """channel evidence を SCV observation に射影する

        ChannelEvidence が None（前提条件不成立）の channel は
        caller 側で除外済みであり、ここには渡されない。
        """
        observations: dict[str, SCVObservation] = {}
        for ev in evidences:
            projector = self._projectors[ev.channel_id]
            observations[ev.channel_id] = projector.project(ev)
        return SCVObservationBundle(observations=observations)
```

Path channel の projector は、少なくとも以下を bundle に残す:
- `quantitative_metrics`: `max_blockage_ratio`, `persistence_confidence`, `numeric_resolution_limited`
- `witness_bundle`: `witness_pose_id`, `obstruction_path_ids`, `path_family`
- `exploration_slice`: `top_k_blockage_ratios`, `apo_accessible_goal_voxels`, `goal_voxel_count`, `feasible_count`（取得可能な範囲）

Cap / Catalytic も同様に、SCV が後段で必要とする定量観測を `quantitative_metrics` に保持する。ただし、**public verdict は依然として SCV のみが返す**（SC-01）。projector が行うのは evidence の bridge 表現への射影であり、判定の再評価ではない。

この設計により:
1. SCVBridge core は channel-private payload semantics を再解釈しない
2. 既存 SCV が必要とする定量量を lossless に近い形で保持できる
3. projector は channel package 側に属するため、channel の evolution と projector の evolution が同期する
4. FB-BRIDGE-01 が問題にする「state のみへの圧縮による情報損失」を構造的に回避できる

### E.3 rc2 adapter

rc2 bridge mode 時は、rc2 の既存 observation（anchoring, offtarget, PAT）を `SCVObservationBundle` に変換する adapter を提供する。

```python
class RC2Adapter:
    """rc2 observation → SCVObservationBundle への adapter"""

    def adapt(self, rc2_observations: dict) -> SCVObservationBundle:
        """rc2 の既存 observation format を v3 bridge format に変換する

        rc2 の observation は v4.3.2 の Sensor output 形式であり、
        距離・ε-band・feasible_count・blockage_ratio 等を含む。
        これらを SCVObservation の quantitative_metrics / witness_bundle /
        exploration_slice に対応づける。
        """
        ...
```

bridge comparator は `RC2Adapter` の出力と SCVBridge の出力を比較し、evidence-level drift report を生成する。

---

## F. Cap Partition の二段階設計

### F.1 三値状態の formal 定義

```python
class PartitionValidationState(str, Enum):
    """Cap partition の validation 状態"""
    VALIDATED = "validated"       # pose 観測で妥当性が確認された
    PROVISIONAL = "provisional"  # graph-only 候補を暫定 accept（pocket reality 未検証）
    REJECTED = "rejected"        # pose 観測で妥当性が否定された
```

`VALIDATED > PROVISIONAL > REJECTED` の順序は evidence confidence の順序に対応する。

### F.2 Stage A: PartitionCandidateSet（pre-pose, deterministic）

```python
@dataclass(frozen=True, slots=True)
class PartitionCandidate:
    """graph-topological partition の候補"""
    candidate_id: str
    warhead_region: tuple[int, ...]
    linker_region: tuple[int, ...]
    cap_primary: tuple[int, ...]
    cap_auxiliary: tuple[tuple[int, ...], ...] = ()
    ambiguous_nodes: tuple[int, ...] = ()
    topological_confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class PartitionCandidateSet:
    """一分子に対する partition 候補の集合"""
    molecule_id: str
    candidates: tuple[PartitionCandidate, ...]
    provenance: Provenance

    # 不変条件: 同一分子 → 同一候補集合（deterministic）
```

Stage A の入力は molecular graph と warhead atoms のみ。protein geometry は参照しない。出力は 1 つ以上の `PartitionCandidate` であり、生成は deterministic。

### F.3 Stage B: PartitionValidation（pose-dependent, channel-internal）

CapEvidenceChannel 内で、pose 観測を用いて候補を validate する。

```python
@dataclass(frozen=True, slots=True)
class PartitionValidation:
    """候補 partition の検証結果"""
    candidate_id: str
    state: PartitionValidationState
    contact_support: dict[str, object] | None
    reject_reason: str | None


def validate_partition(
    candidate: PartitionCandidate,
    pocket_contacts: PocketContactObservation,
) -> PartitionValidation:
    """pose 観測に基づいて partition 候補を validate する"""
    cap_atoms = set(candidate.cap_primary)
    contacting_atoms = {c.atom_index for c in pocket_contacts.contacts}
    cap_contact_ratio = len(cap_atoms & contacting_atoms) / max(len(cap_atoms), 1)

    if cap_contact_ratio >= VALIDATION_THRESHOLD:
        return PartitionValidation(
            candidate_id=candidate.candidate_id,
            state=PartitionValidationState.VALIDATED,
            contact_support={"cap_contact_ratio": cap_contact_ratio},
            reject_reason=None,
        )
    elif cap_contact_ratio > 0:
        return PartitionValidation(
            candidate_id=candidate.candidate_id,
            state=PartitionValidationState.PROVISIONAL,
            contact_support={"cap_contact_ratio": cap_contact_ratio},
            reject_reason=None,
        )
    else:
        return PartitionValidation(
            candidate_id=candidate.candidate_id,
            state=PartitionValidationState.REJECTED,
            contact_support=None,
            reject_reason="no_cap_pocket_contact",
        )
```

### F.4 SCV への影響

CapEvidenceChannel は partition validation の結果に基づいて evidence state を返す:
- 最良候補が `VALIDATED` → `EvidenceState.SUPPORTED`（engagement/mobility assessment に進む）
- 最良候補が `PROVISIONAL` → `EvidenceState.INSUFFICIENT`（Cap identity 未確立）
- 全候補が `REJECTED` → `EvidenceState.REFUTED`

CapChannelProjector はこの evidence state に加え、SCV が必要とする定量観測（engagement metrics, mobility scores, contact topology summary）を `quantitative_metrics` に保持する。SCV は ChannelEvidence を直接参照せず、projector が構築した `SCVObservation` 経由でのみ情報を受け取る。

### F.5 SoT との整合性

- SoT §8.4 の「deterministic identity を欲しい」→ Stage A で candidates は deterministic
- 物理的妥当性 → Stage B で pose-validated
- 「分からないものを推測で埋めない」→ `PROVISIONAL` は明示的な不確実性状態
- SoT P-04 truth-source explicitness → PartitionValidation は truth source（pocket contacts）を明示

### F.6 失敗基準

**FB-CAP-01**: 実運用データで Cap `PROVISIONAL` 状態が molecule population の過半数を占め、CapEvidenceChannel が恒常的に `INSUFFICIENT` を返す場合、二段階設計は有効に機能していない。対処: (a) validation threshold の引き下げ、(b) graph-only partition heuristic の改善、(c) 二段階設計を廃止し SoT 原案の pre-pose deterministic partition に戻す。

**FB-CAP-02**: `VALIDATED` と `PROVISIONAL` の boundary で同一分子が pose set の微小変化により状態遷移する（flip）場合、threshold 近傍の安定性が不足している。対処: ε-band を導入し `VALIDATED` / `PROVISIONAL` 間に hysteresis を設ける。

---

## G. Path-first 実装計画

### G.1 PathEvidence channel の優先理由

1. v4.3.2 §8.5 が `path_blocking`, `PATGoalRegion`, `goal_precheck`, `TUNNEL`/`SURFACE_LIKE` を formal に定義済み
2. 既存 `pathyes.py` からの実装知見が活用可能
3. same-pose requirement 不要（SoT §11.3.4 参照）
4. Rule 3 proposal-connected に触れない
5. 監査負担が 3 channel 中最小

### G.2 dependency graph

```text
      ┌──────────────────────────────────┐
      │ T0: policy + contracts +         │
      │     EvidenceChannel Protocol +   │
      │     ChannelProjector Protocol +  │
      │     SCVBridge routing shell      │  ← 全 channel の基盤
      └──────┬───────────────────────────┘
             │
    ┌────────┴────────────┐
    ▼                     │
┌────────────────┐        │
│ T1a: Path      │        │
│  channel       │        │  ← 最初の実装対象
│  (TUNNEL)      │        │
│  + projector   │        │
└─────┬──────────┘        │
      │              ┌────┴───────────┐
      │              │ T1b: Cap       │  ← Path 完了後に着手推奨
      │              │  channel       │
      │              │  (propose/     │
      │              │   validate)    │
      │              │  + projector   │
      │              └────┬───────────┘
      │                   │
      │              ┌────┴──────────────┐
      │              │ T1c: Catalytic    │  ← 並行可能
      │              │  channel          │
      │              │  + projector      │
      │              └────┬──────────────┘
      │                   │
      ▼                   ▼
┌──────────────────────────────────────┐
│ T2: sidecar runner + ArtifactSink   │  ← T1a 完了時点で着手可能
│     + Layer 0 artifact emission     │
│     + generator_manifest            │
└──────┬───────────────────────────────┘
       │
  ┌────┴─────────────┐
  ▼                  ▼
┌──────────┐  ┌──────────────┐
│ T3a:     │  │ T3b: rc2     │  ← 並行可能
│ shadow   │  │ bridge       │
│ hook     │  │ adapter +    │
│          │  │ RC2Adapter   │
└────┬─────┘  └────┬─────────┘
     │             │
     ▼             ▼
┌──────────────────────────────────────┐
│ T4: bridge comparator                │
│     + exploratory CI                 │
└──────────────────────────────────────┘
```

### G.3 T0: 基盤実装

ファイル:
- `crisp/v3/__init__.py`
- `crisp/v3/policy.py` — SemanticPolicyVersion, SemanticMode
- `crisp/v3/contracts.py` — EvidenceState, EvidenceChannel Protocol, ChannelEvidence, ChannelProjector Protocol, Provenance, payload types, SCVObservation, SCVObservationBundle
- `crisp/v3/scv_bridge.py` — SCVBridge（routing shell のみ）
- `crisp/v3/artifacts/__init__.py`
- `crisp/v3/artifacts/sink.py` — ArtifactSink, GeneratorManifest, GeneratorEntry, MaterializePolicy

テスト:
- `tests/v3/test_policy.py`
- `tests/v3/test_scv_bridge.py` — routing 動作と None channel 除外

### G.4 T1a: PathEvidence channel

ファイル:
- `crisp/v3/channels/__init__.py`
- `crisp/v3/channels/path.py` — PathEvidenceChannel, PathEvidencePayload, PathChannelProjector

内部構造:
```text
PathEvidenceChannel.evaluate(context):
  0. applicability gate
     → goal_precheck を実行
     → 不成立なら ChannelEvidence は返さず、
       run-level applicability diagnostic を記録して None を返す
       （compound-level FAIL / UNCLEAR へ落とさない — v4.3.2 §8.5.8 準拠）

  1. path_reference_setup
     → PATGoalRegion 計算（v4.3.2 §8.5.3 準拠）
     → apo baseline 計算（TUNNEL: §8.5.5 / SURFACE_LIKE: §8.5.6）

  2. obstruction_measure
     → top_k_poses に対する blockage ratio 計算
     → witness_pose_id / obstruction_path_ids / apo_accessible_goal_voxels を取得

  3. persistence_assess
     → rigidity profile による persistence confidence を算出
     → ただし T1a では obstruction 判定を覆す独立 gate にせず、
       payload と bridge metrics に記録する
       （Rule1A/1B の正式分離は ADR-V3-02 で確定）

  4. package
     → PathEvidencePayload 構築
     → PathChannelProjector が SCVObservation へ射影可能な bundle を同時に準備
     → EvidenceState 決定:
        numeric_resolution_limited → INSUFFICIENT
        blockage ≥ threshold       → SUPPORTED
        blockage < threshold       → REFUTED
```

実装上の注記:
- `goal_precheck` 不成立は v4.3.2 の定義どおり run-level の入力不整合または適用外であり、channel-level evidence state に押し込まない
- `numeric_resolution_limited` は Path channel の `INSUFFICIENT` 理由として保持する
- `persistence_confidence` は T1a では記録先行とし、public semantics への昇格は行わない

テスト:
- `tests/v3/test_path_channel.py` — deterministic unit tests
- `tests/v3/test_path_invariants.py` — evidence invariant tests（SUPPORTED には witness、REFUTED には reason）
- `tests/v3/test_path_applicability.py` — goal_precheck 不成立が run-level diagnostic へ分離され、ChannelEvidence が None として返されること
- `tests/v3/test_path_projector.py` — PathChannelProjector が quantitative_metrics / witness_bundle / exploration_slice を正しく構築すること

### G.5 T2: sidecar runner

ファイル:
- `crisp/v3/runner.py` — sidecar orchestrator

責務:
- `run_integrated_v29` からの opt-in hook
- channel 実行の orchestration
- channel が `None` を返した場合の `RunApplicabilityRecord` 記録
- ArtifactSink への generator 登録と flush（`generator_manifest.json` 含む）
- current Path-first canonical artifacts（`sidecar_run_record.json`, `observation_bundle.json`, `channel_evidence_path.jsonl`）の出力
- rc2 verdict path の完全保持

Current implementation note:
- Cap / Catalytic も同じ runner から opt-in で materialize してよい
- input source が存在しない場合は `ChannelEvidence` を捏造せず `RunApplicabilityRecord` を残す
- Catalytic は `evidence_core` snapshot を read-only truth-source chain とし、proposal-connected Rule 3 へ昇格させない

### G.6 T3a: shadow hook

`crisp/v29/cli.py` の `run_integrated_v29` に最小限の hook を追加。default off。

```python
# crisp/v29/cli.py への追加（概念）
if sidecar_policy.mode != SemanticMode.OFF:
    from crisp.v3.runner import run_sidecar
    sidecar_result = run_sidecar(context, sidecar_policy)
    # rc2 verdict は不変。sidecar_result は別 namespace に出力。
```

### G.7 T3b: rc2 bridge adapter

ファイル:
- `crisp/v3/adapters/__init__.py`
- `crisp/v3/adapters/rc2_bridge.py` — RC2Adapter, rc2 artifact reader

テスト:
- `tests/v3/test_rc2_bridge.py` — rc2 artifact の読み取りと SCVObservationBundle への正規化

### G.8 変更対象（既存ファイル）

Must 範囲:
- `crisp/v29/cli.py` — sidecar hook 追加（default off, verdict path 不変）

Path-first milestone の実装注記:
- `output_inventory.json` への sidecar artifact 登録は rc2 schema 保全のため意図的に見送ってよい。current canonical inventory は `v3_sidecar/generator_manifest.json` とし、`crisp/v29/manifest.py` / `writers.py` の inventory 統合は full migration ADR まで defer 可能とする。

### G.9 branch 名 / commit message

```text
feat/v3-kernel-policy-contracts
  feat: scaffold v3 evidence-channel kernel policy and contracts

feat/v3-path-evidence-channel
  feat: add PathEvidenceChannel with TUNNEL obstruction measure and projector

feat/v3-artifact-sink
  feat: add three-layer artifact sink with generator manifest and expected digests

feat/v3-sidecar-runner
  feat: wire opt-in v3 sidecar runner into run_integrated_v29

feat/v3-scv-bridge
  feat: add SCVBridge routing shell with channel-owned projectors

feat/v3-rc2-bridge-adapter
  feat: add rc2 artifact adapter for bridge comparison

feat/v3-cap-evidence-channel
  feat: add CapEvidenceChannel with propose/validate partition and projector

feat/v3-catalytic-evidence-channel
  feat: add CatalyticEvidenceChannel stub with constraint set and projector

ci/v3-exploratory-lane
  ci: add non-required v3 exploratory workflow
```

---

## H. 早期警戒指標と失敗基準

### H.1 sidecar 安全性

**FB-SIDE-01**: sidecar mode で rc2 verdict が 1 件でも変わったら即停止。sidecar runner は rc2 verdict path に一切介入しない設計だが、副作用（メモリ、timing、global state）による予期せぬ変化を検出するための必須 gate。

テスト: `tests/v3/test_sidecar_invariants.py`

### H.2 replay 再具象化

**FB-ART-01**: generator の deterministic 再生成不能（§D.5 参照）。
**FB-ART-02**: `expected_output_digest` 計算コスト超過（§D.5 参照）。

### H.3 Cap partition 有効性

**FB-CAP-01**: `PROVISIONAL` 過半数問題（§F.6 参照）。
**FB-CAP-02**: threshold 近傍の flip 頻発問題（§F.6 参照）。

### H.4 channel façade の透明性

**FB-CHAN-01**: channel façade の内部が不透明で evidence truth source が追跡できない場合、channel 内部の builder/evaluator contract を public に再露出させる。判定方法: replay audit で「この evidence claim の truth source は何か」を Layer 0 + Layer 1 artifact から一意に特定できなければ失敗。

### H.5 SCVBridge の射影品質

**FB-BRIDGE-01**: SCVBridge の evidence → observation 射影で情報が失われ、SCV の verdict 品質が劣化する場合（rc2 との verdict 一致率が sidecar invariant test の基準未満）、projector の quantitative_metrics / exploration_slice を拡張する。

---

## I. ADR Queue

本文書の implementation supplement 範囲外であり、専用 ADR が必要な項目の一覧。

| ADR ID | Topic | 前提条件 |
|---|---|---|
| ADR-V3-01 | semantic-policy versioning | T0 完了後 |
| ADR-V3-02 | PathEvidence channel formal contract（Rule1A/1B 分離含む） | T1a 実装経験に基づく |
| ADR-V3-03 | CapPartition propose/validate formal contract | T1b 実装経験に基づく |
| ADR-V3-04 | CatalyticEvidence anchoring vs disruption split | T1c 実装経験に基づく |
| ADR-V3-05 | bridge comparator drift attribution policy | T4 実装経験に基づく |
| ADR-V3-06 | operator / CI semantic-policy separation | T4 完了後 |
| ADR-V3-07 | witness equivalence vs same-pose requirement | 全 channel 実装完了後 |
| ADR-V3-08 | evidence-demand loop without SCV reverse-flow | 全 channel 実装完了後 |
| ADR-V3-09 | taxonomy / comparison semantics redesign | bridge comparator の drift data 蓄積後 |

---

## J. 本文書の位置づけ

本文書は `CRISP_v3x_semantic_design_SOT_RC.md`（Semantic Core）を否定しない。

本文書は SoT の Implementation Architecture に対する代替案であり、以下の関係を持つ:

```text
CRISP_v4.3.2.md                        ← 上位規範（不変条件の源泉）
  ↓
CRISP_v3x_semantic_design_SOT_RC.md    ← Semantic Core（authority 維持）
  ↓
本文書                                  ← Implementation Supplement（architecture 代替案）
  ↓
ADR-V3-01 .. ADR-V3-09                 ← Follow-up ADRs（channel ごとの formal contract）
```

SoT の §1.1 authority は維持する。本文書が拘束するのは implementation-level の architecture 選択のみであり、semantic meaning の再定義権は持たない。

---

*End of document*
