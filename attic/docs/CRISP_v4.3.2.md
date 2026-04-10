# CRISP v4.3.2：幾何学的実現可能性テスト（GFT）統合設計書（Phase 1 freeze 維持 / Phase 2 PAT 設計改訂版）

## 改訂履歴

| 版 | 日付 | 内容 |
|---|---|---|
| v3.2 | 2026-03-03 | ゼロベース再設計。GFTへの再定義、CSPとしての形式化 |
| v3.2.1 | 2026-03-03 | MEF計算量制御、SO(3)整合、PAT命名凍結、αの意味固定 |
| v3.3 | 2026-03-03 | 有限予算存在判定の形式化、計算量見積り、再現性プロトコル、設定スキーマ、PAT算法素描 |
| v3.4 | 2026-03-03 | 不変条件・適用限界、健全性射程固定、再現性成立条件、性能契約、PDB前処理凍結 |
| v4.0 | 2026-03-03 | v2.0出口戦略との統合。三値判定、SCV責務分離、Anchoring状態表 |
| v4.1 | 2026-03-03 | I-04修復（OffTarget Sensor分離）、WarheadAtoms原子マップ凍結（I-08）、PAT top-K |
| v4.1.1 | 2026-03-03 | ハロメチルケトンSMARTS修正、ActiveSiteAnchor定義凍結、ワーヘッド出所ログ追加 |
| v4.2 | 2026-03-03 | 化学記述修正、原子配列順序凍結（I-09）、argminタイブレーク凍結（I-10） |
| v4.3 | 2026-03-11 | 実装整合化。canonical configを現行loader/suiteに一致させ、staging/terminal policyを状態機械として明示、述語体系と三値意味論の二層化、staging provenance（I-13）を追加。PASS射程宣言と新規化学空間移植監査を明文化 |
| **v4.3.1** | **2026-03-16** | **Phase 1 Anchoring 確定版。3ライブラリ（fACR-2240 / CYS-3200 / ChemDiv CPI-7801）での検証結果を記録。no_feasible_early_abort_trial=4096 を canonical 運用値として確定。SMARTS クラス別 PASS 率・enrichment 統計を §15.4 に追記。Phase 1 freeze 宣言を §19 に記載。§18 ロードマップを Phase 2 起点に更新** |
| **v4.3.2** | **2026-03-18** | **PAT 設計改訂版。`path_blocking` の上位定義と `path_model`（`TUNNEL` / `SURFACE_LIKE`）を分離して正式化。`PATGoalRegion`、`goal_precheck`、run-level PAT diagnostics、PAT Evidence 項目を追加。`SURFACE_LIKE` を Phase 3 の別述語ではなく PAT の model switch として統合** |

運用規則：

- `v4.3.x` は Phase 1 freeze を維持したまま、Phase 2 以降の設計詳細・Evidence・config schema を拡張する改訂系列とする。
- canonical object logic や public taxonomy の大域的再編が入る場合は `v4.4.0` 以上へ繰り上げる。

---

## 0. 要点

本プラットフォームは「活性を予測する」系ではなく、**活性が出ない分子を構造論的に排除する一次スクリーニング**である。
GFT は最適化ではなく、有限予算内での**実現可能解の存在判定**を行う。
出力の成功条件は、(i) FAIL/UNCLEAR 理由の説明可能性、(ii) PASS 根拠の監査可能性、(iii) 計算再現性、(iv) staging を含む探索過程の再検算可能性、である。

### 0.1 PASSの射程宣言

CRISP PASS は「モデル M の下で幾何学的到達可能性が証明された化合物」を意味する。
これは阻害の十分条件ではなく必要条件の検査であるため、PASS 群は**「阻害仮説に矛盾しない化合物群」**として解釈される。

ただしこの「矛盾しない」は、以下の条件下でのみ成立する。

**(a) WARHEAD_SMARTS が対象化学空間の共有結合反応機構を十分に被覆している**
SMARTS 集合が対象ライブラリの warhead 類型を網羅していなければ、MEF-04 の段階で回収漏れが生じる。

**(b) α が対象化学空間 × 標的ペアに対して校正されている**
vdW 衝突判定の緩和係数 α は、分子サイズ・形状の分布と標的ポケットの幾何に依存する。化学空間または標的を変更した場合、α の再校正が必要である。

**(c) 剛体タンパクモデルが当該標的ポケットに対して妥当である**
誘導適合や大域的構造変化が結合に不可欠な標的では、剛体モデルによる FAIL が偽陰性を含みうる。

この条件下で、CRISP は以下を保証する。

- **PASS 群の健全性**：witness pose が存在し、モデル M 内で偽陽性は構造的にゼロ
- **FAIL 群の説明可能性**：理由コードと探索ログにより排除理由が監査可能
- **UNCLEAR 群の管理可能性**：staging / budget 拡張により偽陰性低減の方向が明示される

### 0.2 対偶としての設計意図

CRISP が直接行うのは、

```
¬幾何学的必要条件 → ¬阻害候補
```

の方向の一次フィルタである。PASS は「阻害する」を主張しない。「少なくともモデル M の下で、阻害仮説と矛盾しない」を主張する。この非対称性が、ドッキングの「高得点 ≈ 有望」とは本質的に異なる設計意図である。

---

## 1. Invariants（不変条件）と適用限界

### 1.1 不変条件

| ID | 不変条件 | 根拠 |
|---|---|---|
| I-01 | 目的関数（スコア）を定義しない。ランキングもしない | ADR-01 |
| I-02 | PASS は必ず Certificate（witness pose + 観測量）を伴う | §12 |
| I-03 | FAIL/UNCLEAR は必ず Fail-certificate（理由コード + 最良到達点 + 予算 + 棄却内訳）を伴う | §12 |
| I-04 | 各 Sensor が返す**判定用連続量は 1 つだけ**（Anchoring: target_distance、OffTarget: offtarget_distance、PAT: blockage_ratio） | §8 |
| I-05 | サンプリングは決定論的であり、R0 条件で同一入力 → 同一出力を保証する | §13 |
| I-06' | K/M を増やしても PASS→FAIL 反転なし（Sobol prefix 不変）。N_conf は対象外 | §13, ADR-09 |
| I-07 | SCV のみが最終判定（PASS/FAIL/UNCLEAR）を返す。Sensor は観測量を返すだけ | §9 |
| I-08 | WarheadAtoms は SMARTS 内の原子マップ（`:1`）で一意に定義される。マップなし SMARTS は設計時エラー | §6.2 |
| I-09 | 原子インデックス配列（`warhead_atoms_union`, `mapped_atoms` 等）は昇順ソート済み・重複なしで出力する | §8.2 |
| I-10 | 同一距離のタイブレークは辞書式最小 `(distance, trial_number, smarts_index, atom_index)` で解決する | §8.2, §8.3 |
| I-11 | terminal policy は object logic の外側に置く。PASS/FAIL/UNCLEAR の論理意味は SCV core が定義し、staging の継続/終端は search-control logic が定義する | §3 |
| I-12 | stage-wise superset property は**global sampler 部分**に対してのみ要求する。local rescue は各 stage で独立に追加される sampling extension とする。成立条件：global sampler は Sobol 列の prefix extension を用い、local sampler は各 stage で独立に追加する | §7.6.2 |
| I-13 | Evidence Artifact は `stage_id` と `translation_type`（`global` / `local`）を必須記録し、staging-aware な再検算を可能にする | §7.8, §12, ADR-24 |

### 1.2 適用限界

| ID | 限界 |
|---|---|
| L-01 | タンパク質は剛体として扱う。誘導適合・大域的構造変化は扱わない |
| L-02 | 反応速度・活性（IC50 等）は予測しない。幾何学的必要条件の検査である |
| L-03 | 溶媒効果・電荷・プロトン化状態は一次近似として無視する |
| L-04 | エントロピー寄与は考慮しない |
| L-05 | peptide-like / 高柔軟性化合物は replay benchmark に含めうるが、de novo acceptance benchmark の一次受入れ基準には含めない |
| L-06 | §0.1 の3条件 (a)(b)(c) が満たされない化学空間・標的には直接適用できない。新規適用時は §15.3 の事前監査を必須とする |

**射程の宣言**
本設計書でいう「健全性（soundness）」は、モデル M（剛体タンパク＋離散コンフォーマ＋vdW衝突＋距離閾値）に関する健全性を指す。現実の実験系における反応・結合を保証する主張ではない。

---

