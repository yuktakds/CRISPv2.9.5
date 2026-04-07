# CRISP v3.x Bridge & CI Contracts

Status: Pre-implementation freeze  
Date: 2026-04-07  
Authority note: this unversioned filename is the canonical repo-carried bridge / CI contract note for the current sidecar scope.  
Parent: `v3x_evidence_channel_kernel_architecture_rev3.1.md` §I ADR Queue  
Scope: ADR-V3-05, ADR-V3-06, RC2Adapter field coverage table

---

## ADR-V3-05: Bridge Comparator Drift Attribution Policy

### 1. 背景

rev.3 §E は SCVBridge と RC2Adapter を定義し、rc2 frozen reference と v3.x shadow の比較を前提としている。しかし「drift が検出されたとき、それが何に起因するか」の taxonomy が凍結されていない。drift attribution が曖昧なままだと、bridge comparator の出力が「何かが違う」以上の情報を持てず、operator は行動判断ができない。

### 2. 判断

bridge comparator が report する drift を以下の 4 種に分類し、各 drift kind の意味・検出条件・operator-facing 表示規則を凍結する。

### 3. Drift Taxonomy

#### 3.1 `coverage_drift`

**意味**: rc2 と v3 で evidence channel の適用範囲が異なる。rc2 では評価された compound が v3 では評価されない、またはその逆。

**検出条件**:
- rc2 が当該 sensor の observation を持つが、v3 channel が `None`（前提条件不成立）を返した
- v3 channel が ChannelEvidence を返したが、rc2 に対応する sensor observation が存在しない
- rc2 の run-level diagnostics（例: `pathyes_rule1_applicability`）と v3 channel の applicability gate が異なる結論を出した

**典型例**:
- rc2 では `pathyes_goal_precheck_passed=True` だが v3 PathEvidence の goal_precheck が不成立（protein geometry interpretation の差異）
- rc2 では PAT 非適用（`pathyes_skip_code` あり）だが v3 PathEvidence が評価を実行した
- rc2 に Cap 観測がない run mode（`core-only`）で v3 CapEvidence が stub 評価を返した

**report field**:

```python
@dataclass(frozen=True, slots=True)
class CoverageDrift:
    molecule_id: str
    channel_id: str
    rc2_evaluated: bool        # rc2 が当該 sensor を評価したか
    v3_evaluated: bool         # v3 channel が ChannelEvidence を返したか
    rc2_skip_reason: str | None
    v3_skip_reason: str | None
```

#### 3.2 `metrics_drift`

**意味**: rc2 と v3 の両方が同一 evidence を評価し、coverage は一致するが、定量観測値が異なる。

**検出条件**: 対応する quantitative field ペアの差分が定義済み tolerance を超える。

**対象 field ペアと tolerance**:

| rc2 field | v3 bridge field | tolerance | 根拠 |
|---|---|---|---|
| `sensors.pat.max_blockage_ratio` | `quantitative_metrics["max_blockage_ratio"]` | 1e-6 (absolute) | deterministic voxel 計算 |
| `sensors.anchoring.best_target_distance` | `quantitative_metrics["best_target_distance"]` | 1e-9 (absolute) | deterministic distance |
| `sensors.offtarget.best_offtarget_distance` | `quantitative_metrics["best_offtarget_distance"]` | 1e-9 (absolute) | deterministic distance |
| `sensors.pat.apo_accessible_goal_voxels` | `exploration_slice["apo_accessible_goal_voxels"]` | 0 (exact) | integer count |
| `exploration_log.feasible_count` | `exploration_slice["feasible_count"]` | 0 (exact) | integer count |
| `sensors.pat.numeric_resolution_limited` | `quantitative_metrics["numeric_resolution_limited"]` | exact match | boolean |

tolerance 超過は `metrics_drift` として report する。tolerance 以内は drift なしとする。

**report field**:

```python
@dataclass(frozen=True, slots=True)
class MetricsDrift:
    molecule_id: str
    channel_id: str
    field_name: str
    rc2_value: float | int | bool | None
    v3_value: float | int | bool | None
    tolerance: float
    delta: float | None         # 数値 field の場合
```

