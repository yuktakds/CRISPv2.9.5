# ADR-V3-10: Full Migration Contract and Promotion Policy

Status: accepted — design authority for full migration contract boundary  
Date: 2026-04-09  
Parent: `v3x_evidence_channel_kernel_architecture.md`, `v3x_bridge_ci_contracts.md`, `v3x_path_verdict_comparability.md`, `v3_full_migration_preconditions.md`  
Supersedes: `v3x_bridge_ci_contracts.md` §6 full scope baseline provisional rule (this ADR finalizes the denominator left provisional there)

---

## Context

v3.x semantic redesign は architecture level では release-candidate complete と判断されており、current repo で Path-first milestone が成立している。current state は以下で固定されている。

| fact | value |
|---|---|
| comparator_scope | `path_and_catalytic_partial` |
| comparable_channels | `["path", "catalytic"]` |
| comparable component keys | `path`, `catalytic_rule3a` |
| v3-only retained evidence | `cap`, `catalytic_rule3b` |
| v3_shadow_verdict | None / inactive |
| verdict_match_rate | N/A |
| operator display | rc2 primary / v3 secondary |
| output_inventory.json | rc2 authority |
| sidecar inventory | generator_manifest.json |

これらは current scope の closure semantics であり、full migration ready とは別物である。

同時に、`v3_full_migration_preconditions.md` は P1–P7 を列挙し、current sidecar が full-channel migration contract、full verdict comparability、promotion criteria、required CI gating に進む前に満たすべき条件を定義している。

---

## Problem

The current `path_and_catalytic_partial` partial comparator is landed, but the full migration contract boundary remains distinct and not yet operator-activated.

- どの artifact 群が authority なのか
- Cap / Catalytic が materialized された時に comparability を claim してよいのか
- v3_shadow_verdict をいつ non-None にできるのか
- verdict_match_rate をどう定義するのか
- exploratory CI をどの時点で required 候補にできるのか

Current partial-scope documents make clear that component comparability under `path_and_catalytic_partial` is still not SCV-level full verdict comparability. rc2 verdict は anchoring + offtarget + PAT の Kleene 強三値 AND であり、Path channel 単独では rc2 verdict を構成できない。Path-only closure を full verdict comparability に読み替えることは構造的に誤りである。

---

## Decision

本 ADR は以下の五点を決定する。

1. full migration contract の canonical boundary は Layer 0 authority、Layer 1 replay/audit authority、operator-facing secondary を分離した artifact family として定義する
2. channel promotion は simultaneous promotion ではなく channel-owned promotion とする
3. SCV-level full verdict comparability は all-required-SCV-input coverage を満たした場合にのみ成立する
4. v3_shadow_verdict を non-None にするには `v3x_path_verdict_comparability.md` §2.4 の VN-01–VN-06 を全て満たす
5. operator-facing / CI promotion は exploratory と required を分離し続け、required 昇格は explicit gate を通した場合のみ許可する

---

## Scope

対象:
- canonical artifact set と authority layering
- comparable-channel promotion policy
- full verdict comparability contract
- v3_shadow_verdict activation conditions
- operator-facing separation
- CI promotion gate
- replay / falsifiability block 条件

対象外:
- 実装コード
- 具体的 adapter 実装
- Cap / Catalytic formal contract の中身

---

## Non-goals

本 ADR は以下を authorize しない。

- any further widening beyond the current `path_and_catalytic_partial` partial scope
- any silent change to the meaning of current rc2 public outputs
- output_inventory.json の拡張
- current scope での v3 final verdict publish
- mixed summary 生成
- hybrid SCV mode の導入
- proposal-connected Rule 3 の authorization
- diagnostic field の final semantic field への昇格

未定義点は UNKNOWN のまま維持し、推測値で埋めない。

---

## Canonical boundary

### Layer 0: authority