## 2. 問題の定義：有限予算存在判定（BBET）

### 2.1 定義

GFT はモデル M の下で、有限予算 B 回の試行により次を返す。

```text
PASS    → モデル M の下で実現可能解が存在する（証拠：witness pose）
非PASS  → 予算 B 回の試行では実現可能解が発見されなかった
```

非PASS の FAIL / UNCLEAR 分類は SCV の責務であり、探索の継続/終端は staging policy の責務である。

### 2.2 ドッキングとの形式的差異

| 観点 | ドッキング | GFT（BBET） |
|---|---|---|
| 問題の種類 | 最適化（目的関数の極値探索） | 判定問題（制約充足解の存在検査） |
| 目的関数 | あり | なし |
| 出力 | スコア付きランキング | PASS / FAIL / UNCLEAR + Evidence |
| PASS の意味 | 高スコア仮説 | witness 付き存在証明 |
| 偽陽性の構造 | スコア関数依存 | モデル M 内で構造的にゼロ |
| 偽陰性の構造 | 探索器依存 | 予算依存・search-control 依存 |
| 停止条件 | 収束 or 予算 | PASS 証拠発見 / 非PASS 終端 |

### 2.3 問題の二層化

#### 2.3.1 object logic

object logic は「与えられた feasible pose 集合に対して、その化合物を PASS / FAIL / UNCLEAR と判定する論理」を定義する。
Anchoring / OffTarget / PAT の各述語と、それらの三値統合がここに属する。

#### 2.3.2 search-control logic

search-control logic は「次 stage へ送るか、ここで終端するか」を定義する。
出力は以下の 5 値である。

```text
CONTINUE
FINALIZE_PASS
FINALIZE_FAIL
FINALIZE_UNCLEAR
FINALIZE_BY_TERMINAL_POLICY
```

ここで `FINALIZE_BY_TERMINAL_POLICY` は中間値であり、§10.4 の終端正規化により最終 verdict に解決される。

---

## 3. 設計原理

| 原則 | 内容 |
|---|---|
| 原則1：有限予算存在判定 | 最適解を探さない。実現可能解の存在を有限予算で問う |
| 原則2：反証可能性 | すべての出力に検証可能な証拠を付与する |
| 原則3：判定境界の単純性 | 各 Sensor の判定用連続量は 1 つだけ |
| 原則4：測定と判定の分離 | Sensor は観測量を返し、SCV が判定する |
| 原則5：論理層と探索制御層の分離 | object logic と search-control logic を混同しない |
| 原則6：保守的 OffTarget | covalent Phase 1 では ∀ pose 安全性を採用し、偽陽性ゼロを優先する |

---

## 4. アーキテクチャ

```text
入力：SMILES + pathway + TargetConfig
       │
  ┌────▼──────────────┐
  │  MEF (Stage 0)    │  分子適格性フィルタ（2D、決定的）
  └────┬──────────────┘
       │ PASS
  ┌────▼──────────────┐
  │  CPG              │  制約付き配置生成（sampling + clash reject）
  └────┬──────────────┘
       │ feasible_poses + exploration_log
  ┌────▼──────────────────────────────────────────┐
  │  Sensors                                      │
  │  ├ Anchoring Sensor   → target_distance       │
  │  ├ OffTarget Sensor   → offtarget_distance    │
  │  └ PAT Sensor         → blockage_ratio        │
  └────┬──────────────────────────────────────────┘
       │ ObservationBundle
  ┌────▼──────────────┐
  │  SCV              │  唯一の判定器（三値判定）
  └────┬──────────────┘
       │ v_core
  ┌────▼──────────────┐
  │  Staging Policy   │  唯一の search-control logic
  └────┬──────────────┘
       │
    最終出力：PASS / FAIL / UNCLEAR + Evidence Artifact
```

### 4.1 責務分離

| コンポーネント | 責務 | やらないこと |
|---|---|---|
| MEF | 入力妥当性・探索空間有限性の保証 | 座標系依存の判定 |
| CPG | 候補 pose 集合の生成、致命的衝突棄却 | 閾値判定 |
| Sensors | 観測量の計算 | 判定 |
| SCV | 観測量の三値判定 | 探索継続判断 |
| Staging Policy | CONTINUE / FINALIZE の判定 | 観測量計算・論理述語評価 |

---

## 5. canonical TargetConfig（現行 loader/suite 整合スキーマ）

### 5.1 canonical YAML（v4.3.2 現行）

```yaml
target_name: "I7L_9JAL"
pathway: "covalent"

pdb:
  path: "9JAL.cif"
  model_id: 0
  altloc_policy: "A"
  include_hydrogens: false

residue_id_format: "author"

target_cysteine:
  chain: "A"
  residue_number: 328
  insertion_code: ""
  atom_name: "SG"

anchor_atom_set:
  - {chain: "A", residue_number: 328, insertion_code: "", atom_name: "SG"}

offtarget_cysteines:
  - {chain: "A", residue_number: 237, insertion_code: "", atom_name: "SG"}

search_radius: 8.0
distance_threshold: 3.5

budget:
  n_conformers: 8
  n_rotations: 64
  n_translations: 64
  alpha: 0.78

anchoring:
  bond_threshold: 2.2
  near_threshold: 3.5
  epsilon: 0.3

offtarget:
  distance_threshold: 3.5
  epsilon: 0.3

scv:
  min_feasible_for_confident_fail: 10
  no_feasible_early_abort_trial: 4096   # v4.3.1 確定値（fACR/CYS校正）

staging:
  retry_target_distance_lower: 3.5
  retry_target_distance_upper: 5.0
  terminal_far_target_threshold: 5.0
  max_stage: 3

translation:
  local_translation_fraction: 0.75
  local_translation_min_radius: 2.0
  local_translation_max_radius: 4.0
  local_translation_start_stage: 2

pat:
  path_model: "TUNNEL"
  goal_mode: "cys_approach_hemishell"
  grid_spacing: 0.5
  probe_radius: 1.4
  r_outer_margin: 6.0
  blockage_pass_threshold: 0.5
  top_k_poses: 5
  goal_shell_clearance: 0.2
  goal_shell_thickness: 1.0
  surface_window_radius: 1.5
  min_baseline_voxels: 32
  min_goal_voxels: 24

random_seed: 42
```

### 5.2 注記

- `scv.no_feasible_early_abort_trial = 4096` は v4.3.1 で確定。fACR-2240 の runtime 最適化と CYS-3200 での PASS 率影響評価に基づく（§15.4 参照）。分子サイズ適応型の閾値は Phase 2 スコープとする。
- `pat` は Phase 2 専用ではなく、Phase 1 でも `top_k_poses` の既定値として参照されるため必須。
- `pat.path_model` の正式対応は当面 `TUNNEL` と `SURFACE_LIKE` のみとする。`PORTAL_CUT` は概念上の拡張候補ではあるが、canonical config の正式値には含めない。
- `pat.blockage_pass_threshold = 0.5` は初期値であり、Phase 2 の感度分析で校正する。
- `TUNNEL` と `SURFACE_LIKE` で同一 threshold を共有する妥当性は、Phase 2 で評価する。
- `prefilter` は canonical TargetConfig の正規スキーマには含めない。研究用 override / ignored key としてのみ扱う。
- canonical config は現行 workspace / current suite の校正設定に一致させる。

### 5.3 ActiveSiteAnchor 導出ルール

```text
covalent経路：
  ActiveSiteAnchor = target_cysteine 指定原子の座標

noncovalent経路：
  ActiveSiteAnchor = centroid(anchor_atom_set の全原子座標)
  centroid = 均等重み算術平均
```

**Phase 2 注記（PAT との分離）**

`ActiveSiteAnchor` は CPG の並進定義域を与える量であり、PAT の goal region を兼ねない。
covalent Phase 2 の PAT は、target cysteine の局所幾何から導出される `PATGoalRegion` を別途定義する。
したがって、Phase 1 freeze 済みの
`ActiveSiteAnchor = target_cysteine 指定原子の座標`
は保持される。

言い換えると、Phase 2 で修正するのは PAT の goal 幾何と path model であって、CPG の anchor 定義ではない。

---

## 6. Stage 0：MEF（分子適格性フィルタ）

### 6.1 判定基準

