# CRISP v3.x Path-Only Verdict Comparability Semantics

Status: Pre-implementation freeze  
Date: 2026-04-08  
Authority note: this unversioned filename is the canonical repo-carried path-only comparability note for the current comparator scope.  
Parent: `v3x_evidence_channel_kernel_architecture.md`, `v3x_bridge_ci_contracts.md`  
Scope: Path channel に限定した verdict comparability の定義。full migration contract (ADR-V3-05/06 の scope 拡大) には入らない。

---

## 0. Current State（既成事実）

以下は本文書の前提であり、再議論しない。

| fact | status |
|---|---|
| comparator scope | `path_only_partial` |
| comparable_channels | `["path"]` |
| Path-first milestone | complete |
| full migration contract | open |
| full verdict comparability | open |
| P6 rc2 adapter coverage table | frozen (bridge_ci_contracts §3–§7) |
| P6 full bridge consumer for Path | exists (PathChannelProjector) |
| P2/P7 truth-source / inventory authority | hardened in current sidecar scope |
| P4/P5 operator-facing / CI separation | hardened in current scope |
| operator-facing surface | `semantic_policy_version`, `[exploratory]`, rc2 primary / v3 secondary, `verdict_match_rate: N/A`, inventory authority split |
| required matrix | untouched; v3 jobs are exploratory |
| `output_inventory.json` authority | rc2 |
| sidecar inventory authority | `generator_manifest.json` |
| `v3_shadow_verdict` | currently `None` is normal |

---

## 1. Path における「final verdict comparable」の定義

### 1.1 構造的制約

rc2 verdict の生成式は v4.3.2 §9.4–§9.5 で固定されている。

```text
rc2_verdict = scv_integrate(
    scv_anchoring(anchoring_obs, exploration_log, config),
    scv_offtarget(offtarget_obs, exploration_log, config),
    scv_pat(pat_obs, config)
)
```

`scv_integrate` は Kleene 強三値 AND である。rc2 verdict は 3 つの sensor verdict の合成であり、PAT 単独では rc2 verdict を再現できない。

v3 Path channel は rc2 PAT sensor に対応する evidence を生成する。しかし v3 は現時点で Anchoring / OffTarget channel を持たない。したがって **Path channel だけでは SCV-level の verdict を構成できず、rc2 verdict との直接比較は構造的に不可能**である。

### 1.2 comparability は verdict level ではなく SCV component level で定義する

Path-only scope において「final verdict comparable」とは、以下の限定的な意味を持つ。

> **Path における final verdict comparable とは、v3 PathEvidence channel の出力を PathChannelProjector 経由で SCVObservation に射影した結果が、rc2 の `scv_pat` に渡される observation と同一の public taxonomy 上で直接比較可能であることを意味する。**

これは SCV-level verdict の比較ではない。SCV の 3 入力のうち 1 入力（PAT component）の比較である。

### 1.3 comparability の単位

| 単位 | Path-only scope での意味 |
|---|---|
| compound 単位 | 一化合物について、rc2 PAT component verdict と v3 Path evidence state の比較が可能か |
| run 単位 | 一 run の全化合物について、compound 単位の comparability が成立する割合 |
| channel 単位 | 当該 channel が comparable_channels に含まれているか（Path: yes、Cap/Catalytic: no） |
| comparable subset 単位 | coverage_drift も applicability_drift もない化合物集合 |

**primary 単位は compound** とする。run-level の summary は compound 単位の集計である。

### 1.4 comparability は三段階

```python
class CompoundPathComparability(str, Enum):
    """一化合物に対する Path component の comparability"""
    NOT_COMPARABLE = "not_comparable"
    EVIDENCE_COMPARABLE = "evidence_comparable"
    COMPONENT_VERDICT_COMPARABLE = "component_verdict_comparable"
```

**`NOT_COMPARABLE`**: 以下のいずれかに該当する。
- rc2 で PAT が評価されていない（`pathyes_skip_code` あり）かつ v3 Path channel も `None` を返した → 両方未評価、比較不要
- rc2 で PAT が評価されたが v3 Path channel が `None` を返した（またはその逆）→ `coverage_drift`
- `applicability_drift` が検出された → 前提条件の不一致

**`EVIDENCE_COMPARABLE`**: 以下の全てを満たす。
- rc2 と v3 の両方が当該 compound に対して Path/PAT evidence を生成した
- coverage_drift なし
- applicability_drift なし
- ただし metrics_drift の有無は問わない（evidence は comparable だが値が異なりうる）