current accepted state では `adr_v3_11_m2_authority_transfer.md` により `verdict_record.json` が canonical Layer 0 record であり、`sidecar_run_record.json` は backward-compatible mirror である。`generator_manifest.json` は canonical sidecar inventory かつ re-materialization contract のまま維持され、`output_inventory.json` は rc2 authority のまま不変である。public bridge inclusion, comparator scope widening, `v3_shadow_verdict`, operator-facing `verdict_match_rate` activation はこの authority transfer に含まれない。

### Layer 1: replay / audit authority

canonical Layer 1 artifact は `v3x_evidence_channel_kernel_architecture.md` §D.1 に従い、`channel_evidence_path.jsonl`, `channel_evidence_cap.jsonl`, `channel_evidence_catalytic.jsonl`, `builder_provenance.json` を中心とする。

`observation_bundle.json` は同 §D.1 implementation note で Layer 1-class artifact として既出であり、SCVObservationBundle の serialized carrier として full verdict claim 時に materialize してよい。ただし、current Path-first milestone における常時 Layer 1 bulleted set を retroactively rename するものではない。

operator が読む summary はここから派生してよいが、authority 自体は Layer 1 の machine-readable record にある。`builder_provenance.json` は current sidecar では operator-facing truth-source-chain record とされているが、authority 上は Layer 1 replay/audit record である。

### Operator surface: secondary only

`bridge_operator_summary.md`、`eval_report` / `qc_report` の v3 section は、`semantic_policy_version` を明示し、`[exploratory]` を可視化し、rc2 verdict を primary として表示する。Cap / Catalytic materialization を full verdict comparability と読ませてはならない。operator surface は説明のために存在し、authority を再定義するためには使わない。

---

## Comparable-channel promotion policy

### Channel-owned promotion

本 ADR は channel-owned promotion を採用する。P1・P3・P6 が明示するように、promotion 条件は channel-specific であり、Path / Cap / Catalytic は必要 evidence も blocker も異なる。「全部そろうまで一つも比較対象に入れない」simultaneous promotion は不要である。ただし、個別 channel promotion は full verdict comparability と切り離される。channel comparability は個別に上がりうるが、SCV-level verdict comparability は collective gate である。

### Materialization ≠ comparability

channel が sidecar で materialize されたことは、観測や provenance の記録が存在することを意味するだけで、`comparable_channels` 参加を意味しない。comparability を claim するには、rc2-side source inventory、adapter coverage table、missing-source behavior freeze、lossless projector field preservation、deterministic test の五条件が必要である（P1）。Cap is materialized-but-not-comparable in the current scope. Catalytic participates publicly only through the frozen `catalytic_rule3a` comparable surface; Rule3B remains v3-only evidence and must not be read as full-channel comparability.

### Two-stage channel promotion

channel promotion は二段階で扱う。第一段階は **channel contract completion** であり、当該 channel が comparability-ready かを評価する。第二段階は **public bridge inclusion** であり、当該 channel を `comparable_channels` に実際に入れるかを決める。前者は channel-owned だが、後者は operator safety を見るため bridge contract 側の explicit decision が必要である。

The intermediate public scope is now defined and landed as `path_and_catalytic_partial`. That landed partial scope does not by itself activate `v3_shadow_verdict` or numeric `verdict_match_rate`. UNKNOWN remains whether any stronger public scope beyond the current partial bundle should ever be defined.

### Channel lifecycle state

以下の三状態は `EvidenceState`（SUPPORTED / REFUTED / INSUFFICIENT）ではなく、**channel migration-level lifecycle state** である。EvidenceState は evidence-level state を表し、lifecycle state とは混同しない。`v3_full_migration_preconditions.md` P3 が四つの状態の区別を要求し、`v3x_evidence_channel_kernel_architecture.md` §C.5–C.6 が `evaluate() → None` と run-level applicability 分離で実装面を支える。

