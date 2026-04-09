# WP-4 / WP-5 Audit Criteria

Status: accepted  
Date: 2026-04-09  
Parent: `adr_v3_10_full_migration_contract.md`, `wp1_wp2_channel_contracts_schema_freeze.md`, `comparable_channels_semantics.md`  
Scope: WP-4（full-scope denominator + FULL_VERDICT_COMPARABLE 集計）と WP-5（exploratory → required promotion gate 自動化）の実装監査観点を定義する。WP-3 完了を前提とする。

---

## 前提条件

WP-4 / WP-5 は以下の完了を前提とする。

| dependency | deliverable | status |
|---|---|---|
| WP-1 | Cap formal contract (ADR-V3-03), Catalytic formal contract (ADR-V3-04), mapping framework | closed |
| WP-2 | verdict_record.json migration conditions, `run_drift_report.json` filename freeze | closed |
| WP-3 | full-SCV input coverage checker, cross-artifact consistency checker, operator display guard | required before WP-4/WP-5 着手 |
| comparable_channels 語義 | rc2-mappable FROZEN channel のみ; Cap は参加不可; NOT_COMPARABLE は derived status | closed |

---

## WP-4: Full-Scope Denominator + FULL_VERDICT_COMPARABLE Aggregation

### 4.1 実装責務

WP-4 は ADR-V3-10 §denominator で最終凍結された分母定義を bridge comparator 実装に落とす。対象は以下の四指標である。

| metric | denominator | source |
|---|---|---|
| verdict_match_rate | FULL_VERDICT_COMPARABLE subset | ADR-V3-10 |
| verdict_mismatch_rate | FULL_VERDICT_COMPARABLE subset | ADR-V3-10 |
| coverage_drift_rate | 全 compounds | ADR-V3-10 |
| applicability_drift_rate | 全 compounds | ADR-V3-10 |

加えて、current Path-only scope の `path_component_match_rate`（COMPONENT_VERDICT_COMPARABLE subset 分母）は既存実装として保持し、full scope 指標と混同しない。

### 4.2 監査観点

#### 4.2.1 FULL_VERDICT_COMPARABLE subset の算出正確性

FULL_VERDICT_COMPARABLE は、「rc2 SCV の full verdict formula が要求する**全 required SCV components**について、対応する v3 mapping が FROZEN であり、かつ当該 compound で coverage_drift = 0, applicability_drift = 0, metrics_drift = 0 を満たす」場合にのみ定義される subset である。

したがって、required SCV components のいずれかが FROZEN 未達である間は、FULL_VERDICT_COMPARABLE は**空集合または not computable**として扱う。現時点では `scv_pat` のみが FROZEN、`scv_anchoring` は CANDIDATE、`scv_offtarget` は UNKNOWN であるため、full verdict comparability は未成立であり、`verdict_match_rate` / `verdict_mismatch_rate` は数値化してはならない。

| audit item | pass condition | fail signal |
|---|---|---|
| subset に含まれる compound は全 required SCV components が FROZEN かつ comparable | compound ごとに、full verdict formula に必要な全 FROZEN mapping component で coverage_drift = 0, applicability_drift = 0, metrics_drift = 0 | required SCV component 未充足のまま subset が算出される |
| v3-only evidence channel が subset 判定に影響しない | Cap evidence と Catalytic Rule3B の有無が FULL_VERDICT_COMPARABLE 判定を変えない | v3-only evidence の materialization 有無で subset membership が変動する |
| CANDIDATE / UNKNOWN mapping channel が subset に入らない | `scv_anchoring` が CANDIDATE、`scv_offtarget` が UNKNOWN の間は full subset は空集合または not computable | CANDIDATE / UNKNOWN を FROZEN 相当として扱っている |
| subset が空または not computable のとき verdict_match_rate は N/A | FULL_VERDICT_COMPARABLE count = 0 または computable = false → 数値化しない | 0/0 を 0% や 100% に丸めている |

#### 4.2.2 verdict_match_rate の活性化条件

| audit item | pass condition | fail signal |
|---|---|---|
| VN-01–VN-06 が全て satisfied でない限り verdict_match_rate は N/A | v3_shadow_verdict == None のとき verdict_match_rate を数値出力しない | VN gate bypass |
| v3_shadow_verdict が None なのに verdict_match_rate が数値 | ADR-V3-10 hard block に該当 | cross-artifact inconsistency |
| verdict_match_rate と path_component_match_rate の non-equivalence | 両者が別 field / 別 label / 別分母で保持されている | 一方が他方の alias になっている |

#### 4.2.3 分母の正確性

| audit item | pass condition | fail signal |
|---|---|---|
| coverage_drift_rate の分母は全 compounds | 分母 = run 内の total compound count | 分母が subset に絞られている |
| applicability_drift_rate の分母は全 compounds | 同上 | 同上 |
| verdict_match_rate の分母は FULL_VERDICT_COMPARABLE のみ | 分母 ≠ total compounds | 分母 = total compounds |
| path_component_match_rate の分母は COMPONENT_VERDICT_COMPARABLE のみ | Path-only scope では変更なし | full scope 導入で分母が汚染された |