**`COMPONENT_VERDICT_COMPARABLE`**: `EVIDENCE_COMPARABLE` に加え、以下を全て満たす。
- metrics_drift なし（quantitative_metrics が tolerance 以内）
- v3 Path の `EvidenceState` を `scv_pat` 相当のロジックで rc2 PAT verdict と同一 taxonomy 上に射影可能
- witness_drift の有無は問わない（verdict level の comparability を阻害しない）

### 1.5 witness_drift の位置づけ

witness_drift は comparability の阻害要因に**含めない**。理由は三つある。

第一に、v4.3.2 §9.4 が「Anchoring witness と PAT witness は同一 pose である必要はない」と明示しており、witness の一意性はそもそも CRISP の設計上要求されていない。

第二に、同一 `max_blockage_ratio` を複数の pose が達成しうる場合、tiebreak rule の微差で異なる witness が選ばれることは determinism の範囲内で正当である。

第三に、witness drift を comparability の阻害要因にすると、component verdict が一致していても comparability が落ちることになり、operator にとって直感に反する。

witness_drift は drift report に記録し、operator が必要に応じて確認できるようにするが、comparability level の決定には使わない。

### 1.6 Path-only から full bridge への semantic threshold

Path-only partial comparator から full bridge comparator へ進むとき、以下が semantic threshold になる。

| threshold | 意味 |
|---|---|
| `comparable_channels` の拡大 | Cap / Catalytic channel が comparable_channels に追加される |
| SCV integration の定義 | v3 の全 channel output を SCV に統合して single verdict を生成する方式が確定する |
| `v3_shadow_verdict` の活性化 | v3 が SCV-level verdict を生成し、rc2 verdict と直接比較可能になる |

これらは本文書の scope 外であり、full migration contract ADR で扱う。本文書は Path component の comparability のみを閉じる。

---

## 2. `v3_shadow_verdict` を非 None にしてよい条件

### 2.1 原則

`v3_shadow_verdict` は SCV-level の verdict である。SCV は Kleene 強三値 AND で 3 component を統合する（SM-03）。したがって **v3_shadow_verdict を非 None にするには、SCV に渡す全 component の source が定義されていなければならない**。

### 2.2 full-SCV input coverage requirement

v3_shadow_verdict を計算するために SCV が必要とする入力 component は、rc2 では anchoring / offtarget / PAT の 3 つである（v4.3.2 §9.4）。しかし v3 architecture の public channel は Path / Cap / Catalytic であり、**v3 channel outputs が rc2 SCV の 3 component にどう射影されるかの mapping はまだ未定義**である。

| rc2 SCV component | v3 channel 候補 | mapping status |
|---|---|---|
| scv_pat | Path channel | confirmed（PathChannelProjector） |
| scv_anchoring | **UNKNOWN** | full migration ADR で定義する |
| scv_offtarget | **UNKNOWN** | full migration ADR で定義する |

v3 の Cap channel が rc2 anchoring にどう対応し、Catalytic channel が rc2 offtarget にどう対応するかは、channel-to-SCV-component mapping として full migration contract ADR で凍結する。Path P6 scope ではこの mapping を先取りしない。

したがって Path-only scope では v3_shadow_verdict は non-None にできない。必要なのは Path → scv_pat の単一 mapping のみであり、それは confirmed 済みである。

### 2.3 hybrid SCV mode（将来の選択肢）

未定義の SCV component を rc2 observation から借用する hybrid SCV mode は概念上可能だが、以下の問題がある。

第一に、hybrid は cross-version composition であり、semantic_policy_version の meaning が曖昧になる。「この verdict はどの semantic policy で生成されたか」に対して一貫した回答ができない。

第二に、hybrid verdict を rc2 verdict と比較して「一致した」と主張しても、借用した component が同一 source なのだから一致は自明であり、比較の情報量がゼロになる。実質的に Path component の比較しかしていないのに、verdict-level の一致を claim することになる。

第三に、hybrid mode は SC-01（SCV のみが verdict を返す）には違反しないが、operator safety（SoT P-06）に抵触する。public meaning が silent に drift する。

### 2.4 判断

**Path-only scope では `v3_shadow_verdict` は None のままとする。** hybrid SCV mode は採用しない。

