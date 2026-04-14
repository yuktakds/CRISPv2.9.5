# v3 RP-5 Release-Blocking Gate Consolidation Plan

Status: design-only  
Date: 2026-04-13  
Parent: `v3_current_boundary.md`, `v3_rp4_operator_surface_materialization_plan.md`, `v3_rp3_activation_decision_surface.md`, `v3_rp3_promotion_decision_surface.md`  
Scope: RP-5 は forbidden state を run failure / release block まで昇格し、CI / runner / artifact writer の failure semantics を統一する。boundary は動かさない。

---

## Purpose

RP-4 は「表示されるべきでないものを suppress する」ことを operator surface level で保証した。RP-5 はその保証を release path 全体に押し上げる。

RP-5 の責務は「不正な状態なら成果物生成・昇格・required candidacy を止める」ことであり、「新しい値を表示する」ことではない。forbidden surface violation、cross-artifact inconsistency、unauthorized promotion を、report suppression ではなく run failure / release block として扱うことで、operator surface だけでなく artifact output と CI promotion の両方で危険経路を封じる。

---

## What RP-5 May Authorize

RP-5 は、以下を authorize する。

1. `operator_surface_state.json`（RP-4 で導入した `ActivationPromotionState` の materialized carrier）を runner 終了判定の single-source diagnostics input として使用すること
2. forbidden surface violation / cross-artifact inconsistency を run failure まで昇格すること
3. promotion candidacy を advisory と blocking に分離し、required 化された lane のみが merge / release を止めるようにすること
4. CI / runner / artifact writer の failure exit code を統一すること

---

## What RP-5 Does Not Authorize

- `comparator_scope` の変更
- `comparable_channels` の変更
- Cap の `comparable_channels` 参加
- Rule3B の `component_matches` 参加
- authority layering 変更
- `output_inventory.json` の変更
- `v3_shadow_verdict` / `verdict_match_rate` の activation（RP-3 decision に従う）
- operator rendering rule の変更（RP-4 contract に従う）
- mixed rc2/v3 aggregate summary の生成
- `[exploratory]` label の除去
- full migration closure

RP-5 は failure semantics の統一であり、新しい success path を追加しない。

---

## Failure Semantics

### RP-4 との違い

RP-4 は forbidden state を「rendering suppression + suppression reason 記録」として処理した。RP-5 は同じ forbidden state を「run-level failure」として扱う。

| forbidden state | RP-4 behavior | RP-5 behavior |
|---|---|---|
| numeric verdict rates + v3_shadow_verdict inactive | suppress rendering, record reason | **run failure** |
| `catalytic_rule3b` in `component_matches` | suppress rendering, record reason | **run failure** |
| `cap` in `comparable_channels` | suppress rendering, record reason | **run failure** |
| mixed rc2/v3 aggregate summary | suppress rendering, record reason | **run failure** |
| unauthorized promotion gate ID | suppress rendering, record reason | **run failure** |
| `[exploratory]` label absent on v3 section | suppress rendering, record reason | **run failure** |
| cross-artifact field mismatch (verdict_record ↔ sidecar_run_record) | hard block rendering | **run failure** |
| Layer 0 field absent (null ではなく missing) | validator reject | **run failure** |

### Must-present field inventory

Layer 0 artifact（`verdict_record.json` / `sidecar_run_record.json`）において、以下の field は must-present である。値が suppressed 状態でも field 自体は JSON object に存在し、明示的 `null` を持たなければならない。field が JSON key として missing の場合は exit code 1。

| field | suppressed 時の値 | active 時の値 |
|---|---|---|
| `v3_shadow_verdict` | `null` | `"PASS"` / `"FAIL"` / `"UNCLEAR"` |
| `verdict_match_rate` | `null` | numeric |
| `verdict_mismatch_rate` | `null` | numeric |
| `full_verdict_computable` | `false` | `true` |
| `full_verdict_comparable_count` | `0` | numeric |
| `comparator_scope` | 現行 scope 文字列 | 同左 |
| `comparable_channels` | 現行 channel list | 同左 |
| `v3_only_evidence_channels` | 現行 v3-only list | 同左 |
| `channel_lifecycle_states` | 現行 lifecycle dict | 同左 |
| `authority_transfer_complete` | `true` / `false` | 同左 |
| `path_component_match_rate` | `null` | numeric |