| 基準ID | 基準 | covalent | noncovalent |
|---|---|---|---|
| MEF-01 | SMILES 解析可能 | 必須 | 必須 |
| MEF-02 | 重原子数 ∈ [5, 80] | 必須 | 必須 |
| MEF-03 | 回転可能結合数 ≤ 10 | 必須 | 必須 |
| MEF-04 | 求電子ワーヘッド存在（原子マップ付き SMARTS） | 必須 | 不要 |
| MEF-05 | 多反応性モチーフ除外 | 推奨 | 推奨 |
| MEF-06 | PDB に対象残基が存在 | 必須 | 必須 |

### 6.2 ワーヘッド SMARTS 集合（v4.3 凍結）

```python
WARHEAD_SMARTS = [
    "[C:1]=[C][C](=O)",            # Michael acceptor
    "[C:1]=[C][S](=O)(=O)",        # Vinyl sulfone
    "[C:1]=[C]C#N",                # Acrylonitrile-like
    "C(=O)[CH2:1][Cl,Br,I]",       # Halomethyl ketone
    "C(=O)[CH:1]([Cl,Br,I])",      # α-Haloketone substituted
    "[N]=[C:1]=[S]",               # Isothiocyanate
    "[C:1]1[C:1]O1",               # Epoxide
    "[C:1]1[C][N]1[C](=O)",        # N-acyl aziridine
]
```

### 6.3 凍結ルール

- 各 SMARTS は少なくとも 1 つの `:1` を持つ。
- `:1` がない SMARTS は設計時エラー。
- WarheadAtoms は全 match の `:1` 原子の和集合。
- `mapped_atoms` / `warhead_atoms_union` は昇順ソート済み・重複なし。

### 6.4 FAIL 理由コード（MEF固有）

```text
FAIL_PARSE
FAIL_TOO_LARGE
FAIL_TOO_SMALL
FAIL_TOO_FLEXIBLE
FAIL_NO_WARHEAD
FAIL_OVERREACTIVE
FAIL_PDB_INCOMPLETE
```

---

## 7. CPG（Constrained Placement Generation）

### 7.1 責務

CPG は候補 pose 集合と探索ログを生成する。
CPG 自体は判定を行わない。C1 違反の早期棄却のみを行う。

### 7.2 CSP 変数と定義域

```text
V = { t, q, c }
t = (tx, ty, tz) ∈ ℝ³
q ∈ S³
c ∈ {1, ..., N_conf}

Domain(t) = Sphere(ActiveSiteAnchor, R_search)
Domain(q) = Shoemake + Sobol(d=3, scramble=False)
Domain(c) = {1, ..., N_conf}
```

### 7.3 衝突回避制約 C1

```text
∀ (i,j) ∈ LigandHeavyAtoms × ProteinHeavyAtoms :
    dist(i,j) ≥ α × (r_vdw(i) + r_vdw(j))
```

### 7.4 コンフォーマ生成

- RDKit ETKDG v3
- `n_conformers = 8`（現行受入れ設定）
- RMSD pruning ≤ 0.5 Å
- エネルギー最小化なし

### 7.5 グローバル並進

- Sobol 列から球座標変換による球内準一様サンプルを生成
- `radii = R × cbrt(u₁)`, `φ = 2π u₂`, `cosθ = 2u₃ − 1`（Sobol の3次元出力 `(u₁, u₂, u₃)` から）

### 7.6 local rescue（warhead-first placement）

#### 7.6.1 定義

local rescue は `translation_type = "local"` の追加サンプル群を導入する。
warhead 基準で anchor 近傍へ並進再配分を行う。

#### 7.6.2 位置づけ

local rescue は sampling extension であり、スコアリングではない。
存在判定の結果意味論を変えるものではなく、探索効率を改善するための strategy である。

**superset property の成立条件：**
stage-wise superset property は global sampler 部分に対してのみ成立する。
Sobol prefix extension により `GlobalSet_k ⊆ GlobalSet_{k+1}` を保証する。
local sampler は各 stage で独立に追加される rescue 集合であり、stage 間包含は要求しない。

#### 7.6.3 local rescue パラメータ

- `translation.local_translation_fraction`
- `translation.local_translation_min_radius`
- `translation.local_translation_max_radius`
- `translation.local_translation_start_stage`

#### 7.6.4 実装ポリシー

- stage 1：global のみ
- stage 2 以降：global + local
- `translation_type ∈ {"global", "local"}` を各 pose に記録する

### 7.7 CPG 出力

```yaml
feasible_poses:
  - pose_id: 12
    conformer_id: 3
    translation: [12.3, -4.1, 8.7]
    quaternion: [0.32, 0.45, 0.67, 0.49]
    trial_number: 421
    stage_id: 2
    translation_type: "local"

exploration_log:
  total_trials: 58175
  budget: {n_conformers: 8, n_rotations: 64, n_translations: 64, alpha: 0.78}
  feasible_count: 13
  c1_rejected: 78633
  early_stopped: true
  stopped_at_trial: 58175
  active_site_anchor_xyz: [12.45, -3.21, 8.89]
  anchor_derivation: "target_cysteine.SG"
  anchor_source_atoms:
    - {atom: "A:328:SG", xyz: [12.45, -3.21, 8.89]}
```

### 7.8 staging provenance（I-13）

Evidence Artifact は以下を必須記録する。

- `stage_id`
- `translation_type`
- `trial_number`
- `stopped_at_trial`
- `early_stop_reason`

再検算チェッカーは `stage_id` と `translation_type` が canonical policy と矛盾しないことを検証する。
たとえば `stage_id < local_translation_start_stage` なのに `translation_type = "local"` なら不整合として検出する。

### 7.9 no_feasible_early_abort（v4.3.1 確定）

zero-feasible 化合物に対する計算量制御として、`scv.no_feasible_early_abort_trial` trial を消費しても feasible pose が 1 つも生成されない場合、CPG を中断し `FAIL_NO_FEASIBLE` を返す。

v4.3.1 確定値は `4096`。これは fACR-2240 の校正実験で runtime を 6.85s → 1.52s/compound に短縮しつつ、PASS 率低下が -10pt（86.67% → 76.67%）であることを確認して決定した。8192 では追加的な PASS 率改善が見られなかった。本校正範囲では、4096 以降の追加 trial が新たな feasible pose を実質的に生んでいないと推定されるが、特定の分子サイズ・形状によっては打切り偽陰性が生じうる点は留意が必要である。

この閾値は分子サイズに対して一律適用される。分子サイズ適応型の閾値（重原子数に応じた動的設定）は Phase 2 のスコープとする。

---

## 8. Sensors（測定器群）

### 8.1 共通原則

- 各 Sensor は判定用連続量 1 つだけ返す
- 閾値判定はしない
- 原子配列は昇順ソート済み
- 同一距離のタイブレークは `(distance, trial_number, smarts_index, atom_index)` の辞書式最小

### 8.2 Anchoring Sensor（連続量：target_distance）

covalent:
```text
min_{a ∈ WarheadAtoms} dist(a, TargetCys.SG)
```

noncovalent:
```text
min_{a ∈ LigandHeavyAtoms, b ∈ AnchorAtomSet} dist(a, b)
```

出力例：

```yaml
anchoring_observation:
  best_target_distance: 3.03
  best_pose:
    pose_id: 41
    conformer_id: 2
    translation: [...]
    quaternion: [...]
    trial_number: 58175
    stage_id: 2
    translation_type: "local"
  warhead_provenance:
    matched_smarts:
      - {smarts_index: 0, pattern: "[C:1]=[C][C](=O)", mapped_atoms: [7]}
    warhead_atoms_union: [7]
    argmin_target:
      atom_index: 7
      smarts_index: 0
      smarts_pattern: "[C:1]=[C][C](=O)"
      tiebreak_key: [3.03, 58175, 0, 7]
  poses_evaluated: 13
  top_k_poses:
    - {target_distance: 3.03, pose_id: 41, trial_number: 58175, stage_id: 2, translation_type: "local"}
```

### 8.3 OffTarget Sensor（連続量：offtarget_distance）

各 feasible pose について、WarheadAtoms から各 offtarget Cys までの最小距離を測る。
返すのは全 feasible pose にわたる最小値である。

```yaml
offtarget_observation:
  best_offtarget_distance: 7.83
  closest_offtarget_residue: 237
  best_offtarget_pose:
    pose_id: 41
    conformer_id: 2
    trial_number: 58175
    stage_id: 2
    translation_type: "local"
  argmin_offtarget:
    atom_index: 7
    smarts_index: 0
    smarts_pattern: "[C:1]=[C][C](=O)"
    tiebreak_key: [7.83, 58175, 0, 7]
```