`v3_shadow_verdict` を非 None にしてよい条件は以下の全てを満たす場合のみである。

| 条件 ID | 条件 | 検証方法 |
|---|---|---|
| VN-01 | full migration ADR で channel-to-SCV-component mapping が凍結されている | ADR document merged |
| VN-02 | mapping で定義された全 SCV component に対して、v3 channel が ChannelEvidence を生成できる | 全対応 T1 task complete |
| VN-03 | 全対応 channel の ChannelProjector が SCVObservation を生成し、SCV core に渡せる | SCVBridge integration test green |
| VN-04 | 全対応 channel の formal contract ADR が complete | ADR documents merged |
| VN-05 | sidecar invariant test（FB-SIDE-01）が直近 30 run green | CI history |
| VN-06 | `verdict_record.json` の schema が v3_shadow_verdict を含む形で freeze され、Layer 0 authority が `sidecar_run_record.json` から移行済み | schema ADR merged |

VN-01 から VN-06 のいずれかが未達の間、`v3_shadow_verdict` は None であり、`verdict_match_rate` は `N/A` である。

### 2.5 `verdict_record.json` の schema reservation

**`verdict_record.json` は schema reservation のみであり、current canonical Layer 0 record ではない。** Path-first milestone の canonical Layer 0 record は `sidecar_run_record.json` である。`verdict_record.json` は full-channel bridge 後に正規定義される将来の予約名であり、Path P6 scope では以下の位置づけとする。

- schema reservation only
- non-canonical（`sidecar_run_record.json` が canonical authority）
- optional（emit してもしなくてもよい）
- not Layer 0 authority（Layer 0 authority は `sidecar_run_record.json` + `generator_manifest.json`）

将来 `verdict_record.json` を Layer 0 canonical に昇格する場合は、full migration contract ADR で schema を freeze し、`sidecar_run_record.json` からの authority 移行を explicit に定義する。

以下は将来の schema reservation として記録する。Path P6 scope ではこの schema に基づくファイルを生成する義務はない。

```python
@dataclass(frozen=True, slots=True)
class VerdictRecordSchema:
    """schema reservation: full-channel bridge 後に正規定義する予約構造"""
    run_id: str
    semantic_policy_version: str
    comparator_scope: str                       # "path_only_partial"
    comparable_channels: tuple[str, ...]        # ("path",)

    # rc2 verdict（sidecar mode では常に rc2 が primary）
    rc2_verdict: str                            # "PASS" / "FAIL" / "UNCLEAR"
    rc2_reason: str

    # v3 shadow verdict（条件 VN-01..VN-05 未達の間は None）
    v3_shadow_verdict: str | None               # None
    v3_shadow_reason: str | None                # None
    v3_shadow_composition: str | None           # None

    # channel-level evidence states（利用可能な channel のみ）
    channel_evidence_states: dict[str, str]     # {"path": "supported"} 等
    channel_comparability: dict[str, str]       # {"path": "component_verdict_comparable"} 等

    # component-level comparison（Path のみ）
    path_component_match: bool | None           # rc2 PAT verdict == v3 Path projected verdict
```

`v3_shadow_verdict` 関連 field は予約 field である。current `sidecar_run_record.json` には `channel_evidence_states`, `channel_comparability`, `path_component_match` のみを含め、v3_shadow_verdict 関連は含めない。

---

## 3. rc2 semantics を再解釈せずに comparability を計算する方法

### 3.1 比較の原則

rc2 の PASS / FAIL / UNCLEAR の public meaning は変えない（SM-02）。比較は以下の制約下で行う。

> **比較は「rc2 `scv_pat` が返した verdict」と「v3 PathChannelProjector の SCVObservation を同一の `scv_pat` ロジックに通した場合の verdict」の一致判定である。**

つまり、v3 側で新しい verdict logic を走らせるのではなく、**rc2 の `scv_pat` を共通の verdict function として使い、入力 observation だけを差し替える**。

```text
rc2 PAT verdict = scv_pat(rc2_pat_observation, config)
v3  PAT verdict = scv_pat(v3_path_projected_observation, config)

path_component_match = (rc2 PAT verdict == v3 PAT verdict)
```

これにより、verdict logic 自体は rc2 のまま保持され、rc2 semantics の再解釈は発生しない。差異が生じるのは observation の違いのみである。

### 3.2 `scv_pat` への入力の構成