serializer 実装差による false positive を防ぐため、validator は上記 field の key 存在を JSON level で検証し、Python の `None` と JSON の key absence を区別する。

RP-5 が追加するのは failure 昇格であり、RP-4 の suppression logic を置き換えるのではない。suppression は引き続き first line of defense として機能し、RP-5 はその背後に second line として run failure を置く。

### Failure vs suppression の関係

```text
forbidden state detected
  → RP-4 suppression: rendering を止め、reason を記録する
  → RP-5 failure: run exit code を non-zero にし、artifact writer を中断する
```

suppression は「問題があるが partial output は残す」。failure は「問題があるので output 自体を不完全として扱う」。RP-5 は後者を追加する。

---

## Runner Exit Semantics

### Single-source diagnostics input

runner の終了判定は `ActivationPromotionState`（RP-4 §Machine-Readable で定義）を single-source input として使う。runner が独自に forbidden state を再判定することは禁止する。判定ロジックは `rp3_activation.check_forbidden_surfaces` に一元化済みであり、runner はその結果を読むだけ。

### Exit code 分類

| exit condition | exit code | meaning |
|---|---|---|
| clean run, no forbidden state | 0 | 正常完了 |
| forbidden surface detected | 1 | 不正状態で成果物が不完全。forbidden state の詳細は `operator_surface_state.json` に記録済み |
| cross-artifact inconsistency detected | 1 | 同上 |
| rc2 sidecar 自体の computation error | 2 | v3 gate とは無関係な実行エラー |

exit code 1 は「v3 gate violation による中断」を意味し、rc2 verdict path 自体は正常に完了している場合でも発火しうる。rc2 output は exit code 1 でも valid であり、v3 sidecar output のみが不完全として扱われる。

### Artifact writer 中断

exit code 1 の場合、以下の artifact writer 動作を行う。

- `verdict_record.json` は書き出すが、forbidden state に対応する field は null のままとする
- `sidecar_run_record.json` は verdict_record.json と同期して書き出す
- `operator_surface_state.json` は suppression_reasons / failed_gate_ids を含めて完全に書き出す（これが failure の diagnostic record）
- `run_drift_report.json` は書き出すが、ActivationPromotionState の `suppression_reasons` が non-empty であることを記録する
- `generator_manifest.json` への登録は行う（replay 可能性を維持するため）
- `bridge_operator_summary.md` は **suppressed marker 付きで書き出す**（下記参照）

rc2 artifact（`output_inventory.json` 含む）は一切影響を受けない。

### bridge_operator_summary.md の exit-1 振る舞い

exit code 1 時に bridge summary を「書かない」と「annotated 版を書く」の二択がある。本文書は後者を採る。理由は、summary を absent にすると `generator_manifest.json` 側で expected absent を許容する特殊処理が必要になり、replay contract が揺れるためである。

exit code 1 時の bridge summary は以下を満たす。

- ファイル先頭に `<!-- SUPPRESSED: v3 gate violation -->` marker を入れる
- 本文には suppression reason の列挙のみを記載し、verdict / match rate の数値は一切含めない
- `generator_manifest.json` には通常どおり登録し、`expected_output_digest` を記録する
- replay checker は suppressed marker 付き summary を valid artifact として扱う

---

## CI Blocking Semantics

### LanePromotionStatus shape

RP-4 で導入した `LanePromotionStatus` の shape を本文書でも固定する。implementation 時の field 名揺れを防ぐため、ここで canonical field set を再確認する。

```python
@dataclass(frozen=True, slots=True)
class LanePromotionStatus:
    """一つの CI lane / validator に対する promotion gate 判定結果"""
    lane_id: str                    # CI job 名 or validator 名
    passed: bool                    # 全 gate 通過なら true
    failed_gate_ids: tuple[str, ...]  # 未通過の gate ID（例: ("PR-02", "PR-05")）
    authority_reference: str        # gate 定義元（例: "adr_v3_10 §CI promotion gate"）
    promotion_status: str           # "advisory" or "blocking"
```

`promotion_status` field は RP-5 で追加する。advisory / blocking の区別を machine-readable に持たせることで、CI 側が lane ごとに failure behavior を判定できる。

### Advisory vs blocking promotion

RP-3 promotion decision surface は「exact job / validator / gate」の promotion を per-lane で扱う。RP-5 はこれを advisory と blocking に分離する。