#### 3.3 `witness_drift`

**意味**: metrics は tolerance 以内だが、witness（PASS 証拠として提示される pose）が異なる。

**検出条件**:
- 両方が SUPPORTED / PASS で、witness_pose_id が異なる
- witness pose の付帯情報（`stage_id`, `translation_type`, `trial_number`, `conformer_id`）が異なる

**重要な注意**: witness drift は必ずしも不整合ではない。複数の pose が同一 threshold を満たす場合、tiebreak の差異で異なる witness が選ばれることは正当でありうる。したがって witness_drift は**情報提供**であり、自動 fail gate ではない。

**report field**:

```python
@dataclass(frozen=True, slots=True)
class WitnessDrift:
    molecule_id: str
    channel_id: str
    rc2_witness: Mapping[str, object] | None
    v3_witness: Mapping[str, object] | None
    metrics_within_tolerance: bool  # metrics は一致しているか
```

#### 3.4 `applicability_drift`

**意味**: channel の前提条件（applicability gate）の判定結果自体が rc2 と v3 で異なる。`coverage_drift` と重複しうるが、applicability_drift はより限定的に「同一入力で同一前提条件を問うた結果が異なる」ケースを捕捉する。

**coverage_drift との区別**:
- `coverage_drift`: rc2 と v3 で「そもそも何を評価したか」の差異（run mode 差、sensor 有無の差、channel 構成の差）
- `applicability_drift`: 同一 evidence question を問う意図があるのに、前提条件の判定結果が食い違った場合

**検出条件**:
- rc2 `pathyes_goal_precheck_passed` と v3 PathEvidence の goal_precheck 結果が異なる
- rc2 `pathyes_rule1_applicability` と v3 PathEvidence の applicability gate 結果が異なる
- rc2 の当該 sensor が `UNCLEAR_INPUT_MISSING` を返したが、v3 channel は正常に evaluation を完了した（またはその逆）

**report field**:

```python
@dataclass(frozen=True, slots=True)
class ApplicabilityDrift:
    molecule_id: str
    channel_id: str
    gate_name: str              # "goal_precheck", "rule1_applicability" 等
    rc2_result: bool | str | None
    v3_result: bool | str | None
    diagnostic: str
```

### 4. Drift Report の構造

```python
@dataclass(frozen=True, slots=True)
class CompoundDriftReport:
    """一化合物に対する drift report"""
    molecule_id: str
    rc2_verdict: str            # PASS / FAIL / UNCLEAR
    v3_shadow_verdict: str | None  # current Path-only partial comparator では通常 None
    verdict_match: bool | None     # final verdict comparable な場合のみ bool
    coverage_drifts: tuple[CoverageDrift, ...]
    metrics_drifts: tuple[MetricsDrift, ...]
    witness_drifts: tuple[WitnessDrift, ...]
    applicability_drifts: tuple[ApplicabilityDrift, ...]


@dataclass(frozen=True, slots=True)
class RunDriftReport:
    """一 run に対する drift report"""
    run_id: str
    rc2_policy_version: str
    v3_policy_version: str
    total_compounds: int
    verdict_comparable_compound_count: int
    verdict_match_count: int          # comparable compound に限定
    verdict_mismatch_count: int       # comparable compound に限定
    compounds: tuple[CompoundDriftReport, ...]

    # run-level summary
    coverage_drift_count: int
    metrics_drift_count: int
    witness_drift_count: int
    applicability_drift_count: int
```

### 5. Drift → Action の対応

| drift kind | 自動 fail gate か | operator action |
|---|---|---|
| `coverage_drift` | **No** — sidecar mode では情報提供 | channel applicability gate の calibration を検討 |
| `metrics_drift` | **Yes** — tolerance 超過は bridge mismatch | projector / builder の determinism を調査 |
| `witness_drift` | **No** — 情報提供 | tiebreak rule の一致を確認 |
| `applicability_drift` | **No** — sidecar mode では情報提供 | gate 条件の乖離原因を調査 |