v3 PathChannelProjector が生成する `SCVObservation` から、`scv_pat` が必要とする入力を以下のように取り出す。

```python
def extract_pat_observation(scv_obs: SCVObservation) -> PatObservation:
    """SCVObservation → scv_pat の入力形式に変換する

    rc2 の scv_pat は以下を参照する:
      - pat_obs.goal_precheck_passed   → applicability gate で処理済み
      - pat_obs.numeric_resolution_limited → quantitative_metrics
      - pat_obs.max_blockage_ratio     → quantitative_metrics
    """
    return PatObservation(
        goal_precheck_passed=True,  # applicability gate 通過済みが前提
        numeric_resolution_limited=scv_obs.quantitative_metrics["numeric_resolution_limited"],
        max_blockage_ratio=scv_obs.quantitative_metrics["max_blockage_ratio"],
    )
```

### 3.3 comparability を落とすケース

以下のケースでは comparability level が下がる。

**NOT_COMPARABLE に落とすケース**:

| ケース | 理由 |
|---|---|
| `path_model` が rc2 と v3 で異なる | 異なる operational model の出力を同一 threshold で比較する意味がない |
| applicability_drift が検出された | 一方が goal_precheck を通過し他方が不通過なら、比較対象の population が異なる |
| coverage_drift が検出された | 評価された / されていないの不一致 |

`path_model` 差は coverage_drift として report 済み（bridge_ci_contracts §3 field coverage table）だが、NOT_COMPARABLE への降格理由としても明示する。

**EVIDENCE_COMPARABLE に留まるケース（COMPONENT_VERDICT_COMPARABLE に上がれない）**:

| ケース | 理由 |
|---|---|
| metrics_drift が 1 件以上ある | observation が異なるので、同一 `scv_pat` に通しても verdict が異なりうる |

### 3.4 metrics_drift = 0 の位置づけ

`metrics_drift = 0` は `COMPONENT_VERDICT_COMPARABLE` の**必要条件**であるが、**十分条件ではない**。

十分条件は metrics_drift = 0 **かつ** coverage_drift = 0 **かつ** applicability_drift = 0 である。metrics_drift = 0 でも coverage や applicability が不一致なら comparability は NOT_COMPARABLE になる。

逆に、metrics_drift = 0 かつ coverage/applicability drift = 0 であれば、observation が同一であることが保証されるため、同一 `scv_pat` に通した verdict も必然的に一致する。この場合 `path_component_match = True` は自明であるが、それ自体が comparability の品質証明になる。

### 3.5 comparability 判定の formal logic

```python
def compute_path_comparability(
    compound_drift: CompoundDriftReport,
) -> CompoundPathComparability:
    """一化合物の Path component comparability を判定する"""

    # coverage or applicability の不一致 → 比較不能
    if compound_drift.coverage_drifts:
        return CompoundPathComparability.NOT_COMPARABLE
    if compound_drift.applicability_drifts:
        return CompoundPathComparability.NOT_COMPARABLE

    # 両方が未評価 → 比較不要（NOT_COMPARABLE ではなく special case）
    # ← この場合 drift report 自体が生成されないので、ここには到達しない

    # metrics drift あり → evidence は comparable だが verdict は不確定
    if compound_drift.metrics_drifts:
        return CompoundPathComparability.EVIDENCE_COMPARABLE

    # metrics / coverage / applicability 全て clean
    return CompoundPathComparability.COMPONENT_VERDICT_COMPARABLE
```

---

## 4. verdict match rate の意味

### 4.1 v3_shadow_verdict が None の間

`v3_shadow_verdict` が None の間、SCV-level の verdict match rate は定義できない。`verdict_match_rate` は `N/A` のままとする。

### 4.2 代替指標: path_component_match_rate

Path-only scope では verdict match rate の代替として `path_component_match_rate` を定義する。

```text
path_component_match_rate =
    count(path_component_match == True)
    / verdict_comparable_compound_count
```

ここで:
- **分子**: `path_component_match == True` の化合物数（rc2 PAT verdict と v3 Path projected verdict が一致）
- **分母**: `CompoundPathComparability == COMPONENT_VERDICT_COMPARABLE` の化合物数

**分母は全 compounds ではなく、comparable subset に限定する。** NOT_COMPARABLE や EVIDENCE_COMPARABLE の化合物は分母に含めない。理由は、比較不能な化合物を分母に入れると、coverage drift が多い run で rate が人工的に下がり、Path channel 自体の品質とは無関係な noise が入るためである。