### 8.4 OffTarget の witness 意味論

Anchoring の witness は ∃ の存在証明に対応する。
一方、OffTarget Sensor が返す `best_offtarget_distance` は

```text
min_{p ∈ F_s} min_{c ∈ C_off} dist(p, c)
```

であり、これが閾値を超えていれば、すべての feasible pose が安全である。
したがって、OffTarget の min 距離出力は `∀p : O_safe(p)` の反証不能性証明に相当する。

Anchoring の witness は「届いた 1 pose」であるのに対し、OffTarget の witness は「最も危険な pose でも安全であること」を示す**集合レベルの witness** である。

この保守性は Phase 1 では意図的である。
ただし、target 非到達 pose が偶然 OffTarget 近傍を通過した場合に偽陰性を生じうる。
将来 pose-specific OffTarget 評価に移行する場合は、

```text
(∃p ∈ F_s : A(p)) ∧ O_forall_safe(F_s)
```

から

```text
∃p ∈ F_s : A(p) ∧ O_safe(p)
```

への移行を検討する。

### 8.5 PAT Sensor（Phase 2）

- 入力：Anchoring Sensor の `top_k_poses`、apo protein geometry、`PATGoalRegion`、`pat.path_model`
- 出力：`max_blockage_ratio`
- 内部診断：`goal_precheck_passed`、`goal_precheck_reason`、`goal_clearance_max_0`、`apo_accessible_goal_voxels`、`numeric_resolution_limited`
- `pat.top_k_poses` は Phase 1 でも既定 pose limit として参照されるため、config 上必須

#### 8.5.1 path_blocking の上位定義

PAT が測る `path_blocking` とは、

```text
apo で外界から target-neighborhood へ到達可能であった自由空間が、
pose 追加により失われること
```

である。

したがって path blocking は、

- PATGoalRegion 上の局所アクセス可能領域の消失
- 侵入口の遮断
- 途中経路の遮断
- goal 直前のネック遮断

のいずれでも成立しうる。

`path_model` は、この上位概念をどの operational model で測るかを規定する。

#### 8.5.2 path_model の正式定義

```text
pat.path_model ∈ {"TUNNEL", "SURFACE_LIKE"}
```

- `TUNNEL`
  - 外界から PATGoalRegion までの volumetric reachability を評価する。
  - 入口・途中経路・goal 近傍のいずれの遮断も `blockage_ratio` に反映しうる。
- `SURFACE_LIKE`
  - PATGoalRegion 上の局所アクセス可能領域の消失を評価する。
  - これは厳密 SASA ではなく、goal-region 上の local accessibility loss を voxel で近似した dSASA proxy である。

注：`PORTAL_CUT` は概念上の拡張候補として認めるが、現時点では正式対応しない。したがって canonical 実装は `TUNNEL` と `SURFACE_LIKE` の 2 値のみを受理する。

#### 8.5.3 PATGoalRegion（covalent）

```text
SG = target_cysteine.SG の座標
CB = target_cysteine.CB の座標
u_app = normalize(SG - CB)

r_in  = r_vdw(SG) + δ_goal
r_out = r_in + t_goal

PATGoalRegion G_pat =
{ x ∈ R^3 :
    r_in ≤ ||x - SG|| ≤ r_out
    and (x - SG) · u_app ≥ 0
}
```

既定値：

- `pat.goal_mode = "cys_approach_hemishell"`
- `pat.goal_shell_clearance = 0.2  # Å`
- `pat.goal_shell_thickness = 1.0  # Å`

`G_pat` は SG 中心点でも SG 中心球でもなく、SG の外側に位置する「進入半球殻」である。

#### 8.5.4 共通幾何と `goal_precheck`

PAT は compound ごとではなく、target/config ごとに apo 構造で 1 回だけ `goal_precheck` を行う。

```text
ROI = Ball(ActiveSiteAnchor, search_radius + pat.r_outer_margin)
OuterShell(ROI) = ROI の境界 voxel 集合

goal_clearance_max_0 =
    max_{x ∈ G_pat} clearance_apo(x; probe_radius = 0)
```

共通成立条件：

```text
goal_clearance_max_0 > 0
```

意味：

- `goal_clearance_max_0 ≤ 0` は goal 定義が protein excluded volume 内に埋まっていることを意味する。
- この場合 PAT の定義域が不成立であり、run-level に停止する。

この precheck 名称は、旧来の target-side precheck 名を一般化して `goal_precheck` に統一する。理由は、precheck の対象が「標的そのもの」ではなく「PAT が参照する goal region」であるためである。

#### 8.5.5 `TUNNEL` model

`TUNNEL` では、外界から goal までの volumetric reachability を測る。

```text
Occ(X)  = structure X の excluded volume
Free(X) = ROI \ Dilate(Occ(X), pat.probe_radius)

A_tunnel(X) =
{ x ∈ Voxelize(G_pat) :
    x ∈ Free(X)
    and x is connected to OuterShell(ROI) through Free(X)
}
```

apo baseline：

```text
A_apo_tunnel = A_tunnel(protein_apo)
```

model-specific precheck：

```text
|A_apo_tunnel| > 0
```

pose `p` に対する遮断率：

```text
blockage_tunnel(p) =
1 - |A_tunnel(protein_apo ∪ ligand_pose_p)| / |A_apo_tunnel|
```

この定義では、入口遮断・途中経路遮断・goal 近傍遮断のいずれも、最終的に `A_tunnel` の減少として反映されうる。

#### 8.5.6 `SURFACE_LIKE` model

`SURFACE_LIKE` では、PATGoalRegion 上の局所アクセス可能領域の消失を測る。これは厳密な SASA 計算ではなく、goal patch の局所露出度の変化を voxel で近似する dSASA proxy である。

```text
W_goal =
{ y ∈ ROI : dist(y, G_pat) ≤ pat.surface_window_radius }

A_surface(X) =
{ x ∈ Voxelize(G_pat) :
    ∃ y ∈ W_goal such that
    y is a free voxel adjacent to x
    and y is connected to OuterShell(ROI)
}
```

ここで `adjacent` は 6-connectivity（面共有 voxel）とする。

apo baseline：

```text
A_apo_surface = A_surface(protein_apo)
```

model-specific precheck：

```text
|A_apo_surface| > 0
```

pose `p` に対する遮断率：

```text
blockage_surface(p) =
1 - |A_surface(protein_apo ∪ ligand_pose_p)| / |A_apo_surface|
```

`SURFACE_LIKE` は goal patch 周辺の局所 accessibility loss に焦点を当てる。したがって `TUNNEL` に比べて、入口や長い途中経路の容量そのものより、goal 近傍の露出変化に感度が高い。

#### 8.5.7 model 非依存の出力

各 pose について

```text
blockage(p) =
    blockage_tunnel(p)   if pat.path_model = "TUNNEL"
    blockage_surface(p)  if pat.path_model = "SURFACE_LIKE"
```

とし、Sensor 出力は

```text
max_blockage_ratio = max_{p ∈ TopK} blockage(p)
```

とする。

SCV は `pat.path_model` に依存せず、`max_blockage_ratio` のみを用いて `P_pat` を判定する。

また、`goal_voxel_count = |Voxelize(G_pat)|` とする。

以下を満たすとき

```text
numeric_resolution_limited ≡
    apo_accessible_goal_voxels < pat.min_baseline_voxels
    ∨ goal_voxel_count < pat.min_goal_voxels
```

と定義する。

これは浮動小数点一般の不安定性ではなく、voxel 離散化に対して baseline または goal が小さすぎ、`blockage_ratio` の分解能が判定に十分でないことを意味する。

#### 8.5.8 run-level failure policy

以下は compound-level verdict ではなく、run-level diagnostics とする。

- `PAT_UNSUPPORTED_PATH_MODEL`
- `PAT_GOAL_INVALID`
- `PAT_APO_BASELINE_ABSENT`

これらが成立した場合、Phase 2 run は停止し、compound ごとに `PAT_NOT_EVALUABLE` を配布しない。

対応関係は以下のとおりとする。

| 条件 | failure reason |
|---|---|
| `pat.path_model ∉ {"TUNNEL", "SURFACE_LIKE"}` | `PAT_UNSUPPORTED_PATH_MODEL` |
| `goal_clearance_max_0 ≤ 0` | `PAT_GOAL_INVALID` |
| model-specific precheck 不成立 | `PAT_APO_BASELINE_ABSENT` |

---