sidecar mode（rev.3 §G の T3a/T4 相当）では、drift は報告対象であり自動停止条件ではない。ただし `metrics_drift` は FB-BRIDGE-01 の判定入力になるため、蓄積パターンに注意を要する。

### 6. Drift Report の artifact 層

drift report は rev.3 §D.1 の Layer 1 artifact とする。通常 run では `generator_manifest.json` に generator entry のみを登録し、`expected_output_digest` を記録する。bridge comparison run（`--bridge-compare` flag 付き）では Layer 1 を常時出力する。

---

## ADR-V3-06: Operator / CI Semantic-Policy Separation

### 1. 背景

SoT §18 は CI に `rc2-frozen` と `v3x-exploratory` の 2 suite 分離を要求し、required follow-up ADR として operator / CI semantic-policy separation を挙げている。rev.3 §G.9 は `ci/v3-exploratory-lane` を branch 計画に含めている。しかし「exploratory が required に昇格する条件」と「昇格しない条件」が文書化されていない。

### 2. 判断

以下の分離規則と昇格条件を凍結する。

### 3. CI suite 分離

#### 3.1 rc2-frozen suite（既存）

既存 workflow: `.github/workflows/v29-required-matrix.yml`

含まれる required jobs（SoT §18.2 確認済み）:
- `required / benchmark-integrated-smoke`
- `required / production-integrated-smoke`
- `required / ci-sized-full-fixture`
- `required / config-guard-matrix`
- `required / replay-inventory-crosscheck`
- `required / cap-artifact-invariants`
- `required / v2.9.5-matrix`（aggregate gate）

**不変条件**: v3.x の実装は rc2-frozen suite の job を削除・弱体化・条件変更してはならない。rc2-frozen suite が red になった場合、v3.x の変更が原因でないことを証明しない限り merge を停止する。

#### 3.2 v3x-exploratory suite（新規）

新規 workflow: `.github/workflows/v3x-exploratory.yml`

初期 jobs:
- `exploratory / v3-policy-contracts` → `tests/v3/test_policy.py`
- `exploratory / v3-path-channel` → `tests/v3/test_path_channel.py`, `tests/v3/test_path_invariants.py`, `tests/v3/test_path_applicability.py`, `tests/v3/test_path_projector.py`
- `exploratory / v3-scv-bridge` → `tests/v3/test_scv_bridge.py`
- `exploratory / v3-sidecar-invariants` → `tests/v3/test_sidecar_invariants.py`
- `exploratory / v3-artifact-sink` → `tests/v3/test_artifact_sink.py`
- `exploratory / v3-rc2-bridge` → `tests/v3/test_rc2_bridge.py`

後続追加予定:
- `exploratory / v3-cap-channel`
- `exploratory / v3-catalytic-channel`
- `exploratory / v3-bridge-comparator`

**全ての exploratory jobs は `required: false`** とする。

#### 3.3 sidecar invariant test の特殊位置

`exploratory / v3-sidecar-invariants`（FB-SIDE-01 に対応）は exploratory suite 内にあるが、**sidecar hook が default on に昇格する場合、事前に required へ移動しなければならない**。sidecar hook が default off の間は exploratory で十分。

### 4. exploratory job が required へ昇格しない条件

以下のいずれかに該当する限り、当該 job は exploratory に留まる。

| 条件 ID | 条件 | 理由 |
|---|---|---|
| NP-01 | 当該 channel が sidecar mode でのみ動作し、public verdict に影響しない | rc2 verdict を守る限り exploratory で十分 |
| NP-02 | 当該 channel の formal contract ADR（ADR-V3-02/03/04）が未完了 | contract 未凍結の test を required にすると interface 変更で red が頻発する |
| NP-03 | bridge comparator の drift data が bridge baseline（後述）を満たしていない | 比較品質未確認の検証を required gate にするのは早すぎる |
| NP-04 | 当該 test が Windows CI 環境で安定に通らない | rc2-frozen suite は Windows-based であり、platform 不安定な test を required にすると frozen suite を巻き込むリスクがある |

### 5. exploratory job が required 昇格候補になる条件