### 4.3 bridge_ci_contracts §6 baseline との関係

bridge_ci_contracts §6 の baseline は以下のとおりである。

| metric | baseline 閾値 |
|---|---|
| verdict match rate | ≥ 95% |
| coverage drift rate | ≤ 5% |
| metrics drift count | = 0 |
| applicability drift rate | ≤ 5% |

Path-only scope では以下のように読み替える。

| metric | Path-only scope での読み替え | 閾値 |
|---|---|---|
| verdict match rate | `path_component_match_rate`（comparable subset 内） | ≥ 95% |
| coverage drift rate | Path channel の coverage_drift 率（全 compounds 分母） | ≤ 5% |
| metrics drift count | Path channel の metrics_drift 件数 | = 0 |
| applicability drift rate | Path channel の applicability_drift 率（全 compounds 分母） | ≤ 5% |

### 4.4 N/A から数値化への移行条件

`path_component_match_rate` が N/A から数値化される条件は以下の全てを満たす場合。

| 条件 | 意味 |
|---|---|
| `verdict_comparable_compound_count ≥ 1` | comparable subset が空でない |
| bridge comparator が 1 run 以上完了している | 実データが存在する |
| `comparator_scope == "path_only_partial"` | scope が明示されている |

数値化されても、これは `path_component_match_rate` であって `verdict_match_rate` ではない。operator-facing 表示では distinction を明示する（§5.3 参照）。

### 4.5 `verdict_match_rate` が N/A を脱する条件

SCV-level の `verdict_match_rate` が N/A を脱するのは、§2.4 の VN-01 から VN-06 が全て満たされ、`v3_shadow_verdict` が non-None になった時点である。それまでは N/A のままとする。

---

## 5. operator / CI / migration claim への影響

### 5.1 comparator scope を変えてはいけない条件

以下のいずれかに該当する限り、`comparator_scope` は `path_only_partial` から変更しない。

| 条件 ID | 条件 |
|---|---|
| CS-01 | comparable_channels に追加予定の channel（Cap / Catalytic）の T1 task が未 complete |
| CS-02 | 追加 channel の formal contract ADR が未 complete |
| CS-03 | 追加 channel の sidecar invariant test が 30 run green 未達 |
| CS-04 | 追加 channel の field coverage table が未 frozen |
| CS-05 | SCV integration mode（全 channel → single verdict）の設計 ADR が未 complete |

CS-01 から CS-05 のいずれかが残っている channel を `comparable_channels` に追加してはならない。Path 以外の channel を比較対象に含めない理由は、CS-01–CS-05 が当該 channel について未達であることで自動的に明文化される。

### 5.2 exploratory → required 昇格と comparability の関係

bridge_ci_contracts ADR-V3-06 §5 の昇格条件 PR-01 から PR-06 において、`path_component_match_rate` は以下のように関与する。

| PR 条件 | comparability との関係 |
|---|---|
| PR-03 component match rate が baseline 以上 | Path-only scope: `path_component_match_rate ≥ 95%`（comparable subset 分母） |
| PR-04 metrics_drift が 30 run で 0 件 | Path channel の metrics_drift に限定 |

**本文書は design-only 文書であり、exploratory → required 昇格を authorize しない。** Path P6 で comparability semantics を定義したこと自体は、昇格の policy authorization ではない。昇格判断は ADR-V3-06 の既存条件（PR-01 から PR-06 の全達成）を満たした場合の将来候補にとどまり、昇格の explicit authorization は ADR-V3-06 の改訂または full migration contract ADR で行う。

final verdict comparability（SCV-level）は required 昇格の必要条件ではない。SCV-level verdict comparability は full migration contract の問題であり、個別 channel の CI 昇格とは独立である。

### 5.3 operator-facing 表示規則

Path-only scope で operator-facing surface に表示すべきもの。

| 表示項目 | 表示内容 |
|---|---|
| `semantic_policy_version` | 現行 sidecar policy version |
| `comparator_scope` | `path_only_partial` |
| `comparable_channels` | `["path"]` |
| `[exploratory]` label | v3 関連の全 metric に付与 |
| rc2 verdict | primary 表示（変更なし） |
| v3_shadow_verdict | `N/A`（非表示でもよい） |
| `path_component_match_rate` | 数値化された場合のみ `[exploratory]` 付きで secondary 表示 |
| coverage / applicability drift summary | compound 数と割合 |

