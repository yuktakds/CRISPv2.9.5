# v3 Catalytic Public Representation Freeze

Status: accepted  
Date: 2026-04-09  
Parent: `comparable_channels_semantics.md`, `v3_reopen_path_decision_frame.md`, `v3_reopen_path_implementation_plan.md`  
Scope: RP-0. Catalytic の mixed comparable / v3-only representation を docs-only で凍結する。public widening そのものは authorize しない。

---

## Decision

Catalytic の public representation は、将来 widening が別 decision で承認された場合でも、**channel 全体を一様 comparable とみなさない mixed representation** を採る。

- `comparable_channels` に参加しうるのは Catalytic Rule3A のみ
- Rule3A の public comparable surface は `catalytic_rule3a` component として表現する
- Rule3B disruption は引き続き `[v3-only]` evidence として分離する
- Cap と同様に、Rule3B は `component_matches` や match-rate 分子・分母には入れない

この freeze は representation contract の定義であり、current keep-path scope を変更しない。

---

## Current Boundary

current public scope は不変である。see `v3_current_boundary.md`。

この文書は、将来の widening が起きたときの Catalytic 表現だけを先に固定する。

---

## Mixed Representation Contract

### 1. Channel-level meaning

将来 `catalytic` が `comparable_channels` に入る場合でも、その意味は
「Catalytic channel 全体が comparable」ではなく、
「Catalytic のうち Rule3A comparable surface を public comparable として扱う」
である。

### 2. Comparable surface

public comparable surface は次に固定する。

- channel name: `catalytic`
- comparable component key: `catalytic_rule3a`
- comparable payload focus: Rule3A anchoring projection
- primary comparable metric anchor: `best_target_distance`

### 3. v3-only surface

Rule3B disruption は次に固定する。

- stays outside `component_matches`
- stays outside comparable drift lists
- stays outside `COMPONENT_VERDICT_COMPARABLE`
- stays outside `FULL_VERDICT_COMPARABLE`
- stays outside `verdict_match_rate`
- stays in a `[v3-only]` section only

---

## Applicability Contract

Catalytic public comparable applicability は次に固定する。

- `evidence_core` missing / unreadable: APPLICABILITY_ONLY
- projector input incomplete for Rule3A: APPLICABILITY_ONLY
- APPLICABILITY_ONLY の場合、`component_matches["catalytic_rule3a"]` は `null`
- APPLICABILITY_ONLY は mismatch ではない

Rule3B は applicability-only / observational で materialize されてよいが、public comparable 判定には入らない。

---

## Drift Contract

Catalytic Rule3A public drift は、Path と同じ aggregate に雑に混ぜず、`catalytic_rule3a` component drift として扱う。

最低限、次を分離する。

- coverage drift
- applicability drift
- metrics drift
- witness / attribution drift

semantic narrowing gap は別扱いにする。

- motif-based semantics と warhead-atom distance projection の差は expected deviation として documented する
- default で must-match metrics とみなさない
- tolerance / threshold の exact numeric freeze は将来 empirical calibration に委ねてよい

---

## Operator Surface Contract

将来 widening が承認された場合の operator rendering は次に固定する。

- Catalytic section 全体は `[exploratory]` を維持する
- Rule3A comparable surface は `catalytic_rule3a` として表示する
- Rule3B disruption は `[v3-only]` と明示して別 section に表示する
- Rule3B は full verdict comparability を示唆してはならない

forbidden:

- Rule3B を `component_matches` に表示する
- Rule3B を numeric match-rate の説明に混ぜる
- Catalytic channel 全体を “fully comparable” と表現する

---

## What This Freeze Authorizes

- Catalytic mixed representation の docs-only contract
- Rule3A comparable / Rule3B v3-only の境界定義

RP-1 の human widening decision + code は、この freeze と RP-0.5 scope atomics 定義の後にのみ着手できる。

---

*End of document*
