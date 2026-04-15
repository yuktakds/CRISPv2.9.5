# Design Note: `comparable_channels` 語義の確定

Status: accepted  
Date: 2026-04-09  
Parent: `adr_v3_10_full_migration_contract.md`, `wp1_wp2_channel_contracts_schema_freeze.md`  
Scope: `comparable_channels` の語義を一点だけ確定する。WP-3 実装前 gate。

---

## Problem

WP-1 は Cap を「rc2 に相当する独立 sensor がない」「bridge comparison では v3-only evidence として扱う」と定義した。しかし ADR-V3-10 の channel promotion table は Cap が将来 `comparable_channels` に入りうる書き方を残している。

`comparable_channels` が以下のどちらを指すかが未固定である。

- **(A)** rc2 SCV component に FROZEN mapping を持つ channel のみ
- **(B)** bridge report に正式に登場してよい channel 全体（v3-only evidence を含む）

語義が未固定のまま WP-3（validator / operator display guard）に入ると、`component_matches`、`FULL_VERDICT_COMPARABLE`、`verdict_match_rate` との関係が実装ごとに揺れる。

---

## Decision

**`comparable_channels` は (A) を採る。rc2 SCV component に対して FROZEN mapping を持つ channel のみを指す。**

したがって:

| channel / sub-evidence | rc2 mapping status | current public comparable status | note |
|---|---|---|---|
| Path | scv_pat — FROZEN | **yes**（current） | current partial comparator scope |
| Catalytic Rule3A | scv_anchoring — **FROZEN** | **yes**（current） | public comparable via `catalytic` under the mixed representation contract; `component_matches` key remains `catalytic_rule3a` |
| Cap | rc2 対応 component なし | **no** | v3-only evidence |
| Catalytic Rule3B | rc2 対応 component なし | **no** | v3-only evidence retained inside the mixed catalytic representation |

注記: Catalytic のうち rc2-mappable なのは Rule3A のみであり、Rule3B disruption は引き続き v3-only evidence として扱う。したがって public widening の対象は channel 全体の materialization ではなく、Rule3A comparable representation の明示的凍結を前提とする。

Canonical invariant: `catalytic` が `comparable_channels` に入る場合、`component_matches` に現れるのは **`catalytic_rule3a` のみ**であり、Rule3B は v3-only evidence として `component_matches` に出現しない。

---

## v3-only evidence の扱い

Cap engagement/mobility および Catalytic Rule3B disruption は `comparable_channels` には入らないが、bridge report に登場してよい。これらは `reported_channels` ではなく、drift report 内の **v3-only evidence section** として扱う。

NOT_COMPARABLE は `ChannelLifecycleState` の primary enum 値ではなく、`channel_lifecycle_state == OBSERVATION_MATERIALIZED AND channel ∉ comparable_channels` から導出される report-level status である（ADR-V3-10 §channel lifecycle state 参照）。

具体的には:

- `RunDriftReport` の compound record に v3-only evidence の存在 / 不在を記録してよい
- operator summary に `[v3-only]` ラベル付きで表示してよい
- ただし `component_matches` には含めない
- `COMPONENT_VERDICT_COMPARABLE` / `FULL_VERDICT_COMPARABLE` の判定に影響しない
- `path_component_match_rate` / `verdict_match_rate` の分子・分母に含めない

将来、rc2 SCV formula が拡張されるか、v3 SCV が独自 formula を採用する場合は、別途 ADR で `comparable_channels` の語義を再検討してよい。現段階では新概念（`reported_channels` 等）を追加しない。

---

## sidecar_run_record.json への反映

`sidecar_run_record.json` の `comparable_channels` field は rc2-mappable channel のみを列挙する。v3-only evidence の存在は別 field で記録する。

```python
# sidecar_run_record.json の関連 field
comparable_channels: ["path", "catalytic"]     # rc2-mappable FROZEN channel のみ
v3_only_evidence_channels: ["cap"]             # channel-level v3-only evidence
channel_lifecycle_states: {                    # primary lifecycle state（3 値）
    "path": "OBSERVATION_MATERIALIZED",
    "cap": "OBSERVATION_MATERIALIZED",
    "catalytic": "OBSERVATION_MATERIALIZED",
}
# comparable component participation remains narrower than channel materialization:
#   `catalytic` participates publicly only through `catalytic_rule3a`
#   `catalytic_rule3b` remains v3-only evidence and must not appear in component_matches
# NOT_COMPARABLE は primary enum ではなく derived status:
#   channel_lifecycle_state == OBSERVATION_MATERIALIZED
#   AND channel ∉ comparable_channels
# よって cap は report level で NOT_COMPARABLE と表示される

```

---

## WP-3 への影響

この語義確定により、WP-3 の validator は以下を検証すればよい。

| validation rule | 根拠 |
|---|---|
| `comparable_channels` の全要素が FROZEN mapping を持つ | 本 design note |
| v3-only evidence channel が `comparable_channels` に混入していない | 本 design note |
| v3-only evidence が `component_matches` に含まれていない | 本 design note |
| v3-only evidence が match rate の分子・分母に含まれていない | 本 design note |
| operator summary で v3-only evidence に `[v3-only]` が付いている | ADR-V3-10 operator display gate |

---

## What this note closes

`comparable_channels` は rc2-mappable FROZEN channel のみを指す。current state では `path` と `catalytic` が参加しうるが、`catalytic` の comparable component participation は `catalytic_rule3a` に限定される。Cap は参加不可。

## What this note does not close

将来の `reported_channels` 概念の要否。v3 SCV 独自 formula 採用時の語義再検討。

---

*End of design note*