Path-only scope で operator-facing surface に表示**してはいけない**もの。

| 禁止項目 | 理由 |
|---|---|
| `verdict_match_rate` の数値 | v3_shadow_verdict が None の間は定義不能 |
| `path_component_match_rate` を `verdict_match_rate` と呼ぶこと | component match と verdict match の混同を防ぐ |
| v3 Path evidence state を verdict として表示すること | SC-01 違反（SCV のみが verdict を返す） |
| Cap / Catalytic が comparable であるかのような表示 | comparable_channels に含まれていない |
| drift summary なしの `path_component_match_rate` 単独表示 | rate だけでは comparable subset の大きさが不明 |

`path_component_match_rate` を表示する場合は、必ず以下を併記する。

```text
Path component match: 98.2% (163/166 comparable, 4 not_comparable, 170 total)
  [exploratory] scope=path_only_partial
  coverage_drift: 2 compounds
  applicability_drift: 2 compounds
  metrics_drift: 0
```

### 5.4 Cap / Catalytic を比較対象に含めない理由の明文化

`sidecar_run_record.json` の `comparable_channels` が `["path"]` であること自体が、Cap / Catalytic が比較対象外であることの明文化になる。追加の理由文書は不要だが、operator に対する説明が求められた場合は以下を参照する。

> Cap / Catalytic channel は `comparable_channels` に含まれていません。これは当該 channel の formal contract ADR が未完了であり、sidecar invariant test と field coverage table が freeze 要件を満たしていないためです（CS-01–CS-04）。比較対象への追加は、当該 channel の ADR complete + 30 run green 達成後に検討されます。

---

## 6. Path P6 closure checklist

本文書で定義した semantics を踏まえ、Path P6 を閉じるための checklist。

| item | status | 検証 |
|---|---|---|
| `CompoundPathComparability` 三段階が定義されている | この文書 §1.4 | — |
| comparability 判定の formal logic が定義されている | この文書 §3.5 | — |
| `path_component_match` の計算方法が定義されている | この文書 §3.1–§3.2 | — |
| `path_component_match_rate` の分母が定義されている | この文書 §4.2 | — |
| `v3_shadow_verdict` が None のままである条件が定義されている | この文書 §2.4 | — |
| `verdict_record.json` が schema reservation であり Layer 0 authority でないことが明記されている | この文書 §2.5 | — |
| channel-to-SCV-component mapping が UNKNOWN / deferred として明記されている | この文書 §2.2 | — |
| operator-facing 表示規則が定義されている | この文書 §5.3 | — |
| witness_drift が comparability を阻害しない理由が定義されている | この文書 §1.5 | — |
| metrics_drift = 0 が必要条件であり十分条件でない理由が定義されている | この文書 §3.4 | — |
| baseline 閾値の Path-only 読み替えが定義されている | この文書 §4.3 | — |
| CS-01–CS-05 が Cap/Catalytic 非対象の理由を自動的に明文化している | この文書 §5.1 | — |
| 本文書が required 昇格を authorize しないことが明記されている | この文書 §5.2 | — |

---

## 7. 本文書が閉じないもの

以下は本文書の scope 外であり、full migration contract ADR で扱う。

| topic | 理由 |
|---|---|
| SCV integration mode（全 channel → v3_shadow_verdict） | Path-only scope では SCV-level verdict を生成しない |
| channel-to-SCV-component mapping | §2.2 で UNKNOWN とした。v3 channel が rc2 SCV component にどう射影されるかは full migration ADR で定義する |
| `verdict_record.json` の Layer 0 authority 昇格 | §2.5 で schema reservation に限定した。`sidecar_run_record.json` からの authority 移行は full migration ADR で扱う |
| `verdict_match_rate` の数値化 | v3_shadow_verdict が None の間は定義不能 |
| hybrid SCV mode の採否 | §2.3 で棄却したが、full migration contract で再検討可能 |
| Cap / Catalytic の comparability semantics | 当該 channel の formal contract ADR に依存 |
| `comparator_scope` の `path_only_partial` → `full` への移行条件 | CS-01–CS-05 + VN-01–VN-06 の全達成後 |
| exploratory → required 昇格の explicit authorization | §5.2 で本文書は authorize しないと明記。ADR-V3-06 改訂で扱う |

---

*End of document*