```text
ChannelLifecycleState (primary, mutually exclusive):
  DISABLED              — channel is not enabled for this run / policy
  APPLICABILITY_ONLY    — preconditions were evaluated, but no ChannelEvidence was produced
  OBSERVATION_MATERIALIZED — ChannelEvidence and/or Layer 1 evidence artifacts exist
```

P3 が要求する四つ目の区別 NOT_COMPARABLE は primary enum 値ではなく、以下の条件から**導出される report-level status** である。

```text
NOT_COMPARABLE (derived):
  channel_lifecycle_state == OBSERVATION_MATERIALIZED
  AND channel ∉ comparable_channels
```

この導出は `comparable_channels`（rc2-mappable FROZEN channel のみ）と `v3_only_evidence_channels` の二 field から一意に決定される。独立 enum 値として持たないことで、materialization/applicability 軸と comparability 軸の二軸が単一 enum に混入する問題を回避する。

`OBSERVATION_MATERIALIZED` → `comparable_channels` 参加には P1 五条件 + public bridge inclusion decision が必要である。lifecycle state から `comparable_channels` 参加への自動昇格は存在しない。

---

## Full verdict comparability contract

### Definition

SCV-level full verdict comparable とは、v3 channel 群からのみ構成された SCVObservationBundle が、frozen channel-to-SCV-component mapping に従って rc2 SCV が要求する全 component を欠落なく満たし、その結果として得られる v3_shadow_verdict を rc2 verdict と同一 public taxonomy 上で比較できる状態を意味する。

「component-level comparability が何個か成立している」ことではなく、「SCV が必要とする全 component の source が定義済みである」ことが要件である。

Under the current `path_and_catalytic_partial` scope, component-level comparability exists for `path` and `catalytic_rule3a`, but this still does not constitute SCV-level full verdict comparability. `path_component_match_rate` and any `catalytic_rule3a` component match remain component-level indicators; neither is a synonym for `verdict_match_rate`. This ADR preserves that non-equivalence.

### v3_shadow_verdict activation gate

v3_shadow_verdict を non-None にしてよい条件は、`v3x_path_verdict_comparability.md` §2.4 の VN-01–VN-06 を、本 ADR の full migration gate として by reference で採用する場合に限る。以下の散文説明は補足であり、条件の正本は VN table である。

| this ADR gate | source of truth |
|---|---|
| full-SCV mapping frozen | VN-01 |
| all mapped SCV components generated by v3 channels | VN-02 |
| all projectors integrated to SCV core | VN-03 |
| all corresponding channel formal contract ADRs complete | VN-04 |
| sidecar invariant test 30-run green | VN-05 |
| verdict_record.json schema freeze and Layer 0 authority migration complete | VN-06 |

VN-01 から VN-06 のいずれかが未達の間、v3_shadow_verdict は None、verdict_match_rate は N/A のままである。

### Hybrid SCV mode rejection

本 ADR は hybrid SCV mode を採用しない。未定義 component を rc2 observation から借用すると、semantic policy version の一貫性が壊れ、verdict-level comparison の情報量がゼロになり、silent semantic drift を起こす。この棄却理由は `v3x_path_verdict_comparability.md` §2.3 がすでに明示している。full migration contract でも同じ理由が成り立つため、hybrid は reopen しない。

### Denominator / match rate / mismatch rate

`v3x_bridge_ci_contracts.md` §6 が full scope baseline の分母を provisional rule として full migration ADR に留保していた点について、本 ADR はその留保をここで解消し、full-scope `verdict_match_rate` / `verdict_mismatch_rate` / `coverage_drift_rate` / `applicability_drift_rate` の分母を以下のとおり最終凍結する。

| metric | denominator | rationale |
|---|---|---|
| verdict_match_rate | FULL_VERDICT_COMPARABLE subset | 全 compounds を分母にすると coverage / applicability の欠落が verdict mismatch に混入し原因帰属が壊れる |
| verdict_mismatch_rate | FULL_VERDICT_COMPARABLE subset | 同上 |
| coverage_drift_rate | 全 compounds | coverage は母集団全体に対する割合として意味を持つ |
| applicability_drift_rate | 全 compounds | 同上 |