| status | meaning | CI effect |
|---|---|---|
| advisory | promotion candidacy は report されるが merge / release を止めない | CI job は green / red を report するが required matrix に入らない |
| blocking | required 化された lane は merge / release を止める | CI job は required matrix に入り、failure は merge block |

advisory → blocking への昇格は RP-3 promotion decision の explicit human decision を要する。RP-5 は昇格判定を行わず、判定結果に従って CI の failure behavior を配線するだけ。

### Required lane の failure behavior

required 化された lane が failure した場合の behavior は以下に固定する。

- CI job は red を返す
- merge は block される
- rc2-frozen suite の required job は影響を受けない（v3 lane の failure は v3 lane だけで閉じる）
- failure reason は `LanePromotionStatus.failed_gate_ids` から machine-readable に取得可能

### Required 化されていない lane

advisory lane の failure は merge を block しない。report に `[advisory]` として表示される。advisory lane が安定して green であることは promotion candidacy の evidence になるが、promotion 自体は authorize しない。

---

## Cross-Artifact Consistency Enforcement

RP-4 §Cross-Artifact Alignment の 5 対の整合 rule を、RP-5 では run failure まで昇格する。

| artifact pair | RP-4 action | RP-5 action |
|---|---|---|
| `verdict_record.json` ↔ `sidecar_run_record.json` | hard block rendering | **run failure (exit 1)** |
| `verdict_record.json` ↔ operator summary | hard block rendering | **run failure (exit 1)** |
| `run_drift_report.json` ↔ operator summary | hard block rendering | **run failure (exit 1)** |
| `generator_manifest.json` ↔ `run_drift_report.json` | hard block rendering | **run failure (exit 1)** |
| operator summary ↔ `[exploratory]` label | hard block rendering | **run failure (exit 1)** |

加えて、RP-5 は以下の consistency check を追加する。

| check | violation action |
|---|---|
| `operator_surface_state.json` が `generator_manifest.json` に登録されていない | run failure |
| `operator_surface_state.json` の `expected_output_digest` が manifest と不一致 | run failure |
| `LanePromotionStatus.authority_reference` が `adr_v3_10 §CI promotion gate` を指さない | run failure |
| `LanePromotionStatus.failed_gate_ids` に PR-01..PR-06 以外の ID が含まれる | run failure |

---

## `operator_surface_state.json` の位置づけ

RP-4 は `ActivationPromotionState` を `run_drift_report.json` の section として定義した。RP-5 はこれを独立 artifact `operator_surface_state.json` として materialization し、runner 終了判定の single-source input とする。

| property | value |
|---|---|
| filename | `operator_surface_state.json` |
| layer | Layer 1 |
| content | `ActivationPromotionState` + `LanePromotionStatus[]` の JSON serialization |
| generation | 毎 run 必ず materialization（suppressed state でも書き出す） |
| manifest 登録 | 必須。`expected_output_digest` を `generator_manifest.json` に記録 |
| runner 参照 | runner exit 判定の single-source diagnostics input |

`run_drift_report.json` にも同一 section を保持してよいが、runner exit 判定に使う canonical source は `operator_surface_state.json` とする。

---

## Rollback / Freeze-Back

RP-5 の failure 昇格が不安定を引き起こした場合、freeze-back は以下のとおり。

- run failure を RP-4 の suppression-only に戻す（exit code 1 → exit code 0 + suppression reason 記録）
- required lane を advisory に demote する
- `operator_surface_state.json` の materialization は継続する（diagnostic 価値があるため）
- rc2 artifact / rc2 exit code は不変
- boundary / scope / authority は不変

freeze-back は explicit decision で行い、自動化しない。freeze-back の判断基準は「RP-5 failure 昇格により rc2 production 運用が阻害されているか」であり、v3 sidecar 内部の failure は freeze-back の必要条件ではない。

---

## Still Out of Scope

- Cap comparable 参加
- Rule3B comparable 昇格
- `comparator_scope` の変更
- `comparable_channels` の変更
- authority layering 変更
- `output_inventory.json` 変更
- `v3_shadow_verdict` / `verdict_match_rate` の activation 条件変更
- operator rendering rule の変更
- full migration closure
- `[exploratory]` label の除去
- mixed rc2/v3 aggregate summary
- stale / archived 文書の authority 復帰
- rc2-frozen suite の required matrix 変更

---

*End of document*