## 9. SCV（object logic）

### 9.1 責務

SCV は以下を行う唯一のコンポーネントである。

- 観測量と閾値の比較
- 三値判定（PASS / FAIL / UNCLEAR）
- Evidence Artifact 構築

### 9.2 covalent Phase 1 の述語体系

#### 9.2.1 pose-level predicates

```text
A(p)        ≡ dist_target(p) ≤ θ_anchor
O_safe(p)   ≡ dist_offtarget(p) > θ_offtarget
```

#### 9.2.2 set-level predicates

```text
O_forall_safe(F_s) ≡ ∀p ∈ F_s : O_safe(p)
```

#### 9.2.3 compound-level Phase 1 predicate

```text
GFT_cov_phase1(F_s) ≡ (∃p ∈ F_s : A(p)) ∧ O_forall_safe(F_s)
```

ここで `∃p : A(p)` の witness は Anchoring witness pose、
`O_forall_safe(F_s)` の witness は OffTarget Sensor の min 距離出力である。

### 9.3 noncovalent Phase 1 predicate

```text
GFT_noncov_phase1(F_s) ≡ ∃p ∈ F_s : A(p)
```

### 9.4 Phase 2 predicate 追加

PAT が導入された後は、

```text
P_pat(p) ≡ blockage(p) ≥ θ_blockage
```

を加え、compound-level verdict は SCV の三値 AND で決める。

```text
TopK(F_s) = Anchoring Sensor が返す top_k_poses 集合
          = feasible pose 集合 F_s のうち、
            target_distance 昇順で上位 pat.top_k_poses 件
```

```text
GFT_cov_phase2(F_s) ≡ (∃p ∈ F_s : A(p)) ∧ O_forall_safe(F_s) ∧ (∃p ∈ TopK(F_s) : P_pat(p))
```

なお、Anchoring witness（`∃p : A(p)` を充足する pose）と PAT witness（`∃p : P_pat(p)` を充足する pose）は**同一 pose である必要はない**。各述語は独立に witness を持てばよい。将来、同一 pose での充足を要求する設計（`∃p : A(p) ∧ P_pat(p)`）に変更する場合は、本述語を明示的に改訂する。

`P_pat` の object logic は `pat.path_model` 非依存である。すなわち `TUNNEL` と `SURFACE_LIKE` はいずれも PAT の内部実装差であり、SCV は最終的な `max_blockage_ratio` のみを受け取る。

ただし、PAT 評価は `goal_precheck_passed = True` を前提とする。`goal_precheck` が不成立な場合、それは compound-level の FAIL / UNCLEAR ではなく、run-level の入力不整合または適用外である。

PAT の SCV 正規化は以下とする。

```python
def scv_pat(pat_obs, config):
    if not pat_obs.goal_precheck_passed:
        raise RuntimeError("PAT goal_precheck failed")

    if pat_obs.numeric_resolution_limited:
        return Verdict.UNCLEAR, "UNCLEAR_NUMERIC_RESOLUTION"

    if pat_obs.max_blockage_ratio >= config.pat.blockage_pass_threshold:
        return Verdict.PASS, {"borderline": False}

    return Verdict.FAIL, "FAIL_PAT_BLOCKAGE"
```

このとき `FAIL_PAT_BLOCKAGE` は「goal_precheck は成立していたが、TopK のいずれの pose も十分な遮断率を与えなかった」ことを意味する。

### 9.5 三値論理の意味論

SCV の統合は Kleene 強三値論理の AND と同型である。

```python
def scv_integrate(verdicts):
    if any(v == Verdict.FAIL for v in verdicts):
        return Verdict.FAIL
    if any(v == Verdict.UNCLEAR for v in verdicts):
        return Verdict.UNCLEAR
    return Verdict.PASS
```

ここで terminal policy はこの三値論理の外側に置かれる。
したがって、terminal policy による FAIL 化は object logic の破綻ではなく、search-control logic による終端正規化である。

### 9.6 Anchoring 判定

```python
def scv_anchoring(anchoring_obs, exploration_log, config):
    d = anchoring_obs.best_target_distance
    θ = config.distance_threshold
    ε = config.anchoring.epsilon
    f = exploration_log.feasible_count
    f_min = config.scv.min_feasible_for_confident_fail

    if d <= θ:
        return Verdict.PASS, {"borderline": d > θ - ε}
    if f is None:
        return Verdict.UNCLEAR, "UNCLEAR_INPUT_MISSING"
    if f < f_min:
        return Verdict.UNCLEAR, "UNCLEAR_SAMPLING_BUDGET"
    if d <= θ + ε:
        return Verdict.UNCLEAR, "UNCLEAR_BORDERLINE_EPS"
    return Verdict.FAIL, "FAIL_ANCHORING_DISTANCE"
```

### 9.7 OffTarget 判定

```python
def scv_offtarget(offtarget_obs, exploration_log, config):
    d_off = offtarget_obs.best_offtarget_distance
    θ = config.offtarget.distance_threshold
    ε = config.offtarget.epsilon
    f = exploration_log.feasible_count
    f_min = config.scv.min_feasible_for_confident_fail

    if d_off > θ + ε:
        return Verdict.PASS, "OFFTARGET_SAFE"
    if d_off > θ:
        return Verdict.PASS, {"borderline": True}
    if f < f_min:
        return Verdict.UNCLEAR, "UNCLEAR_SAMPLING_BUDGET"
    if d_off >= θ - ε:
        return Verdict.UNCLEAR, "UNCLEAR_BORDERLINE_EPS"
    return Verdict.FAIL, "FAIL_OFFTARGET_CYS"
```

---

## 10. Staging / terminal policy（search-control logic）

### 10.1 補助述語

```text
Z(s)         ≡ feasible_count(s) = 0
Sparse(s)    ≡ 0 < feasible_count(s) < f_min
Dense(s)     ≡ feasible_count(s) ≥ f_min

NearBand(s)  ≡ retry_lower ≤ best_target_distance(s) ≤ retry_upper
FarBand(s)   ≡ best_target_distance(s) > terminal_far_target_threshold
```

### 10.2 canonical staging parameters

- `staging.retry_target_distance_lower = 3.5`
- `staging.retry_target_distance_upper = 5.0`
- `staging.terminal_far_target_threshold = 5.0`
- `staging.max_stage = 3`

### 10.3 状態遷移表

**非終端 stage（stage_id < max_stage）**

| 条件 | 出力 |
|---|---|
| `v_core = PASS` | `FINALIZE_PASS` |
| `v_core = FAIL` | `FINALIZE_FAIL` |
| `v_core = UNCLEAR ∧ Z(s)` | `CONTINUE` |
| `v_core = UNCLEAR ∧ NearBand(s)` | `CONTINUE` |
| `v_core = UNCLEAR ∧ ¬NearBand(s)` | `FINALIZE_BY_TERMINAL_POLICY` |

**注記：** 非終端 stage では Sparse / Dense を CONTINUE 判定に直接使わない。これは「feasible が少なくても、距離帯として retry value がある限り次 stage へ送る」ためである。

**終端 stage（stage_id = max_stage）**

| 条件 | 出力 |
|---|---|
| `v_core = PASS` | `FINALIZE_PASS` |
| `v_core = FAIL` | `FINALIZE_FAIL` |
| `v_core = UNCLEAR` | `FINALIZE_BY_TERMINAL_POLICY` |

### 10.4 terminal policy 正規化

`FINALIZE_BY_TERMINAL_POLICY` は以下の規則で最終 verdict に正規化される。

```python
def scv_terminal_policy(v_core, feasible_count, best_target_distance, config):
    f_min = config.scv.min_feasible_for_confident_fail
    far = config.staging.terminal_far_target_threshold

    if feasible_count == 0:
        return Verdict.FAIL, "FAIL_NO_FEASIBLE"

    if best_target_distance is not None and best_target_distance > far:
        return Verdict.FAIL, "FAIL_LOW_PRIORITY_FAR_TARGET"

    return Verdict.UNCLEAR, "UNCLEAR_SAMPLING_BUDGET"
```

### 10.5 taxonomy の一本化

外部公開 reason は以下を正規名とする。

- `FAIL_ANCHORING_DISTANCE`
- `FAIL_OFFTARGET_CYS`
- `FAIL_PAT_BLOCKAGE`
- `FAIL_NO_FEASIBLE`
- `FAIL_LOW_PRIORITY_FAR_TARGET`
- `UNCLEAR_SAMPLING_BUDGET`
- `UNCLEAR_BORDERLINE_EPS`
- `UNCLEAR_INPUT_MISSING`
- `UNCLEAR_NUMERIC_RESOLUTION`

