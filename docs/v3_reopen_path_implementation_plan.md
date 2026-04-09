# v3 Reopen-Path Implementation Plan (corrected)

Status: design-only  
Date: 2026-04-09  
Authority: この文書は `v3_reopen_path_decision_frame.md` を起点とし、current authority set のみを Source of Truth として扱う。stale / superseded 文書は引用しない。  
Scope: reopen-path の最初の実装対象を定め、current authority を壊さずに stronger-claim 側へ進むための設計・実装順序を定義する。

---

## 1. 要点

**reopen-path の実装順序**: RP-0 で Catalytic Rule3A の public comparable representation を docs-only で凍結し、RP-0.5 で scope atomics（`comparator_scope` と `comparable_channels` の同時変更 semantics）を docs-only で凍結し、その後にだけ RP-1 の human widening decision + code に進むこと。

**keep-path close を壊さない前提**: current public scope（`path_only_partial` / `comparable_channels=["path"]` / `v3_shadow_verdict` inactive / `verdict_match_rate=N/A` / required promotion なし / public widen なし）は reopen-path の全 phase を通じて、explicit human decision が下されるまで不変である。

**まだ code に入るべきでない論点**: full verdict comparability の活性化、operator-facing activation、required promotion、Cap の comparable 参加。これらは blocker が open のままである。`scv_offtarget` source decision は既に Option B（thin OffTarget wrapper）で FROZEN であり、open question ではない。

---

## 2. 現状診断

### 2.1 Current frozen boundary

reopen-path decision frame と wp6 public inclusion decision memo が固定する current boundary は以下のとおりである。

`verdict_record.json` が canonical Layer 0 authority であり、`sidecar_run_record.json` は mirror である。`output_inventory.json` は rc2 authority のまま不変。`generator_manifest.json` は sidecar inventory / replay contract のまま。`comparator_scope` は `path_only_partial`、`comparable_channels` は `["path"]`、`v3_shadow_verdict` は inactive、`verdict_match_rate` は `N/A`。Cap は `comparable_channels` に参加不可（rc2 SCV component mapping が存在しない v3-only evidence）。required promotion は未承認。public widen は未承認。

### 2.2 SCV component mapping status（current authority 確認）

wp1_wp2_channel_contracts_schema_freeze.md と adr_v3_10_full_migration_contract.md の both が明示するとおり、三 SCV component の mapping は全て FROZEN である。

| SCV component | v3 source | mapping status |
|---|---|---|
| scv_pat | Path channel via PathChannelProjector | **FROZEN** |
| scv_anchoring | Catalytic Rule3A via CatalyticChannelProjector | **FROZEN** |
| scv_offtarget | thin OffTarget channel wrapper via read-only `core_compounds` snapshot | **FROZEN** (Option B) |

pre-freeze fragments が `scv_anchoring=CANDIDATE` や `scv_offtarget=UNKNOWN` と記述していた場合、それらは superseded であり current authority ではない（adr_v3_10 update note, wp1_wp2 update note）。

したがって、full verdict comparability を阻んでいるのは mapping 未決定ではなく、**public bridge inclusion decision + scope atomics 定義 + WP-3/WP-4 実装 + human activation decision** である。

### 2.3 Reopen-path で open の decision

reopen-path decision frame §Open Decisions が列挙する四つの independent decision surface を、修正した blocker 状況とともに整理する。

**Decision 1: `comparable_channels` widening**

widening の唯一の現実的候補は Catalytic Rule3A である。mapping は FROZEN だが public comparable inclusion は未承認。wp6 guard は「Catalytic Rule3A mapping/source freeze does not authorize public comparable inclusion」と明示している。

さらに wp6 は「`comparator_scope` widening と `comparable_channels` widening は atomic でなければならない」と規定している。したがって、`comparable_channels` を `["path", "catalytic"]` に拡大するには、同時に `comparator_scope` を `path_only_partial` から次の値に変更しなければならない。次の scope 値は RP-0.5 で `path_and_catalytic_partial` に凍結する。

Cap は構造的に参加不可のまま。

**Decision 2: operator activation**

`v3_shadow_verdict` activation と `verdict_match_rate` 数値化は、three mapping 全て FROZEN（済み）+ public bridge inclusion decision + WP-3/WP-4 実装 + human activation decision を全て経た後にのみ可能。mapping incompleteness はもはや blocker ではないが、public activation は未承認。

**Decision 3: required promotion**

PR-01–PR-06 条件は channel-owned だが human explicit decision を要する。current scope が widen された後にのみ意味を持つ。

**Decision 4: blocker inventory closure**

Catalytic について以下が未固定のまま残っている。