以下の**全て**を満たした場合、当該 job は required 昇格候補となる。昇格自体は PR review + explicit merge decision で行う。

| 条件 ID | 条件 | 検証方法 |
|---|---|---|
| PR-01 | 当該 channel の formal contract ADR が complete である | ADR document が repo に merge 済み |
| PR-02 | sidecar invariant test（FB-SIDE-01）が直近 30 run 連続 green | CI history |
| PR-03 | bridge comparator の verdict match rate が baseline 閾値以上 | RunDriftReport の `verdict_match_count / total_compounds` |
| PR-04 | metrics_drift が直近 30 run で 0 件 | RunDriftReport 集計 |
| PR-05 | 当該 test が Windows CI 環境で直近 30 run 連続 green | CI history |
| PR-06 | rc2-frozen suite に対する regression がないことを確認済み | rc2-frozen suite が当該 PR branch で全 green |

### 6. bridge baseline の定義

bridge comparator の品質を測る baseline は以下で定義する。**適用条件**は、`verdict_comparability != not_comparable` かつ baseline の対象 metric に必要な channel が `comparable_channels` に含まれる場合に限る。Path-only partial comparator 段階では、full verdict baseline ではなく **path-only partial comparison baseline** として解釈する。

| metric | baseline 閾値 | 適用条件 | 意味 |
|---|---|---|---|
| verdict match rate | ≥ 95% | final verdict comparable な compound に限定 | comparable verdict がある範囲で v3 shadow verdict が rc2 verdict と一致する割合 |
| coverage drift rate | ≤ 5% | `path` channel comparable case | coverage_drift が発生する compound の割合 |
| metrics drift count | = 0 | `path` channel comparable case | deterministic 不一致は許容しない |
| applicability drift rate | ≤ 5% | applicability gate を双方が保持する case | applicability_drift が発生する compound の割合 |

baseline 閾値は初期値であり、bridge comparator の実運用データに基づいて ADR 改訂で調整する。

Additional rule for the current Path-only partial comparator:
- when `v3_shadow_verdict` is `None` for all compounds in scope, verdict match rate shall be reported as `N/A` rather than `0%`
- `bridge_comparison_summary.json` must carry:
  - `semantic_policy_version`
  - `comparator_scope` (`"path_only_partial"` or `"full_bridge"`)
  - `verdict_comparability` (`"not_comparable"`, `"partially_comparable"`, `"fully_comparable"`)
  - `comparable_channels`

### 7. operator-facing report の分離

operator-facing report（`eval_report`, `qc_report` 等）には `semantic_policy_version` を常に表示する（rev.3 §A.2 SM-02, SoT §18.4）。なお、current Path-only partial comparator では final v3 shadow verdict を canonical 出力としないため、`v3_shadow_verdict` は将来の full-channel bridge までは `None` を許容する。rc2 verdict と v3 shadow verdict を同一 report 上に並べる場合は、以下を遵守する。

- rc2 verdict を primary として表示する（sidecar mode の間）
- v3 shadow verdict は `[exploratory]` ラベル付きで secondary 表示する
- 両者を混合した verdict summary を生成しない
- drift summary は付録として添付可能だが、primary verdict section に混在させない

---

## RC2Adapter Field Coverage Table

### 1. 目的

RC2Adapter が rc2 observation を `SCVObservationBundle` に変換する際の field 対応、drift 分類、未実装時の挙動を 1 枚で固定する。

### 2. 凡例

- **rc2 source**: rc2 evidence artifact の field path
- **bridge target**: SCVObservation 内の対応 field
- **drift kind**: 差異検出時の drift 分類
- **missing behavior**: rc2 source が存在しない場合の adapter 挙動

### 3. PathEvidence channel（rc2 PAT sensor 対応）