これは Path-only の COMPONENT_VERDICT_COMPARABLE subset 分母と同型である。threshold 自体は bridge_ci_contracts の provisional baseline を継承し、full scope では初期値 95% を baseline とするが、将来の ADR revision で empirical drift data に基づき調整可能とする。

---

## Operator-facing / CI separation

### Operator surface freeze

operator-facing surface は current freeze を維持する。

- rc2 verdict が primary
- v3 shadow content が secondary
- `[exploratory]` 可視化
- `semantic_policy_version` 常時表示
- mixed aggregate summary の禁止
- Cap / Catalytic materialization の非-comparability 明示

full migration 後も、semantic-policy 跨ぎの silent commingling は禁止。

### CI promotion gate

required CI への promotion は operator claim とは別 gate である。exploratory job が required candidate になるには以下の全条件を要する（`v3x_bridge_ci_contracts.md` ADR-V3-06 §4–§5 by reference）。

| gate | rule |
|---|---|
| PR-01 | channel formal contract ADR complete |
| PR-02 | sidecar invariant test 30 consecutive runs green |
| PR-03 | bridge baseline met; Path-only: path_component_match_rate, full scope: verdict_match_rate |
| PR-04 | metrics_drift = 0 across last 30 runs |
| PR-05 | Windows CI 30 consecutive runs green |
| PR-06 | no rc2-frozen regression on PR branch |

逆に sidecar mode 専用、contract 未完、baseline 未達、Windows 不安定のいずれかなら exploratory にとどまる（NP-01–NP-04）。

Path / Cap / Catalytic を required CI 昇格のために同時昇格させる必要はない。required gate は channel-owned である。ただし full verdict comparability claim は simultaneous input coverage を要求する。CI 昇格は channel-wise、full shadow verdict claim は SCV-wise、という二層構造になる。

---

## Replay / falsifiability contract

full migration contract では、truth-source chain completeness と replayability を「昇格条件」ではなく「claim validity 条件」として使う。各 compared channel は source label、source digest、source location kind、builder identity、projector identity、observation artifact pointer を持ち、Layer 0 / Layer 1 から reconstructable でなければならない。`generator_manifest.json` は単なる inventory ではなく re-materialization contract であり、`expected_output_digest` を介して非 materialized artifact も replay claim の対象になる。

### Hard blocks

以下はいずれも full migration claim を無効にする cross-artifact inconsistency である。

- manifest と materialized digest の不一致
- run_record が comparable を claim しているのに対応する provenance / observation が reconstruct できない
- report が verdict_match_rate 数値を表示しているのに v3_shadow_verdict が None
- output_inventory.json が sidecar authority を取り込んでいる
- missing-source behavior が silent inference になっている

### Witness drift

witness drift は comparability 阻害要因ではなく、情報提供である（`v3x_path_verdict_comparability.md` §1.5）。full migration でも同様に扱う。

---

## Alternatives considered

**Simultaneous all-channel promotion**: P6 が channel-specific blockers を別々に列挙していること、Cap / Catalytic の contract maturity が非対称であること、Path-only closure がすでに存在することと整合しない。棄却。

**Hybrid SCV mode**: cross-version composition により semantic policy の意味が曖昧になり、verdict-level comparison が実質 Path component comparison の言い換えに堕ちる。棄却。

**Cap / Catalytic materialization = comparability**: operator safety を破り、current display freeze に反する。Cap には pre-pose deterministic partition と pocket-dependent reality の緊張が指摘されており、formal contract なしの昇格は不適切。棄却。

---

## Consequences

The migration path remains intentionally conservative. The current `path_and_catalytic_partial` scope is maintained without collapsing component-level comparability into verdict-level comparability. Cap remains materialized-but-not-comparable, and Catalytic remains mixed: `catalytic_rule3a` is publicly comparable while Rule3B stays v3-only. Full verdict comparability therefore remains a later unlock, which prevents verdict-level metrics from being backfilled by weaker component-level claims.