- public comparable representation（Rule3A comparable / Rule3B v3-only の混合表現）
- scope atomics（`comparator_scope` の次の enum 値と widening semantics）
- applicability semantics（public representation 視点での freeze）
- drift schema（Catalytic public drift の定義）
- operator surface rendering（mixed comparable / v3-only channel の表示規則）

### 2.4 First reopen candidate の妥当性評価

Catalytic Rule3A public comparable inclusion を最初の reopen 対象とする理由は三つある。

第一に、mapping が FROZEN 済みであり、internal technical readiness は充足している。

第二に、Catalytic Rule3A は `comparable_channels` 語義（rc2-mappable FROZEN channel のみ）を満たしうる唯一の next candidate である。

第三に、scv_offtarget も FROZEN 済みであるため、Catalytic widening 後に full-SCV input coverage が成立する技術的可能性がある。ただし、public activation は別の human decision であり、widening が自動的に activation を trigger しない。

Catalytic は Rule3A（comparable 候補）と Rule3B（v3-only）の二面性を持つ。この mixed representation は RP-0 で `v3_catalytic_public_representation_freeze.md` に凍結し、scope atomics は RP-0.5 で `v3_scope_atomics_definition.md` に凍結する。したがって、RP-1 に残る blocker は representation 未定義ではなく、human widening decision と code 実装である。

### 2.5 UNKNOWN register

| topic | status | resolution path |
|---|---|---|
| Catalytic Rule3A public comparable representation | frozen | `v3_catalytic_public_representation_freeze.md` |
| `comparator_scope` の次の enum 値 | frozen | `v3_scope_atomics_definition.md` |
| scope atomics widening semantics | frozen | `v3_scope_atomics_definition.md` |
| Catalytic mixed comparable / v3-only operator surface rendering | frozen | `v3_catalytic_public_representation_freeze.md` |
| full verdict comparability の activation 時期 | open（technical blocker は解消方向だが human decision が必要） | Phase RP-3 以降 |
| operator-facing activation が scope widening の前か後か | UNKNOWN | reopen-path decision frame が explicit に残している |
| required promotion の対象 bundle | UNKNOWN | reopen-path decision frame が explicit に残している |
| 将来 `reported_channels` 概念が必要か | UNKNOWN | comparable_channels_semantics が explicit に残している |

注記: `scv_offtarget` source は UNKNOWN ではない。Option B thin OffTarget wrapper で FROZEN 済み。

---

## 3. Reopen-path roadmap

### Phase RP-0: Catalytic public comparable representation freeze（docs-only）

**目的**: Catalytic Rule3A を `comparable_channels` に入れるために必要な、public representation / applicability / drift / operator surface の定義を docs-only で閉じる。code には入らない。

**前提**: keep-path close 不変。current `comparable_channels=["path"]` 不変。この phase は representation を定義するだけであり、widening 自体を authorize しない。

**実装項目**:

(a) Catalytic Rule3A public comparable representation の定義。推奨は、`comparable_channels` に `"catalytic"` を登録し、`component_matches` には `"catalytic_rule3a"` のみが参加し、Rule3B は v3-only section に分離記録する方式。comparable_channels_semantics の語義は変更しない。

(b) Catalytic public applicability semantics freeze。`evidence_core` missing → `evaluate() returns None` → APPLICABILITY_ONLY。`component_matches["catalytic_rule3a"]` は None（比較不能）。

(c) Catalytic public drift schema freeze。Rule3A の `best_target_distance` projection に対する drift 種別を bridge_ci_contracts taxonomy に接続。semantic narrowing gap（motif-based vs warhead-atom distance）は expected deviation として documented。initial tolerance は empirical data で校正するため exact 値は UNKNOWN のまま残してよい。

(d) Operator surface rendering。Rule3A は `component_matches` に表示。Rule3B は `[v3-only]` で分離。channel 全体として `[exploratory]` label 維持。

**完了条件**: design note merge。`comparable_channels` 語義を壊さず、Catalytic mixed representation が一意に定義されていること。

**fail criteria**: Rule3B が `component_matches` に混入。定義が replay-unsafe。

### Phase RP-0.5: scope atomics definition（docs-only）

**目的**: wp6 guard「`comparator_scope` widening と `comparable_channels` widening は atomic」を満たすために、`path_only_partial` の次の scope 値とその semantics を定義する。code には入らない。

**前提**: Phase RP-0 complete。keep-path close 不変。

**実装項目**:

(a) `comparator_scope` の次の enum 値を定義する。推奨は `path_and_catalytic_partial`。この名前は、Path + Catalytic Rule3A が comparable であるが full verdict comparability は未活性であることを表す。

(b) scope 遷移の semantics を定義する。`path_only_partial` → `path_and_catalytic_partial` の遷移は `comparable_channels` の `["path"]` → `["path", "catalytic"]` と atomic に行う。一方だけの変更は hard block。

