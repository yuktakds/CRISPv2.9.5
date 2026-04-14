# v3 RP-4 Operator Surface Materialization Plan

Status: closed  
Date: 2026-04-14  
Parent: `v3_current_boundary.md`, `v3_rp3_activation_decision_surface.md`, `v3_rp3_promotion_decision_surface.md`  
Scope: RP-4 は operator-facing rendering と machine-readable hardening を gate-aware にする。boundary は動かさない。

---

## Purpose

RP-4 は RP-3 で実装した activation / promotion gate を actual operator surface と machine-readable reports に接続する段である。実装は landed しており、RP-5 はこの結果を読むだけで failure semantics を昇格した。

RP-3 は kernel（判定関数・guard ロジック）を実装した。RP-4 はその kernel を report builder / summary builder / artifact writer に配線し、「表示されるべきでないものが出ない」ことを surface level まで保証する。

RP-4 は rendering / hardening であり、boundary change ではない。

The canonical current boundary is defined in `v3_current_boundary.md`. This document records how RP-4 materialized gate-aware rendering under that boundary; it does not restate the boundary as a second normative source.

## Closed State

RP-4 で landed した内容は次のとおり。

- operator-facing bridge summary が activation / promotion gate-aware になった
- `[exploratory]` と rc2 primary / v3 secondary 表示が維持された
- `operator_surface_state.json` が machine-readable carrier として追加された
- `sidecar_run_record.json.bridge_diagnostics.operator_surface_state` に同 state が mirrored され、suppression reason と promotion gate result を監査できるようになった

RP-4 は stronger claim を増やしていない。`v3_shadow_verdict` と numeric verdict rates は current partial scope では inactive / suppressed のままであり、component metrics は verdict proxy に再解釈されない。

---

## What RP-4 May Authorize

RP-4 は、RP-3 の accepted activation / promotion decision が runtime gate を満たした場合に限り、以下を authorize する。

1. `bridge_operator_summary.md`、`eval_report`、`qc_report` に対する guarded rendering の接続
2. `run_drift_report.json` 等 machine-readable artifact への activation / promotion state の明示記録
3. activation / promotion decision が accepted でも runtime gate unmet なら表示しない / hard block する cross-artifact hardening

---

## What RP-4 Does Not Authorize

- `comparator_scope` の変更
- `comparable_channels` の変更
- Cap の `comparable_channels` 参加
- Rule3B の `component_matches` 参加
- authority layering 変更（Layer 0 / Layer 1 の役割変更）
- `output_inventory.json` の変更
- full migration closure
- mixed rc2/v3 aggregate summary の生成
- `[exploratory]` label の除去

RP-4 は rendering の on/off を gate に従って接続するだけであり、gate 自体の条件を緩和しない。

---

## Surface Inventory

RP-4 が touch する surface と、各 surface の rendering rule を以下に固定する。

### Operator-facing documents

| surface | rendering rule | gate function |
|---|---|---|
| `bridge_operator_summary.md` の v3_shadow_verdict section | `may_render_v3_shadow_verdict()` が true のときのみ render | `rp3_activation.may_render_v3_shadow_verdict` |
| `bridge_operator_summary.md` の verdict_match_rate section | `may_render_numeric_verdict_rates()` が true のときのみ render | `rp3_activation.may_render_numeric_verdict_rates` |
| `eval_report` の v3 shadow section | 同上 | 同上 |
| `qc_report` の v3 shadow section | 同上 | 同上 |
| `catalytic_rule3a` component display | comparable component として表示可。`[exploratory]` label 維持 | `comparable_channels` membership check |
| Rule3B display | `[v3-only]` section にのみ表示。`component_matches` には出さない | forbidden leakage guard |
| Cap display | `[v3-only]` section にのみ表示 | forbidden leakage guard |
| rc2 verdict | 常に primary 表示。v3 content は secondary | 変更なし |
| `[exploratory]` label | v3 関連の全 section に維持 | 変更なし |
| mixed aggregate summary | 禁止 | forbidden surface guard |

### Machine-readable artifacts

| artifact | 追加内容 | authority layer |
|---|---|---|
| `verdict_record.json` | `v3_shadow_verdict` / `verdict_match_rate` は既存 field。suppressed 時は明示的 `null` を書く（field absent は禁止） | Layer 0 |
| `sidecar_run_record.json` | 同上（mirror。verdict_record.json と field-by-field 一致必須。同じく明示的 `null`） | Layer 0 mirror |
| `operator_surface_state.json` | activation / promotion / suppression / promotion-gate state の machine-readable carrier | Layer 1 |
| `sidecar_run_record.json` | `bridge_diagnostics.operator_surface_state` mirror を保持 | Layer 0 mirror |

### Null / absent / N/A convention

Layer 0 / Layer 1 の machine-readable artifact では、suppressed field は **field absent ではなく明示的 `null`** を使う。field が JSON object に存在しないことは schema violation として扱い、cross-artifact validator が reject する。operator summary（secondary surface）では `null` を `N/A` と表示してよい。この変換は rendering 時にのみ行い、Layer 0 / Layer 1 には `N/A` 文字列を書かない。

---

## Runtime Suppression Rules

表示判定は RP-3 kernel の関数に一元化し、report builder 側で独自判定しない。

### `v3_shadow_verdict` 表示

```text
render iff:
  activation_decision_accepted("v3_shadow_verdict") == true
  AND vn_gate.all_satisfied == true
  AND full_verdict_computable == true
otherwise:
  suppress. Layer 0 field は明示的 null のまま。operator summary では N/A と表示。
```