artifact governance が強くなり、promotion コストの中心が code より contract へ移る。これは SoT の「semantic delta を coding 前に書く」「affected artifact と replay contract を先に列挙する」という entry rule に整合する。

---

## Open questions / UNKNOWN

| topic | status | resolution path |
|---|---|---|
| Cap → SCV component mapping | **N/A** | Cap has no rc2 SCV component equivalent; v3-only evidence |
| Catalytic (Rule3A) → scv_anchoring mapping | **FROZEN** | projector deterministic; semantic narrowing fixed; public bridge inclusion still separate |
| scv_offtarget の v3 source | **FROZEN** | Option B selected: thin OffTarget channel wrapper over read-only `core_compounds` snapshot |
| Cap formal contract | **closed** | ADR-V3-03 (WP-1) |
| Catalytic formal contract | **closed** | ADR-V3-04 (WP-1) |
| verdict_record.json authority 移行 | **migration conditions defined** | WP-2: Phase M-0 → M-1 → M-2 |
| RunDriftReport canonical filename | **frozen** | WP-2: `run_drift_report.json` |
| comparator_scope enum の将来拡張 | UNKNOWN | full bridge state で判断 |

---

## Normative tables

### Artifact authority table

| artifact / surface | layer | role | authority status | decision |
|---|---|---|---|---|
| `semantic_policy_version.json` | 0 | policy identity | canonical | canonical Layer 0 |
| `sidecar_run_record.json` | 0 | sidecar state / comparator status / backward-compatible mirror | non-canonical current | current full-migration mirror record |
| `generator_manifest.json` | 0 | sidecar inventory + re-materialization contract | canonical | canonical full-migration boundary member |
| `rc2_bridge_pointers.json` | 0 | retained rc2 artifact pointers | optional current | required for full bridge mode, else equivalent refs must exist in Layer 0 |
| `output_inventory.json` | rc2 | rc2 inventory authority | canonical rc2 | unchanged, outside v3 sidecar authority |
| `verdict_record.json` | 0 | canonical full verdict record | canonical current | current Layer 0 authority after ADR-V3-11 |
| `observation_bundle.json` | 1 | serialized SCVObservationBundle | Layer 1-class (§D.1 implementation note) | required for full verdict claim if materialized as canonical carrier; otherwise reconstructable equivalent must be specified |
| `channel_evidence_path.jsonl` | 1 | detailed path evidence | Layer 1 | required when path is comparable |
| `channel_evidence_cap.jsonl` | 1 | detailed cap evidence | Layer 1 | required when cap is materialized; v3-only evidence (not comparable) |
| `channel_evidence_catalytic.jsonl` | 1 | detailed catalytic evidence | Layer 1 | required when catalytic is comparable |
| `builder_provenance.json` | 1 | truth-source chain record | Layer 1 | required for every compared channel |
| `run_drift_report.json` | 1 | machine-readable run-level drift report | canonical filename frozen (WP-2) | required for promotion decisions |
| `bridge_operator_summary.md` | operator | explanatory rendering | secondary only | never authority |
| eval_report / qc_report v3 sections | operator | explanatory rendering | secondary only | never authority; must display [exploratory] until full promotion |

### Channel promotion table