| rc2 source | bridge target | drift kind | missing behavior |
|---|---|---|---|
| `sensors.pat.max_blockage_ratio` | `quantitative_metrics["max_blockage_ratio"]` | `metrics_drift` | → `evaluable=False`, reason=`"rc2_pat_not_evaluated"` |
| `sensors.pat.path_model` | `witness_bundle["path_family"]` | `coverage_drift`（model 不一致時） | → field 欠損を記録、比較 skip |
| `sensors.pat.goal_mode` | `witness_bundle["goal_mode"]` | 参照用（drift 対象外） | → 無視 |
| `sensors.pat.goal_precheck_passed` | adapter-level gate | `applicability_drift` | → `rc2_evaluated=False` |
| `sensors.pat.goal_precheck_reason` | diagnostic（bridge target なし） | 参照用 | → 無視 |
| `sensors.pat.goal_clearance_max_0` | `exploration_slice["goal_clearance_max_0"]` | `metrics_drift` | → None |
| `sensors.pat.apo_accessible_goal_voxels` | `exploration_slice["apo_accessible_goal_voxels"]` | `metrics_drift` | → None |
| `sensors.pat.numeric_resolution_limited` | `quantitative_metrics["numeric_resolution_limited"]` | `metrics_drift` | → None |
| `sensors.pat.witness_pose.pose_id` | `witness_bundle["witness_pose_id"]` | `witness_drift` | → None |
| `sensors.pat.witness_pose.stage_id` | `witness_bundle["witness_stage_id"]` | `witness_drift` | → None |
| `sensors.pat.witness_pose.translation_type` | `witness_bundle["witness_translation_type"]` | `witness_drift` | → None |
| `sensors.pat.witness_pose.trial_number` | `witness_bundle["witness_trial_number"]` | `witness_drift` | → None |
| `sensors.pat.witness_pose.conformer_id` | `witness_bundle["witness_conformer_id"]` | `witness_drift` | → None |

### 4. PathEvidence channel（rc2 replay_audit 対応）

| rc2 source | bridge target | drift kind | missing behavior |
|---|---|---|---|
| `replay_audit.pathyes_goal_precheck_passed` | applicability gate 比較 | `applicability_drift` | → 比較 skip、coverage_drift に fallback |
| `replay_audit.pathyes_rule1_applicability` | applicability gate 比較 | `applicability_drift` | → 比較 skip |
| `replay_audit.pathyes_mode_resolved` | diagnostic（bridge target なし） | 参照用 | → 無視 |
| `replay_audit.pathyes_skip_code` | coverage 判定 | `coverage_drift` | → None（skip なし = 評価済みと解釈） |
| `replay_audit.pathyes_diagnostics_status` | diagnostic | 参照用 | → 無視 |
| `replay_audit.pathyes_state_source` | diagnostic | 参照用 | → 無視 |

### 5. PathEvidence channel（rc2 theta_rule1_resolution 対応）

| rc2 source | bridge target | drift kind | missing behavior |
|---|---|---|---|
| `theta_rule1_resolution.theta_rule1` | `quantitative_metrics["theta_rule1"]` | `metrics_drift` | → None（v3 側で独自に threshold 解決する場合） |
| `theta_rule1_resolution.resolution_status` | diagnostic | 参照用 | → 無視 |
| `theta_rule1_resolution.runtime_contract` | diagnostic | 参照用 | → 無視 |

注記: `theta_rule1_resolution.json` は rc2 では resolved-threshold provenance artifact であり、path obstruction semantics ではない（SoT §13.6.7）。v3 PathEvidence channel は `theta_rule1` を内部 threshold として参照しうるが、bridge 上は metrics comparison の対象とする。

### 6. Anchoring / OffTarget（rc2 sensor → v3 channel 対応、将来用）

現時点では PathEvidence channel のみが T1a 実装対象であるため、Anchoring / OffTarget の bridge 対応は stub とする。以下は将来の Cap / Catalytic channel 実装時に正式化する。

| rc2 source | bridge target | drift kind | missing behavior |
|---|---|---|---|
| `sensors.anchoring.best_target_distance` | stub: `quantitative_metrics["best_target_distance"]` | `metrics_drift` | → None |
| `sensors.anchoring.verdict` | stub: `observation_met` | `coverage_drift` | → 比較 skip |
| `sensors.anchoring.witness_pose.*` | stub: `witness_bundle["anchoring_witness_*"]` | `witness_drift` | → None |
| `sensors.offtarget.best_offtarget_distance` | stub: `quantitative_metrics["best_offtarget_distance"]` | `metrics_drift` | → None |
| `sensors.offtarget.verdict` | stub: `observation_met` | `coverage_drift` | → 比較 skip |