### numeric `verdict_match_rate` / `verdict_mismatch_rate` 表示

```text
render iff:
  activation_decision_accepted("verdict_match_rate") == true
  AND may_render_v3_shadow_verdict() == true   ← ordering dependency
  AND denominator_contract_satisfied == true
otherwise:
  suppress. Layer 0 field は明示的 null のまま。operator summary では N/A と表示。
```

### forbidden surface block

以下のいずれかが render payload に検出された場合、report 出力を hard block する。

| forbidden condition | block reason |
|---|---|
| numeric verdict rates が payload にあるのに `v3_shadow_verdict` が inactive | ordering dependency 違反 |
| `component_matches` に `catalytic_rule3b` がいる | mixed representation contract 違反 |
| `comparable_channels` に `cap` がいる | comparable_channels_semantics 違反 |
| mixed rc2/v3 aggregate summary が生成される | operator safety 違反 |
| promotion report が PR-01–PR-06 以外の独自条件を required 候補として扱う | promotion decision surface 違反。検出方法: 各 `LanePromotionStatus.authority_reference` が `adr_v3_10 §CI promotion gate` を指し、`failed_gate_ids` の全要素が `PR-01`..`PR-06` の部分集合であることを validator が確認する。authority_reference が異なるか、gate ID が PR-01..PR-06 に含まれない場合は hard block |
| operator summary が `[exploratory]` を落とす | current boundary guard 違反 |

block が発動した場合、report は出力せず、suppression reason を machine-readable に記録する。

---

## Machine-Readable Activation / Promotion State

actual implementation では、run-level の activation / promotion state は `operator_surface_state.json` に materialize され、`sidecar_run_record.json.bridge_diagnostics.operator_surface_state` に mirror される。`run_drift_report.json` は denominator / drift surface のままであり、state carrier authority には昇格していない。

```python
@dataclass(frozen=True, slots=True)
class ActivationPromotionState:
    """run-level の activation / promotion 判定結果"""

    # activation decision status
    v3_shadow_verdict_decision_accepted: bool
    numeric_verdict_rates_decision_accepted: bool

    # VN gate runtime status
    vn_gate_all_satisfied: bool
    vn_gate_first_unmet: str | None

    # derived rendering status
    full_verdict_computable: bool
    denominator_contract_satisfied: bool
    v3_shadow_verdict_rendered: bool
    numeric_verdict_rates_rendered: bool

    # suppression reasons（空なら suppression なし。surface 表示用）
    suppression_reasons: tuple[str, ...]

    # promotion gate status（per-lane。監査用の gate-level detail を保持）
    promotion_candidacy: tuple[LanePromotionStatus, ...]


@dataclass(frozen=True, slots=True)
class LanePromotionStatus:
    """一つの CI lane / validator に対する promotion gate 判定結果"""
    lane_id: str
    passed: bool
    failed_gate_ids: tuple[str, ...]  # 例: ("PR-02", "PR-05")
    authority_reference: str           # 例: "adr_v3_10 §CI promotion gate"
```

operator summary にはこの state の要約を `[exploratory]` label 付きで表示してよいが、authority は `operator_surface_state.json` とその run-record mirror にある。

---

## Cross-Artifact Alignment

RP-4 materialization の前後で、以下の cross-artifact 一致を維持する。

| artifact pair | alignment rule | violation action |
|---|---|---|
| `verdict_record.json` ↔ `sidecar_run_record.json` | `v3_shadow_verdict`, `verdict_match_rate` が field-by-field 一致 | hard block |
| `verdict_record.json` ↔ operator summary | verdict_record が None なのに summary が数値表示 → 不一致 | hard block |
| `run_drift_report.json` ↔ operator summary | drift report の `v3_shadow_verdict_rendered` が false なのに summary が表示 → 不一致 | hard block |
| `generator_manifest.json` ↔ `run_drift_report.json` | drift report が manifest に登録され `expected_output_digest` が一致 | hard block |
| operator summary ↔ `[exploratory]` label | v3 section に `[exploratory]` がない → 不一致 | hard block |

不一致検出時は report 出力を block し、suppression reason を `ActivationPromotionState.suppression_reasons` に記録する。

---

## Rollback / Freeze-Back

RP-4 の rendering / hardening が問題を起こした場合、freeze-back は以下のとおり。

- `v3_shadow_verdict` → None に戻す（rendering suppress）
- numeric verdict metrics → N/A に戻す（rendering suppress）
- operator summary → RP-3 以前の suppressed state に戻す
- `run_drift_report.json` の `ActivationPromotionState` → `v3_shadow_verdict_rendered: false`, `numeric_verdict_rates_rendered: false` に戻す
- rc2 primary は不変
- `comparator_scope`, `comparable_channels` は不変
- authority layering は不変
- `output_inventory.json` は不変

freeze-back は rendering surface の巻き戻しであり、boundary / scope / authority の変更ではない。freeze-back は explicit decision で行い、自動化しない。

---

## Still Out of Scope

- Cap comparable 参加
- Rule3B comparable 昇格
- `comparator_scope` の再 widening
- `comparable_channels` の変更
- authority layering 変更
- `output_inventory.json` 変更
- full migration closure
- stale / archived 文書の authority 復帰
- rc2-frozen suite の required matrix 変更
- `[exploratory]` label の除去
- mixed rc2/v3 aggregate summary

---

*End of document*