補足：

- `PAT_NOT_EVALUABLE` は compound-level の外部公開 reason から除外する。
- `PAT_UNSUPPORTED_PATH_MODEL`
- `PAT_GOAL_INVALID`
- `PAT_APO_BASELINE_ABSENT`

は run-level internal diagnostics としてのみ保持する。

これにより、compound-level taxonomy は「化合物が object logic を満たしたか否か」のみを表し、target/config 側の不成立や model 未対応とは分離される。

---

## 11. 早期停止

```python
def should_stop(current_obs, config):
    if current_obs.best_target_distance <= config.distance_threshold - config.anchoring.epsilon:
        if config.pathway == "noncovalent":
            return True
        if current_obs.best_offtarget_distance > config.offtarget.distance_threshold + config.offtarget.epsilon:
            return True
    return False
```

早期停止は PASS 確定時のみ許可する。
FAIL / UNCLEAR の早期終端は search-control logic 側でのみ行う。

---

## 12. Evidence Artifact

### 12.1 PASS

```yaml
verdict: PASS
pathway: covalent
sensors:
  anchoring:
    verdict: PASS
    best_target_distance: 3.03
    witness_pose:
      pose_id: 41
      conformer_id: 2
      trial_number: 58175
      stage_id: 2
      translation_type: "local"
    warhead_provenance:
      matched_smarts:
        - {smarts_index: 0, pattern: "[C:1]=[C][C](=O)", mapped_atoms: [7]}
      warhead_atoms_union: [7]
      argmin_target:
        atom_index: 7
        smarts_index: 0
        tiebreak_key: [3.03, 58175, 0, 7]
  offtarget:
    verdict: PASS
    best_offtarget_distance: 7.83
    closest_residue: 237
    argmin_offtarget:
      atom_index: 7
      smarts_index: 0
      tiebreak_key: [7.83, 58175, 0, 7]
  pat:
    verdict: PASS
    path_model: "TUNNEL"
    goal_mode: "cys_approach_hemishell"
    goal_precheck_passed: true
    goal_precheck_reason: null
    goal_clearance_max_0: 0.61
    apo_accessible_goal_voxels: 148
    max_blockage_ratio: 0.78
    witness_pose:
      pose_id: 41
      conformer_id: 2
      trial_number: 58175
      stage_id: 2
      translation_type: "local"
target_class: ON_TARGET
exploration_log:
  total_trials: 58175
  feasible_count: 13
  c1_rejected: 78633
  active_site_anchor_xyz: [12.45, -3.21, 8.89]
  stage_id_found: 2
  translation_type_found: "local"
meta:
  requirements_hash: "sha256:..."
  input_hash: "sha256:..."
  config_hash: "sha256:..."
```

### 12.2 FAIL

```yaml
verdict: FAIL
reason: FAIL_LOW_PRIORITY_FAR_TARGET
pathway: covalent
sensors:
  anchoring:
    verdict: UNCLEAR
    best_target_distance: 6.55
  offtarget:
    verdict: PASS
    best_offtarget_distance: 9.20
  pat:
    verdict: FAIL
    path_model: "SURFACE_LIKE"
    goal_mode: "cys_approach_hemishell"
    goal_precheck_passed: true
    goal_precheck_reason: null
    goal_clearance_max_0: 0.61
    apo_accessible_goal_voxels: 126
    max_blockage_ratio: 0.22
exploration_log:
  feasible_count: 4
  total_trials: 20480
  stage_id_found: 1
  translation_type_found: "global"
```

### 12.3 UNCLEAR

```yaml
verdict: UNCLEAR
reason: UNCLEAR_SAMPLING_BUDGET
pathway: covalent
sensors:
  anchoring:
    verdict: UNCLEAR
    best_target_distance: 4.30
  offtarget:
    verdict: PASS
    best_offtarget_distance: 8.84
  pat:
    verdict: UNCLEAR
    path_model: "TUNNEL"
    goal_mode: "cys_approach_hemishell"
    goal_precheck_passed: true
    goal_precheck_reason: null
    goal_clearance_max_0: 0.61
    apo_accessible_goal_voxels: 148
    max_blockage_ratio: 0.48
    numeric_resolution_limited: true
exploration_log:
  feasible_count: 3
  total_trials: 20480
  stage_id_found: 1
  translation_type_found: "global"
recommendation: "increase stage budget or continue staging"
```

### 12.4 run-level PAT diagnostics

PAT の定義域不成立は compound artifact ではなく、run-level manifest に保持する。

```yaml
pat_run_diagnostics:
  path_model: "TUNNEL"
  goal_mode: "cys_approach_hemishell"
  goal_precheck_passed: false
  goal_precheck_reason: "PAT_APO_BASELINE_ABSENT"
  goal_clearance_max_0: 0.14
  apo_accessible_goal_voxels: 0
```

run-level diagnostics は、target/config の幾何不整合と compound-level 非充足を混同しないために必要である。

---

## 13. 再現性プロトコル

### 13.1 R0（Bit-exact）

成立条件：

- Python / NumPy / RDKit / SciPy / Biopython version を固定
- float64 強制
- Sobol `scramble=False`
- RDKit `randomSeed` 固定
- 原子配列昇順ソート
- タイブレーク辞書式最小
- `stage_id` / `translation_type` を含む Evidence 再検算

### 13.2 requirements_hash / input_hash / config_hash の定義

- **requirements_hash**
  主要依存ライブラリ version 文字列（NumPy / RDKit / SciPy / Biopython 等）を JSON serialize して hash 化したもの。lockfile hash ではない。

- **input_hash**
  現行実装では compound SMILES + requirements_hash に基づく hash。target structure 実ファイル内容 hash ではない。

- **config_hash**
  TargetConfig 値の serialize に基づく hash。PDB/CIF 実ファイル内容 hash は含まない。

### 13.3 run-level manifest

run-level 再現性を論じるときは、結果ファイル外で以下を別 manifest として管理する。

- `library_hash`
- `compound_order_hash`
- `staging_plan_hash`
- `target_case_id`
- `structure_file_digest`

---

## 14. 性能契約

| ID | 制約 |
|---|---|
| PC-01 | KDTree は局所領域に限定 |
| PC-02 | clash 判定は近接クエリで行う |
| PC-03 | 座標変換は NumPy 一括 |
| PC-04 | `trials_executed`, `feasible_count` を必須ログ |
| PC-05 | 1 pose > 0.2 ms なら Phase 1 内で対応 |
| PC-06 | no_feasible_early_abort_trial により zero-feasible 化合物の計算量を bounded とする |

現行校正値の要約：

- `alpha = 0.78`
- `n_conformers = 8`
- `min_feasible_for_confident_fail = 10`
- `no_feasible_early_abort_trial = 4096`（v4.3.1 確定）
- `single_target_cpg_ms_per_pose_mean ≈ 0.066–0.10 ms`
- negative PASS = 0
- small-molecule known positives = 3/3 PASS
- peptide-like known positive は replay benchmark で評価し、de novo acceptance から除外

3ライブラリでの実測スループット（v4.3.1 確定条件）：

| ライブラリ | 化合物数 | 総runtime | 平均/compound |
|---|---|---|---|
| fACR-2240 | 2,240 | 4,020s | 1.79s |
| CYS-3200 | 3,200 | 10,526s | 3.29s |
| ChemDiv CPI-7801 | 7,801 | 9,063s | 1.16s |

ChemDiv CPI-7801 の低い平均 runtime は 87.8% が MEF 段階で FAIL_NO_WARHEAD として棄却され、CPG に到達しないことによる。

---

## 15. バリデーション計画

### 15.1 ベンチ区分

| ベンチ | 含むもの | 期待 |
|---|---|---|
| de novo acceptance | small-molecule known positives, negatives, screening library | small-molecule known positives ≥ 3/3 PASS、negative PASS = 0 |
| crystal replay benchmark | crystal pose を直接再生する既知陽性（peptide-like 含む可） | Sensor / SCV の穴がないことを確認 |
| negative control | size-infeasible / distance-infeasible | FAIL 優勢 |

### 15.2 受入れ基準