#### 4.2.4 v3-only evidence の隔離

| audit item | pass condition | fail signal |
|---|---|---|
| Cap evidence が component_matches に含まれない | comparable_channels_semantics design note 準拠 | Cap が component_matches dict に key として登場 |
| Catalytic Rule3B が component_matches に含まれない | 同上 | Rule3B evidence が match 対象に含まれる |
| v3-only evidence が match rate の分子に含まれない | 分子カウントが comparable_channels のみを反映 | v3-only match/mismatch が分子に混入 |
| RunDriftReport に v3-only section が分離記録されている | v3-only evidence は drift report の独立 section | comparable drift と v3-only drift が同一 list に混在 |

#### 4.2.5 scope 遷移の安全性

| audit item | pass condition | fail signal |
|---|---|---|
| comparator_scope が path_only_partial のまま full scope 集計が走らない | scope check が aggregation 前に入っている | path_only_partial で verdict_match_rate が数値化される |
| comparable_channels 拡大と scope 遷移が atomic | channel 追加と scope string 更新が同一 transaction | channels は拡大されたが scope string が旧値のまま |
| scope 遷移前後で path_component_match_rate が破壊されない | full scope 追加後も Path-only 指標は別 field で保持 | scope 遷移で path_component_match_rate field が消滅 or 上書き |

#### 4.2.6 replay / determinism

| audit item | pass condition | fail signal |
|---|---|---|
| 同一 RunDriftReport 入力 → 同一 FULL_VERDICT_COMPARABLE subset | deterministic | 実行ごとに subset membership が変動 |
| run_drift_report.json の expected_output_digest が generator_manifest に記録される | ADR-V3-10 replay contract 準拠 | drift report が manifest 外で生成される |

---

## WP-5: Exploratory → Required Promotion Gate Automation

### 5.1 実装責務

WP-5 は ADR-V3-06 PR-01–PR-06 および ADR-V3-10 の full verdict claim gate を CI automation に落とす。重要な制約として、**automation は candidacy 判定のみを行い、実際の required 昇格は human explicit decision を要する**。

### 5.2 監査観点

#### 5.2.1 gate 評価の正確性

| audit item | pass condition | fail signal |
|---|---|---|
| PR-01: channel formal contract ADR の complete 判定 | ADR document の repo merge status を参照 | 手動 flag や config override で bypass 可能 |
| PR-02: 30 run green の window 計算 | 連続 30 run を要求し、gap があればリセット | 累積 30 run（非連続）で pass |
| PR-03: baseline 比較の scope 意識 | path_only_partial → path_component_match_rate, full → verdict_match_rate | scope に依存せず一律に verdict_match_rate を使っている |
| PR-04: metrics_drift = 0 の window 計算 | 直近 30 run で metrics_drift 件数 = 0 | 30 run 平均が 0 に近いだけ（丸め） |
| PR-05: Windows CI の 30 run green | Windows 環境で連続 30 run green | Linux のみで判定、Windows は skip |
| PR-06: rc2-frozen regression check | rc2-frozen suite が PR branch で全 green | rc2-frozen suite の一部 job のみ確認 |

#### 5.2.2 channel-owned vs SCV-level の分離

| audit item | pass condition | fail signal |
|---|---|---|
| channel-level の promotion candidacy が SCV-level verdict claim を imply しない | PR-01–PR-06 pass が v3_shadow_verdict 活性化を trigger しない | channel promotion → v3_shadow_verdict non-None の自動連鎖が存在 |
| VN-01–VN-06 が独立 gate として評価される | PR gate と VN gate が別 evaluation path | VN gate が PR gate に含まれている |
| full verdict claim gate は全 SCV component の集合的条件 | scv_pat + scv_anchoring + scv_offtarget 全ての mapping が FROZEN | 一部 component の FROZEN で claim gate pass |

#### 5.2.3 authorization boundary

| audit item | pass condition | fail signal |
|---|---|---|
| automation は candidacy を report するのみ | promotion candidate status を出力するが、required matrix への実際の追加は行わない | 自動で `.github/workflows/v29-required-matrix.yml` を変更する |
| human explicit decision が介在する | promotion candidate → required 昇格に PR review + merge decision が必要 | cron job や webhook で自動昇格 |
| design-only 文書が policy authorization として実行されない | v3x_path_verdict_comparability.md §5.2 の「本文書は authorize しない」が automation に反映 | design note の存在を promotion 条件として参照 |

#### 5.2.4 NP 条件の enforcement

| audit item | pass condition | fail signal |
|---|---|---|
| NP-01: sidecar mode 専用 channel は required 候補にならない | public verdict に影響しない channel は candidate にならない | sidecar-only channel が candidate list に登場 |
| NP-02: contract 未完 channel は required 候補にならない | ADR-V3-03/04 が merge されていない channel は除外 | formal contract status を check しない |
| NP-03: baseline 未達 channel は required 候補にならない | path_component_match_rate < 95% の channel は除外 | baseline check が absent |
| NP-04: Windows 不安定 channel は required 候補にならない | Windows CI が 30 run green でない channel は除外 | platform check が absent |