(c) `path_and_catalytic_partial` scope で成立する指標と成立しない指標を明示する。

| 指標 | `path_and_catalytic_partial` scope での status |
|---|---|
| `path_component_match_rate` | 継続（既存。分母は COMPONENT_VERDICT_COMPARABLE のうち Path subset） |
| catalytic_rule3a component match | 新設（分母は COMPONENT_VERDICT_COMPARABLE のうち Catalytic Rule3A subset） |
| `verdict_match_rate` | N/A のまま（full-SCV public activation が別 human decision で承認されるまで） |
| `v3_shadow_verdict` | inactive のまま（同上） |

(d) scope 遷移が `v3_shadow_verdict` activation を trigger しないことを明示する。full verdict comparability の activation は scope 遷移とは independent な human decision surface である。三 mapping が全て FROZEN であっても、public activation は別決定。

**完了条件**: scope atomics design note merge。wp6 guard と矛盾しないこと。

**fail criteria**: scope 遷移が `v3_shadow_verdict` activation を implicit に trigger する。`comparable_channels` 単独 widening が許容される。

### Phase RP-1: widening decision + implementation（human decision + code）

**目的**: Catalytic Rule3A を `comparable_channels` に追加する human decision を取得し、scope atomics に従って code に反映する。

**前提**: Phase RP-0 + RP-0.5 complete。keep-path close 不変。`v3_shadow_verdict` inactive 不変。

**human decision point**: `comparable_channels` を `["path", "catalytic"]` に、`comparator_scope` を `path_and_catalytic_partial` に、atomic に変更するかどうかを explicit PR merge で決定する。

**実装項目**:

(a) `verdict_record.json` の `comparable_channels` と `comparator_scope` の atomic 更新。

(b) `component_matches` に `"catalytic_rule3a"` entry を追加。

(c) `v3_only_evidence_channels` の調整。Rule3B は v3-only section に残す。

(d) WP-3 validator の更新。

(e) drift report の Catalytic Rule3A section 追加。Rule3B は v3-only section に分離。

**完了条件**: human decision merged。code merged。30 run exploratory green。keep-path invariants 不変（`v3_shadow_verdict` None、`verdict_match_rate` N/A、`output_inventory.json` 不変）。

**fail criteria**: `v3_shadow_verdict` 活性化。`verdict_match_rate` 数値化。Cap 混入。Rule3B comparable 混入。scope と channels の非 atomic 変更。

### Phase RP-2: full verdict gate preparation（code）

**目的**: WP-3 の validation-only 実装（full-SCV input coverage checker, cross-artifact consistency checker, operator display guard）を完了し、WP-4 の full-scope denominator 実装に進む。

**前提**: Phase RP-1 complete。三 SCV component mapping 全て FROZEN。public activation は未承認のまま。

**実装項目**:

(a) WP-3: full-SCV input coverage checker。三 mapping 全て FROZEN であることを runtime で検証。`full_verdict_computable` flag を true に設定可能にする。ただし `v3_shadow_verdict` は None のまま。

(b) WP-3: cross-artifact consistency checker。verdict_record / sidecar_run_record / generator_manifest / drift report 間の整合性検証。

(c) WP-3: operator display guard。`v3_shadow_verdict` inactive、`verdict_match_rate` N/A、`[exploratory]` label のすべてを enforcement。

(d) WP-4: FULL_VERDICT_COMPARABLE subset 算出。三 mapping 全て FROZEN + comparable_channels に含まれる全 component で drift clean な compound を subset 化。ただし `verdict_match_rate` 数値化は public activation decision 後に限る。internal では計算可能だが operator surface には出さない。

**完了条件**: WP-3 + WP-4 実装 merged。`full_verdict_computable = true` が internal に設定可能。`verdict_match_rate` は N/A のまま。30 run green。

**fail criteria**: `verdict_match_rate` が operator surface に漏洩。`v3_shadow_verdict` が non-None。

### Phase RP-3: activation / required promotion（human decision）

**目的**: operator-facing `v3_shadow_verdict` activation、`verdict_match_rate` 数値化、exploratory → required promotion を個別に human decision として取得する。

**前提**: Phase RP-2 complete。technical readiness 確立済み。

**human decision point**: 以下は全て independent human decision であり、同時に決定する義務はない。

- `v3_shadow_verdict` activation
- `verdict_match_rate` 数値化
- `comparator_scope` の full への変更（三 SCV component + Cap v3-only + Catalytic Rule3B v3-only を含む最終 scope）
- exploratory → required promotion（WP-5 automation 結果に基づく candidacy report を参照）

**完了条件**: 各 decision が explicit PR merge で記録される。