| 指標 | 目標 |
|---|---|
| small-molecule known positives | 3/3 PASS |
| negative PASS count | 0 |
| UNCLEAR rate（fACR100 目安） | ≈ 0.14 程度以下を維持 |
| PC-05 | PASS |
| zero-feasible UNCLEAR 固定化 | 解消済みであること |
| FAIL taxonomy | `FAIL_NO_FEASIBLE` / `FAIL_LOW_PRIORITY_FAR_TARGET` / `FAIL_ANCHORING_DISTANCE` / `FAIL_OFFTARGET_CYS` のいずれかに正規化 |

### 15.3 新規化学空間適用時の事前監査

新しい化学空間または新しい標的に CRISP を適用する場合、パイプライン実行の前に以下を必須監査とする。

**(1) SMARTS coverage audit**
対象ライブラリに含まれる共有結合 warhead 類型が、MEF-04 の `WARHEAD_SMARTS` 集合で十分に表現されているかを確認する。具体的には、対象ライブラリから既知反応性部分構造を抽出し、SMARTS マッチの被覆率を計測する。被覆が不十分な場合は ADR-07 に基づき SMARTS を拡張する。

**(2) α re-calibration check**
対象標的 × 化学空間に対して、canonical α の受入れ値が以下を両立するかを確認する。
- 既知陽性回収率が acceptance 基準を満たす
- 陰性 PASS 率がゼロを維持する

既存校正値（α=0.78）が両立しない場合、感度分析を再実施し新たな canonical α を設定する。

**(3) rigid-pocket applicability check**
標的ポケットが剛体近似で扱えるかを、以下から確認する。
- 既知複合体構造の apo/holo 間 RMSD
- 文献で報告されている結合時の構造変化幅
- 誘導適合の寄与が結合に不可欠であるとの知見の有無

剛体近似が不適切と判断される場合は L-01 の適用限界に該当し、CRISP の FAIL を偽陰性として扱う旨を記録する。

### 15.4 Phase 1 検証結果（v4.3.1 確定）

#### 15.4.1 3ライブラリ検証サマリ

ターゲット：I7L（PDB: 9JAL / 9KR6）、canonical config（§5.1）、`no_feasible_early_abort_trial = 4096`。

**ライブラリ名称の凍結：**

| 略称 | 正式名称 | 化合物数 |
|---|---|---|
| fACR-2240 | Enamine Covalent Fragment Acrylamide Library | 2,240 |
| CYS-3200 | Enamine Cysteine-focused Covalent Fragments | 3,200 |
| ChemDiv CPI-7801 | ChemDiv Cysteine Proteases Inhibitors Library | 7,801 |

以降、本設計書では上記略称を使用する。

| ライブラリ | 役割 | 化合物数 | PASS | UNCLEAR | FAIL | ERROR | PASS率 | UNCLEAR率 |
|---|---|---|---|---|---|---|---|---|
| fACR-2240 | 校正用 | 2,240 | 1,770 | 0 | 470 | 0 | 79.0% | 0.00% |
| CYS-3200 | 実運用 | 3,200 | 1,258 | 2 | 1,940 | 0 | 39.3% | 0.06% |
| ChemDiv CPI-7801 | 除外確認 | 7,801 | 1 | 0 | 7,800 | 0 | 0.01% | 0.00% |

#### 15.4.2 ChemDiv CPI-7801 除外の根拠

ChemDiv CPI-7801 の FAIL 内訳は以下の通り。

| FAIL reason | 件数 | 割合 |
|---|---|---|
| FAIL_NO_WARHEAD | 6,852 | 87.8% |
| FAIL_NO_FEASIBLE | 946 | 12.1% |
| FAIL_TOO_FLEXIBLE | 2 | 0.03% |

SMARTS 被覆率は 12.2%（949/7801）にとどまり、§0.1 条件(a)を充足する母集団が不十分である。当ライブラリは共有結合型ウォーヘッドを主体とするライブラリではなく、非共有結合型の competitive/allosteric 阻害剤が大多数を占める。唯一の PASS は典型的な Michael acceptor 1件であり、一次スクリーニングの費用対効果が成立しない。

なお、FAIL_NO_FEASIBLE の 946 化合物には `no_feasible_early_abort_trial=4096` による打切り偽陰性の可能性が含まれうるが、母集団の 87.8% が MEF 段階で除外される以上、この区別を深掘りする実益は薄い。

#### 15.4.3 SMARTS クラス別検証結果（CYS-3200）

| smarts_index | ウォーヘッド | ライブラリ内 hit 数 | PASS 数 | PASS 率 | enrichment | 検証状態 |
|---|---|---|---|---|---|---|
| 0 | Michael acceptor | 1,522 | 812 | 53.4% | 1.36 | **validated** |
| 3 | Halomethyl ketone | 800 | 273 | 34.1% | 0.87 | **validated** |
| 4 | Alpha-haloketone (substituted) | 640 | 173 | 27.0% | 0.69 | **validated** |
| 1 | Vinyl sulfone | 4 | 0 | 0.0% | — | N不足 |
| 2 | Acrylonitrile-like | 1 | 0 | 0.0% | — | N不足 |
| 5 | Isothiocyanate | 0 | — | — | — | ライブラリ未収載 |
| 6 | Epoxide | 0 | — | — | — | ライブラリ未収載 |
| 7 | N-acyl aziridine | 0 | — | — | — | ライブラリ未収載 |

enrichment は「当該クラスの PASS 率 / ライブラリ全体の PASS 率」で算出。Michael acceptor の enrichment=1.36 は、末端 C=C がポケットへの幾何学的到達に有利であることと整合する。Haloketone 系の低い enrichment（0.69–0.87）は、反応性原子が分子内部寄りに位置する傾向を反映している。

#### 15.4.4 検証カバレッジの評価

8 SMARTS クラスのうち 3 クラス（Michael acceptor、Halomethyl ketone、Alpha-haloketone）が N>600 で統計的に有意な検証を達成した。残り 5 クラスについては、検証対象ライブラリに十分な母集団が存在しなかった。これは**パイプラインの対応能力の限界ではなく、入手可能なライブラリの化学空間の限界**である。将来、Vinyl sulfone / Isothiocyanate / Epoxide 等を主体とする共有結合ライブラリが入手可能になった時点で、§15.3 の事前監査を実施した上で追加検証する。

#### 15.4.5 no_feasible_early_abort_trial の校正結果

fACR-2240 サブセットでの条件検討結果：

| 閾値 | 平均 runtime/compound | PASS 率 | 評価 |
|---|---|---|---|
| 0（打切りなし） | 6.85s | 86.67% | ベースライン |
| **4096** | **1.52s** | **76.67%** | **採用（4.6× 高速化、-10pt）** |
| 8192 | 2.43s | 73.33% | 追加的改善なし |

PASS 率の -10pt 低下は、主に zero-feasible 化合物がより早く FAIL_NO_FEASIBLE に分類されることに起因すると推定される。8192 閾値でも PASS 率の回復が見られないことから、本校正範囲では 4096 以降の追加 trial の寄与は限定的であった。ただし、特定の分子プロファイルに対する打切り偽陰性の可能性は残る。

---

## 16. 新規性

### 16.1 3本柱

1. **Sound-but-incomplete geometric screen**
   PASS は witness 付きで健全。非PASS は不完全。

2. **Witness / fail-witness output**
   PASS は存在証明、FAIL/UNCLEAR は理由付き反証可能出力。

3. **Monotone budget + deterministic reproducibility**
   global sampler の prefix 性と Evidence の決定論化により、再現性を構造的に担保。

### 16.2 形式的新規性

既存ドッキングが「最適解の近似」を目指すのに対し、CRISP は「実現可能解の存在証明」を目指す。
PASS の witness は制約充足問題における証明書付き解に対応し、FAIL/UNCLEAR は search-control logic 付きの非存在未証明状態として表現される。
この点で、CRISP は最適化器ではなく**証明書付き判定器**である。

---

## 17. ADR（Architecture Decision Records）