| channel | current status | minimum promotion conditions | comparator inclusion rule | blocker status |
|---|---|---|---|---|
| path | comparable | rc2 source inventory frozen; adapter coverage frozen; missing behavior frozen; projector fields preserved; deterministic tests; final component comparability semantics defined | already included in current `["path", "catalytic"]` partial scope | current scope closed |
| cap | materialized-but-not-comparable | formal contract (ADR-V3-03) complete; applicability semantics frozen; drift schema frozen; deterministic tests green | **not eligible for comparable_channels** — no rc2 SCV component mapping exists; may appear only as `[v3-only]` evidence | closed for non-comparable bridge presence; comparable participation is N/A |
| catalytic | partially comparable under mixed representation | formal contract (ADR-V3-04) complete; Rule3A → scv_anchoring mapping FROZEN; Rule 3 anchoring vs disruption split validated; proposal-connected Rule 3 still forbidden | current public comparable participation is limited to `catalytic_rule3a`; Rule3B disruption remains v3-only evidence | current partial comparable scope landed; stronger claim remains open |
| all channels collectively | partial coverage landed; operator verdict-level activation not landed | all-required-SCV-input coverage, denominator readiness, activation decision, and promotion decision remain separately gated | required for full verdict comparability only at SCV gate | open |

### Full-SCV input coverage table

| SCV component (rc2) | v3 source | status | full-migration requirement |
|---|---|---|---|
| scv_pat | Path channel via PathChannelProjector | **FROZEN** | keep frozen and replay-safe |
| scv_anchoring | Catalytic (Rule3A) via CatalyticChannelProjector | **FROZEN** | keep deterministic; semantic narrowing remains documented, not silently normalized away |
| scv_offtarget | thin OffTarget channel wrapper via read-only `core_compounds` snapshot | **FROZEN** | Option B fixed; no hybrid borrowing |
| all required components present | yes at mapping/source layer | internally coverable and denominator-prepared after RP-2, but still not operator-activated in public rendering | full verdict publication remains separately gated |
| hybrid borrowing from rc2 | conceptually possible | rejected | forbidden |

### Operator / CI promotion gate table

| gate ID | rule | result if unmet |
|---|---|---|
| PR-01 | channel formal contract ADR complete | remain exploratory |
| PR-02 | sidecar invariant test 30 consecutive runs green | remain exploratory |
| PR-03 | bridge baseline met; Path-only: path_component_match_rate, full scope: verdict_match_rate | remain exploratory |
| PR-04 | metrics_drift = 0 across last 30 runs | remain exploratory |
| PR-05 | Windows CI 30 consecutive runs green | remain exploratory |
| PR-06 | no rc2-frozen regression on PR branch | remain exploratory |
| full verdict claim gate | VN-01–VN-06 all satisfied | when unmet: v3_shadow_verdict remains None, verdict_match_rate remains N/A |
| operator display gate | semantic_policy_version shown, [exploratory] shown, rc2 primary / v3 secondary preserved | when unmet: block any rendering change that would weaken these guards |

### Blocker / exit criteria table

| category | hard blocker | exit criterion |
|---|---|---|
| authority | output_inventory.json changed for v3 sidecar, or verdict_record.json treated as current authority | rc2 inventory untouched; Layer 0 authority explicit |
| source chain | missing source digest / location / builder / projector / observation pointer | reconstructable truth-source chain for every compared channel |
| applicability | channel conflates DISABLED / APPLICABILITY_ONLY / OBSERVATION_MATERIALIZED, or treats NOT_COMPARABLE as primary state rather than derived status | three primary lifecycle states frozen at builder level; NOT_COMPARABLE derived from comparable_channels membership at report level |
| mapping | any SCV component lacks frozen v3 mapping | channel-to-SCV-component mapping complete |
| replay | expected_output_digest unstable or non-reconstructable | replay checker green for all boundary artifacts |
| drift | deterministic metrics_drift present | metrics drift remains zero at baseline window |
| operator safety | mixed summary, Cap/Catalytic shown as full comparability, silent policy commingling | display rules hold in reports |
| CI safety | exploratory lane promoted without PR-01–06 | required promotion explicit and gated |

---

## Acceptance criteria

この ADR が閉じたと見なせる条件は三つである。