**fail criteria**: automation が human decision なしに activation / promotion を実行する。

---

## 4. 実装優先順位

**先にやるべき**: Phase RP-0（Catalytic representation freeze、docs-only）と Phase RP-0.5（scope atomics definition、docs-only）。code を一切含まない。contract-before-code の原則に従う。

**次にやるべき**: Phase RP-1（widening、human decision + minimal code）。RP-0 + RP-0.5 merge 後にのみ着手可能。

**その後**: Phase RP-2（WP-3 + WP-4 実装）。RP-1 complete 後。

**最後**: Phase RP-3（activation / promotion、human decision）。RP-2 complete 後。WP-5 automation はこの段階で着手可能。

---

## 5. 監査観点

### 5.1 keep-path close を壊していないかの block criteria

以下のいずれかが検出された場合、reopen-path 実装を block する。

- `comparable_channels` が human decision なしに拡大された
- `comparator_scope` と `comparable_channels` が非 atomic に変更された
- `v3_shadow_verdict` が non-None になった
- `verdict_match_rate` が数値化された
- `path_component_match_rate` が `verdict_match_rate` の proxy として使われている
- `output_inventory.json` が変更された
- `verdict_record.json` canonical authority が巻き戻された
- Cap が `comparable_channels` に登場した
- `comparator_scope` が human decision なしに変更された
- required matrix が変更された
- `scv_offtarget` が UNKNOWN として扱われている（current authority では FROZEN）

### 5.2 reopen-path 実装で semantic delta 混入を防ぐ監査点

- Catalytic Rule3B が `component_matches` に混入していないか
- Catalytic Rule3A の semantic narrowing gap が documented か
- Phase RP-0 の representation freeze が merge される前に Phase RP-1 の code change が着手されていないか
- Phase RP-0.5 の scope atomics が merge される前に widening code が着手されていないか
- design doc / readiness evidence の存在だけで promotion / activation / widen が authorize されていないか
- UNKNOWN が convenience 実装で埋められていないか
- `full_verdict_computable = true` が internal に設定されたことが operator surface への `verdict_match_rate` 漏洩を trigger していないか

### 5.3 operator safety と CI separation の監査点

- operator summary で Catalytic Rule3A が `[exploratory]` 付きで表示されているか
- Catalytic Rule3B が `[v3-only]` で分離表示されているか
- exploratory lane が required matrix に混入していないか
- rc2-frozen suite が reopen-path の変更で regression していないか
- `semantic_policy_version` が全 operator surface に表示されているか
- mixed aggregate summary が生成されていないか

---

## 6. 最初の実装着手案

### Work Package RP-0: Catalytic public comparable representation freeze（docs-only）

**対象ファイル**: `docs/v3_catalytic_public_representation_freeze.md`（新規）

**内容**: §3 Phase RP-0 の (a)–(d)。テストなし。code なし。

**current state**: `v3_catalytic_public_representation_freeze.md` で docs-only freeze 済み。RP-1 code の前提として参照する。

### Work Package RP-0.5: scope atomics definition（docs-only）

**対象ファイル**: `docs/v3_scope_atomics_definition.md`（新規）

**内容**: §3 Phase RP-0.5 の (a)–(d)。`path_and_catalytic_partial` の定義。scope 遷移 semantics。activation 非 trigger 明示。テストなし。code なし。

**current state**: `v3_scope_atomics_definition.md` で docs-only freeze 済み。RP-1 widening decision + code の前提として参照する。

### Work Package RP-1: comparable_channels widening implementation（Phase RP-1 着手時）

**前提**: RP-0 + RP-0.5 merge 済み。human decision で widening が authorize 済み。

**対象ファイル・テスト**: §3 Phase RP-1 参照。

**docs-only に留めるべき論点**: `verdict_match_rate` activation 時期。required promotion 対象。operator-facing activation 順序。

---

## 7. Branch / commit 提案

**docs branch（RP-0）**:

```text
docs/v3-catalytic-public-representation-freeze
```

```text
docs(v3): freeze Catalytic Rule3A public comparable representation, applicability, drift schema, and operator rendering
```

**docs branch（RP-0.5）**:

```text
docs/v3-scope-atomics-definition
```

```text
docs(v3): define comparator_scope path_and_catalytic_partial and atomic widening semantics
```

**implementation branch（RP-1）**:

```text
feat/v3-widen-comparable-channels-catalytic-rule3a
```

```text
feat(v3): atomic widen comparable_channels to ["path","catalytic"] with scope path_and_catalytic_partial
```

RP-0 と RP-0.5 は docs-only で code を含まない。RP-1 は RP-0 + RP-0.5 freeze 後、human widening decision の後にのみ着手する。

---

*End of document*