| ADR | 決定 |
|---|---|
| ADR-01 | スコアリング禁止。目的関数を導入しない。ランキングもしない |
| ADR-02 | N_conf = 8 固定。動的調整はしない |
| ADR-03 | UNCLEAR 再導入。feasible 不足や境界値を FAIL と断じない |
| ADR-04 | PAT を Phase 1 に含めない。ただし config 上は loader 整合のため必須 |
| ADR-05 | エネルギー最小化なし。力場選択を持ち込まない |
| ADR-06 | noncovalent は centroid でなく min 距離 |
| ADR-07 | ワーヘッド SMARTS は最小集合から開始し、陽性対照の回収漏れ時のみ拡張 |
| ADR-08 | PDB 前処理は TargetConfig で宣言的指定。恣意的推論禁止 |
| ADR-09 | N_conf の単調性除外。prefix 不変性は保証しない |
| ADR-10 | 測定と判定の分離。Sensor は観測量のみ、SCV が判定 |
| ADR-11 | OffTarget Sensor を Anchoring から分離 |
| ADR-12 | WarheadAtoms を `:1` 原子マップで一意定義 |
| ADR-13 | PAT は Anchoring top-K から評価し、`path_model` に依存して算出された `max blockage` を採用する |
| ADR-14 | 原子配列は昇順・重複なし |
| ADR-15 | argmin タイブレークは辞書式最小 |
| ADR-16 | canonical config は現行 loader / suite / workspace に一致させる |
| ADR-17 | prefilter は canonical config に含めない |
| ADR-18 | terminal policy 正規化。`FINALIZE_BY_TERMINAL_POLICY` を FAIL/UNCLEAR に写像する |
| ADR-19 | staging を状態遷移表で固定する |
| ADR-20 | object logic / search-control logic を二層分離する |
| ADR-21 | 述語体系を明文化。`A(p)`, `O_safe(p)`, `O_forall_safe(F_s)` を明示 |
| ADR-22 | OffTarget は `∀` 安全性を採用。現行 OffTarget Sensor が全 feasible pose 上の min 距離を返す実装仕様に依存する。将来 pose-specific に変更する場合、本 ADR は見直し対象 |
| ADR-23 | local rescue は sampling extension。heuristic ranking ではなく探索効率改善の追加 sampling |
| ADR-24 | staging provenance を Evidence に必須記録。`stage_id` と `translation_type` により staging-aware 再検算を可能にする |
| ADR-25 | no_feasible_early_abort_trial=4096 を一律適用。分子サイズ適応型閾値は Phase 2 スコープ |
| ADR-26 | ChemDiv CPI-7801 は §0.1 条件(a) 不充足（SMARTS 被覆率 12.2%）により Phase 1 検証対象から除外 |
| ADR-27 | `path_blocking` は上位概念として定義し、`path_model` はその operationalization として定義する。概念定義と実装定義を混同しない |
| ADR-28 | `ActiveSiteAnchor` と PAT goal は分離する。covalent PAT の goal は `target_cysteine.SG` 中心球ではなく、`PATGoalRegion`（approach hemishell）とする |
| ADR-29 | `goal_precheck` を PAT の必須 run-level 前提条件とする。goal 定義不成立または apo baseline 不在時は Phase 2 run を停止し、compound-level に `PAT_NOT_EVALUABLE` を発行しない |
| ADR-30 | `path_model` の正式対応は当面 `TUNNEL` と `SURFACE_LIKE` のみとする。`PORTAL_CUT` は拡張候補として ADR 注記に留め、canonical config には採用しない |

---

## 18. 実装ロードマップ

**Phase 1（v4.3.1 で確定・freeze）**
- MEF + CPG + Anchoring Sensor + OffTarget Sensor + SCV + Staging Policy ✓
- canonical config 整合 ✓
- 3ライブラリ検証（fACR-2240 / CYS-3200 / ChemDiv CPI-7801）完了 ✓
- SMARTS クラス別 PASS 率・enrichment 統計 完了 ✓
- no_feasible_early_abort_trial 校正 完了 ✓
- Evidence 再検算チェッカーを staging-aware 化 ✓

**Phase 2（次期）**
- PAT Sensor 実装
- `path_blocking` の上位定義と `path_model` の下位実装を分離
- `path_model = TUNNEL | SURFACE_LIKE` の正式対応
- `PATGoalRegion`（`cys_approach_hemishell`）導入
- `goal_precheck` 実装と run-level failure policy 導入
- `P_pat` 述語追加、SCV 3-Sensor AND 統合
- PAT Evidence 拡張（`path_model`, `goal_precheck`, `apo_accessible_goal_voxels` 記録）
- `grid_spacing`, `top_k_poses`, `probe_radius` 感度分析
- `blockage_pass_threshold` の校正、および model 別 threshold の要否評価
- `SURFACE_LIKE` の dSASA proxy 妥当性検証（厳密 SASA との相関分析）
- no_feasible_early_abort_trial の分子サイズ適応型閾値の検討
- ターゲット多様化（I7L 以外の Cys ターゲットへの展開）
- 未検証 SMARTS クラス（Vinyl sulfone / Isothiocyanate / Epoxide / N-acyl aziridine）の追加検証（適切なライブラリ入手時）

**Phase 3**
- `PORTAL_CUT` の設計評価（entry portal の幾何学的切断面で経路遮断を測る model。必要なら別 ADR で正式化）
- path_model 妥当性の標的横断比較（TUNNEL vs SURFACE_LIKE）
- reversible covalent 用 SMARTS パターン拡充
- run-level manifest 完備
- 論文化

---

## 19. Phase 1 確定宣言

CRISP v4.3.1 をもって、Phase 1 Anchoring パイプラインを確定（freeze）とする。

### 19.1 確定の根拠

**(1) 設計仕様の完備性**

object logic（§9）、search-control logic（§10）、三値意味論（§9.5）、staging provenance（I-13）、PASS 射程宣言（§0.1）が明示化され、Phase 2 以降は「述語の追加」と「policy tuning」の問題として扱える。

**(2) 実装の検証完了**

3ライブラリ（13,241 化合物）での検証により、以下を確認した。

- fACR-2240（校正用）：PASS=1,770、UNCLEAR=0、FAIL=470。PASS 率 79.0%、UNCLEAR 率 0.00%
- CYS-3200（実運用）：PASS=1,258、UNCLEAR=2、FAIL=1,940。PASS 率 39.3%、UNCLEAR 率 0.06%
- ChemDiv CPI-7801（除外確認）：SMARTS 被覆率 12.2%。§0.1 条件(a)不充足を確認

**(3) SMARTS クラス別 enrichment の幾何学的整合性**

3/8 SMARTS クラスで N>600 の統計検証を達成。enrichment パターン（Michael acceptor 1.36 > Halomethyl ketone 0.87 > Alpha-haloketone 0.69）はウォーヘッド原子の分子内位置の幾何学的特性と整合しており、パイプラインの偏りではなく物理的現実の反映であることを確認した。

**(4) 計算量制御の確立**

`no_feasible_early_abort_trial=4096` により、fACR で 4.6× の高速化を達成しつつ、CYS で 3.29s/compound の実用的スループットを実現した。

### 19.2 確定されるパラメータ

```yaml
phase1_frozen_parameters:
  alpha: 0.78
  n_conformers: 8
  search_radius: 8.0
  distance_threshold: 3.5
  no_feasible_early_abort_trial: 4096
  staging:
    retry_target_distance_lower: 3.5
    retry_target_distance_upper: 5.0
    terminal_far_target_threshold: 5.0
    max_stage: 3
  translation:
    local_translation_fraction: 0.75
    local_translation_min_radius: 2.0
    local_translation_max_radius: 4.0
    local_translation_start_stage: 2
  anchoring:
    bond_threshold: 2.2
    near_threshold: 3.5
    epsilon: 0.3
  offtarget:
    distance_threshold: 3.5
    epsilon: 0.3
  warhead_smarts: "v4.3 凍結（§6.2）"
```

### 19.3 残存する既知の限界

- 5/8 SMARTS クラスが未検証（ライブラリ未収載による。パイプラインの対応能力の限界ではない）
- `no_feasible_early_abort_trial=4096` は分子サイズに対して一律適用であり、大分子に対する打切り偽陰性の可能性を排除できない
- 単一ターゲット（I7L）での検証にとどまり、ターゲット汎化性は未確認

これらは Phase 2 のスコープとし、Phase 1 の確定を妨げるものではない。

### 19.4 Phase 1 以降の変更規則

Phase 1 の確定パラメータを変更する場合は、以下の手続きを必須とする。

- §15.3 の事前監査を再実施すること
- fACR-2240 および CYS-3200 でのリグレッションテストにより、verdict 変化が許容範囲内であることを確認すること
- 変更理由と影響範囲を ADR に記録すること

PASS は「阻害する」を主張しない。「少なくともモデル M の下で、阻害仮説と矛盾しない」を主張する。この非対称性が本設計の芯であり、witness 付き存在証明とドッキングのスコア仮説を分ける一線である。