#### 5.2.5 comparable_channels 語義の遵守

| audit item | pass condition | fail signal |
|---|---|---|
| v3-only evidence channel が promotion candidate にならない | Cap は rc2 SCV component mapping を持たないため candidate 対象外 | Cap が promotion candidate に含まれる |
| CANDIDATE mapping channel は required-CI candidate になりうるが comparable_channels には入らない | Catalytic Rule3A が CANDIDATE の段階では required-CI candidacy の評価対象になりうる一方、semantic comparability は未成立である | mapping CANDIDATE を comparable として扱う |

#### 5.2.6 operator surface との整合

| audit item | pass condition | fail signal |
|---|---|---|
| promotion candidacy status が operator report に `[exploratory]` 付きで表示される | candidacy 表示は exploratory label 内 | candidacy が primary verdict section に混入 |
| promotion candidacy が verdict_match_rate の数値化を trigger しない | candidacy report と match rate report が独立 | candidacy 達成 → verdict_match_rate 表示 の連鎖 |
| rc2-frozen suite の required job list が promotion 前後で変化しない | promotion candidate 段階では rc2 matrix は不変 | candidacy 段階で rc2 matrix に exploratory job が追加 |

---

## 共通監査観点

### Cross-WP consistency

| audit item | pass condition | fail signal |
|---|---|---|
| WP-4 の FULL_VERDICT_COMPARABLE 判定と WP-5 の PR-03 baseline 判定が、**full scope の場合に限り**同一 subset を参照する | full scope では同一 computation path / shared module を参照し、path_only_partial では PR-03 は `path_component_match_rate` と `COMPONENT_VERDICT_COMPARABLE` を参照する | full scope と path_only scope で異なる subset / denominator が混同される |
| WP-4 の scope check と WP-5 の VN gate が同一 mapping status source を参照する | channel-to-SCV-component mapping status の single source of truth | WP-4 は mapping table を、WP-5 は config flag を参照する等の乖離 |
| WP-3 の validator が WP-4/WP-5 の出力に対しても有効 | WP-3 validator が WP-4 出力（drift report）と WP-5 出力（candidacy report）を検証可能 | WP-4/WP-5 が WP-3 validator を bypass する |

### Semantic delta 混入 block criteria

以下のいずれかが WP-4 / WP-5 の実装で検出された場合、merge を block する。

| block criterion | WP-4 | WP-5 |
|---|---|---|
| path_component_match_rate を verdict_match_rate の alias として扱っている | ● | ● |
| Cap materialization を comparability として計上している | ● | ● |
| v3_shadow_verdict を current scope で non-None にしている | ● | ● |
| output_inventory.json を拡張している | ● | ● |
| missing field を推測値で埋めている | ● | — |
| diagnostic field を final semantic field へ昇格させている | ● | — |
| automation が human decision なしに required 昇格を実行している | — | ● |
| rc2-frozen suite の required matrix を変更している | — | ● |
| mapping CANDIDATE を FROZEN として扱っている | ● | ● |
| v3-only evidence を comparable evidence として計上している | ● | ● |

---

## 文書間の整合性

| this document | authority reference | consistency |
|---|---|---|
| FULL_VERDICT_COMPARABLE 分母 | ADR-V3-10 §denominator | 四指標の分母定義を継承 |
| COMPONENT_VERDICT_COMPARABLE 分母 | path_comparability §4.2 | Path-only 指標の分母定義を継承 |
| v3_shadow_verdict 活性化 gate | path_comparability §2.4 VN-01–VN-06 via ADR-V3-10 | by reference |
| comparable_channels 語義 | comparable_channels_semantics note | rc2-mappable FROZEN のみ |
| NOT_COMPARABLE = derived status | ADR-V3-10 §channel lifecycle state | primary 3 値 + derived |
| Cap 参加不可 | comparable_channels_semantics + WP-1 ADR-V3-03 §9 | Cap は rc2 SCV に component なし |
| Catalytic Rule3A = CANDIDATE | WP-1 mapping framework §3 | FROZEN まで comparable_channels 不参加 |
| PR-01–PR-06 | bridge_ci_contracts ADR-V3-06 §5 | by reference |
| NP-01–NP-04 | bridge_ci_contracts ADR-V3-06 §4 | by reference |
| authorization boundary | path_comparability §5.2 | design-only は authorize しない |
| run_drift_report.json | WP-2 filename freeze | canonical filename 確定済み |
| replay contract | ADR-V3-10 §replay / falsifiability | generator_manifest + expected_output_digest |

---

Proposed branch: `docs/v3-wp4-wp5-audit-criteria`  
Proposed commit: `docs(v3): define WP-4 / WP-5 audit criteria for full migration ADR`

---

*End of document*