1. **Authority conflict がない**: current Path-only scope と本 ADR の判断が矛盾せず、authority 文書間で二重定義が存在しない
2. **Current partial-scope meaning を壊さない**: `comparable_channels == ["path", "catalytic"]`、comparable component participation remains limited to `path` and `catalytic_rule3a`、`v3_shadow_verdict = None`、`verdict_match_rate = N/A` が維持される
3. **UNKNOWN が unauthorized implementation で埋められていない**: 未定義の channel-to-SCV-component mapping、Cap/Catalytic formal contract、verdict_record.json migration schema が convenience code で先取りされていない

## Regression invariants

以下の項目を regression で監視する。各項目は上記 acceptance criteria のいずれかに対応する。

| regression invariant | acceptance criterion |
|---|---|
| `output_inventory.json` unchanged | authority conflict なし |
| `v3_shadow_verdict` inactive in current scope | authority conflict なし |
| `verdict_match_rate` non-numeric / `N/A` on the operator surface | authority conflict なし |
| Cap rendered as non-comparable and Rule3B rendered as `[v3-only]` | authority conflict なし |
| `comparable_channels == ["path", "catalytic"]` | current partial-scope meaning preserved |
| `component_matches` admits `path` and `catalytic_rule3a` only | current partial-scope meaning preserved |
| component-level metrics remain separate from verdict-level metrics | current partial-scope meaning preserved |
| no inferred missing fields | UNKNOWN not collapsed |
| no Cap/Catalytic full-comparability rendering | UNKNOWN not collapsed |
| no unmapped channel-to-SCV-component claim | UNKNOWN not collapsed |
| `metrics_drift = 0` | Path-only meaning preserved |
| `goal_precheck` failure → run-level applicability separation | Path-only meaning preserved |

---

## Implementation handoff

### Work packages

| WP | kind | content | status / dependency |
|---|---|---|---|
| WP-1 | docs-only | Cap / Catalytic formal contract ADR + channel-to-SCV-component mapping freeze | landed |
| WP-2 | artifact/schema-only | verdict_record.json authority migration conditions + RunDriftReport canonical filename | landed |
| WP-3 | validation-only | full-SCV input coverage checker, cross-artifact consistency checker, operator display guard | landed |
| WP-4 | bridge-only | full-scope denominator prep and FULL_VERDICT_COMPARABLE-ready aggregation semantics | landed as readiness prep; operator-facing verdict activation remains separate |
| WP-5 | CI-only / policy | exploratory → required promotion gate automation | pending explicit RP-3 promotion decision |
| RP-3A | docs-only human decision | operator-facing `v3_shadow_verdict` / numeric verdict-metric activation surfaces | next |
| RP-3B | docs-only human decision | required-promotion decision surface | next |

順序は semantic delta 混入防止のため contract-before-code とする。WP-3 は validation code であり、WP-1（contract ADR freeze）および WP-2（schema / artifact naming freeze）の完了を前提とする。WP-4 と WP-5 も同様に WP-1 + WP-2 + WP-3 を前提とし、contract-before-code を破らない。

### Priority

先にやるべき: WP-1, WP-2  
後回しにすべき: operator surface の見栄え改善、new enum 追加、diagnostic field の public 昇格、taxonomy redesign（full migration contract が閉じる前に触ると semantic delta が cleanup / convenience に偽装されやすい）

### Audit points

以下のいずれかが起きたら semantic delta 混入として block する。

- path_component_match_rate を verdict_match_rate の別名として扱っている
- Cap / Catalytic materialization を comparability と誤読させている
- v3_shadow_verdict を current scope に逆流させている
- output_inventory.json を拡張している
- missing field を推測値で埋めている
- diagnostic を final semantic field へ昇格させている

---

## Additional evidence required before implementation

- Cap formal contract ADR (ADR-V3-03)
- Catalytic formal contract ADR (ADR-V3-04)
- full channel-to-SCV-component mapping freeze
- verdict_record.json authority migration ADR
- 30 run の sidecar invariant / metrics drift / Windows CI history

Path については current scope で必要条件を満たしているが、それは full verdict comparability の十分条件ではない。

---

*End of ADR*