### 7. Exploration log（共通）

| rc2 source | bridge target | drift kind | missing behavior |
|---|---|---|---|
| `exploration_log.feasible_count` | `exploration_slice["feasible_count"]` | `metrics_drift` | → None |
| `exploration_log.total_trials` | `exploration_slice["total_trials"]` | `metrics_drift` | → None |
| `exploration_log.stage_id_found` | `exploration_slice["stage_id_found"]` | `witness_drift` | → None |
| `exploration_log.translation_type_found` | `exploration_slice["translation_type_found"]` | `witness_drift` | → None |
| `exploration_log.c1_rejected` | diagnostic | 参照用 | → 無視 |
| `exploration_log.active_site_anchor_xyz` | diagnostic | 参照用 | → 無視 |

### 8. Run-level fields（比較対象外）

以下の rc2 fields は compound-level bridge 比較の対象外とする。run-level の整合性検証は rc2-frozen suite が担い、bridge comparator は compound-level evidence 比較に専念する。

比較対象外:
- `run_manifest.json` の全 field（run-level provenance）
- `output_inventory.json` の全 field（inventory 整合性）
- `run_monitor.json` の全 field（実行 metadata）
- `replay_audit` の consistency / hash / inventory 系 field（replay infrastructure）
- `mapping_table.parquet`（Cap channel 正式実装まで bridge 対象外）
- `falsification_table.parquet`（Cap channel 正式実装まで bridge 対象外）
- `rule3_trace_summary.json`（Catalytic channel 正式実装まで bridge 対象外）

### 9. adapter の設計原則

RC2Adapter は以下の原則に従う。

1. **存在しない field は None にする**: rc2 artifact に field が存在しない場合、adapter は推測や default 値で埋めない。bridge comparator は None field を「比較不能」として扱う。
2. **型変換のみ行い、意味変換は行わない**: rc2 の `best_target_distance` を v3 の `quantitative_metrics["best_target_distance"]` に型変換することは許可する。rc2 の `best_target_distance` を v3 の「path obstruction evidence」に意味変換することは禁止する。
3. **未対応 channel は stub にする**: T1a 時点では PathEvidence 以外の channel adapter は stub であり、全 field を None にする。stub は `coverage_drift` として正直に report する。
4. **diagnostic field は bridge target に含めない**: rc2 の diagnostic-only field（`goal_precheck_reason`, `pathyes_diagnostics_status` 等）は bridge 比較の対象にしない。参照用として adapter が読むことは許可するが、drift 判定には使わない。

---

## 三文書間の整合性

| rev.3 参照 | 本文書の対応箇所 | 整合性 |
|---|---|---|
| §E.2 SCVObservation の `quantitative_metrics` | field coverage table §3–§7 の bridge target 列 | field 名が一致 |
| §E.2 `witness_bundle` | field coverage table の `witness_drift` 対象 field | 一致 |
| §E.2 `exploration_slice` | field coverage table §7 | 一致 |
| §H.5 FB-BRIDGE-01 | ADR-V3-05 §5 の metrics_drift → 調査 action | FB-BRIDGE-01 の input = metrics_drift 蓄積 |
| §H.1 FB-SIDE-01 | ADR-V3-06 §3.3 sidecar invariant の特殊位置 | sidecar hook default on 前に required 昇格必須 |
| §I ADR-V3-05 | 本文書 ADR-V3-05 | 解決済み |
| §I ADR-V3-06 | 本文書 ADR-V3-06 | 解決済み |
| §C.6 evaluate returns None | ADR-V3-05 §3.1 coverage_drift / §3.4 applicability_drift | None 時の drift 分類が明確 |
| §G.4 goal_precheck run-level 分離 | field coverage table §3 `goal_precheck_passed` → applicability_drift | 一致 |

---

*End of document*
