# ADR-V3-10 Draft Audit Report

Date: 2026-04-08  
Auditor: design review  
Subject: ADR-V3-10 (proposed) Full Migration Contract and Promotion Policy  
Authority set: `v3x_evidence_channel_kernel_architecture_rev3.1.md`, `v3x_bridge_ci_contracts.md`, `v3x_path_verdict_comparability.md`, `CRISP_v3x_semantic_design_SOT_RC.md`, `CRISP_v4_3_2.md`, `v2_9_5_rc2_deferred_v3x_topics.md`

---

## Summary

ADR draft は、全体の方向性・5 判断・normative tables ともに authority 文書群と高い整合性を持つ。Path-only closure を後退させず full migration boundary を上乗せする設計は正しい。ただし、以下の 3 件の contract issue、2 件の表記不整合、3 件の明確化推奨を検出した。blocking issue は 1 件。

---

## A. Contract Issues（修正すべき）

### A.1 [BLOCKING] denominator 決定の authority 越権

**箇所**: 「Denominator / match rate / mismatch rate は以下で固定します」節

**問題**: 「verdict_match_rate と verdict_mismatch_rate の分母は全 compounds ではなく FULL_VERDICT_COMPARABLE subset とする」と断定している。しかし bridge_ci_contracts §6 の full scope baseline は分母を「full migration ADR で定義」と明示的に provisional に留めている。本 ADR がその「full migration ADR」であるならば判断権限はあるが、その場合 bridge_ci_contracts の provisional 注記を本 ADR が supersede することを明示すべきである。現状では、bridge_ci_contracts が「まだ決めない」と言い、本 ADR が「決める」と言い、しかし supersede 関係が書かれていないため、authority の二重化が生じる。

**推奨**: 本文中に「bridge_ci_contracts §6 が full scope denominator を provisional rule としていた点について、本 ADR はこれを以下のとおり最終決定する」と supersede 宣言を追加する。または、本 ADR 自身もまだ provisional とする場合は bridge_ci_contracts との表現を揃える。

### A.2 observation_bundle.json の出自不明

**箇所**: Canonical boundary 節 Layer 1 の記述、および artifact authority table

**問題**: `observation_bundle.json` が Layer 1 required artifact として登場し、「required for full verdict claim」とされている。しかし rev3.1 §D.1 の三層 model には `observation_bundle.json` は含まれていない。rev3.1 が定義する Layer 1 artifact は `channel_evidence_*.jsonl` と `builder_provenance.json` である。`observation_bundle.json` は authority 文書群のいずれにも定義されていない新規 artifact name である。

**推奨**: 二つの選択肢がある。(a) `observation_bundle.json` は SCVObservationBundle の serialization であり、rev3.1 §D.1 に追加定義が必要な新規 artifact であることを明示する。(b) SCVObservationBundle は channel_evidence_*.jsonl + projector metadata から再構成可能であり、独立 artifact は不要と判断し、表から削除する。いずれにせよ、authority 文書に存在しない artifact name を normative table に置くなら、新規導入であることを宣言すべき。

### A.3 RunDriftReport artifact filename が UNKNOWN のまま normative table に入っている

**箇所**: artifact authority table の RunDriftReport 行

**問題**: 「artifact class defined, filename UNKNOWN」としつつ「required for promotion decisions」と判断している。bridge_ci_contracts §6 は drift report を Layer 1 artifact と定義しているが、filename は指定していない。本 ADR が filename を UNKNOWN のまま required にすると、「何が required かは分かっているが、何を見ればよいかは分からない」状態になる。

**推奨**: filename を UNKNOWN のまま残すなら「required for promotion decisions once filename is frozen」と条件付きにする。または、この ADR で canonical filename を決定する（例: `run_drift_report.json`）。

---

## B. 表記不整合（軽微だが修正推奨）

### B.1 VN 条件の番号ずれリスク

**箇所**: 「VN-01〜VN-06 相当の full-SCV input coverage requirement」

**問題**: path_verdict_comparability は VN-01〜VN-06 を定義しているが、本 ADR は「VN-01〜VN-06 相当」と書き、条件の内容を散文で再記述している。両者が一致しているかは読み手が照合しなければ分からない。とくに path_verdict_comparability の VN-01 は「channel-to-SCV-component mapping が凍結されている」であり、本 ADR の散文記述順序はこれと異なる。

**推奨**: VN-01〜VN-06 を path_verdict_comparability から by reference で引用し、散文での再記述は補足説明に留める。または本 ADR 版の条件一覧を明示的に付け、path_verdict_comparability との対応表を置く。

### B.2 channel promotion table の Cap blocker 記述

**箇所**: channel promotion table、Cap 行の minimum promotion conditions

**問題**: 「rc2 adapter inputs and truth-source equivalence frozen against cap_batch_eval」と書かれている。しかし `cap_batch_eval` は authority 文書群に登場しない名前である。rc2 の Cap 解析は `cap/layer0.py`〜`layer2.py`、`cap/scv.py`、`mapping.py`、`falsification.py` であり、SoT §15.2 もこれらの module 名を使っている。`cap_batch_eval` が何を指すかが不明確。

**推奨**: authority 文書に存在する module / artifact 名に差し替えるか、`cap_batch_eval` が本 ADR で新規導入する概念であることを明示する。

---

## C. 明確化推奨（blocking ではないが品質向上）

### C.1 materialized-but-not-comparable の四状態化

**箇所**: Comparable-channel promotion policy 節、blocker table の applicability 行

**問題**: blocker table は「channel conflates disabled / applicability-only / observation materialized / not comparable」を hard blocker としており、「four-state semantics frozen at builder and report level」を exit criterion としている。この四状態は authority 文書群で formal に定義されていない。rev3.1 §C.2 の EvidenceState は三値（SUPPORTED / REFUTED / INSUFFICIENT）であり、channel の lifecycle state とは別概念である。

**推奨**: この四状態が channel lifecycle state として新規導入されるなら、enum 定義を本文中に置くか、§Scope で「channel lifecycle state の formal 定義は本 ADR の scope に含む」と宣言する。authority 文書の EvidenceState（evidence-level）と channel lifecycle state（migration-level）の区別を明示する。

### C.2 WP 順序の contract-before-code 宣言と WP-3 の位置

**箇所**: 実装への受け渡しメモ、WP-3

**問題**: 「順序は contract before code とする」と述べつつ、WP-3 は「validation-only で full-SCV input coverage checker, cross-artifact consistency checker, operator display guard を追加する」であり、これは code work である。WP-1（docs）→ WP-2（schema）→ WP-3（validation code）の順序は contract-before-code に準拠しているが、WP-3 が code であることを明示しないと「WP-1,2 が完了する前に WP-3 に着手してよいか」が曖昧になる。

**推奨**: WP 間の dependency を明示する。「WP-3 は WP-1 + WP-2 の完了を前提とする」等。

### C.3 acceptance criteria の「三つ」と regression 項目の関係

**箇所**: acceptance criteria 節

**問題**: 「この ADR が閉じたと見なせる条件は三つ」と書かれているが、直後の「regression で監視すべき項目」は 8 項目あり、これらが三条件のどれに属するかが不明確。三条件は抽象的な原則であり、8 項目は具体的な監視対象であるが、対応関係が書かれていない。

**推奨**: 8 項目を三条件に mapping するか、三条件を acceptance criteria、8 項目を regression invariants として明示的に分離する。

---

## D. 整合性確認済み（問題なし）

以下の項目は authority 文書群と整合していることを確認した。

| 確認項目 | 対応 authority | 結果 |
|---|---|---|
| SCV 単一判定器の継承 | v4.3.2 §9.1, rev3.1 §A.1 SC-01 | 整合 |
| hybrid SCV mode の棄却理由 | path_comparability §2.3 | 同一理由を継承、整合 |
| v3_shadow_verdict = None の維持条件 | path_comparability §2.4 VN-01〜VN-06 | 整合（ただし B.1 の表記ずれに注意）|
| verdict_record.json は schema reservation | path_comparability §2.5 | 整合 |
| sidecar_run_record.json が current Layer 0 authority | path_comparability §2.5 | 整合 |
| output_inventory.json は rc2 authority のまま | 全 authority 文書 | 整合 |
| channel-to-SCV-component mapping は UNKNOWN | path_comparability §2.2 | 整合 |
| witness_drift は comparability 阻害要因に含めない | path_comparability §1.5 | 整合 |
| metrics_drift = 0 は必要条件 | path_comparability §3.4, bridge_ci_contracts §5 | 整合 |
| Path-only scope の path_component_match_rate 分母 | path_comparability §4.2 | 整合 |
| PR-01〜PR-06 の昇格条件 | bridge_ci_contracts ADR-V3-06 §5 | 整合 |
| NP-01〜NP-04 の非昇格条件 | bridge_ci_contracts ADR-V3-06 §4 | 整合 |
| rc2 frozen boundary の保全 | deferred index, SoT §4 | 整合 |
| ADR-gated items の非触 | SoT §5.3, deferred index table | 整合 |
| generator_manifest.json の re-materialization contract 性 | rev3.1 §D.2, path_comparability | 整合 |
| adapter 設計原則（None, 型変換のみ, stub, diagnostic 非対象）| bridge_ci_contracts §9 | 整合 |
| component match ≠ verdict match の non-equivalence | path_comparability §1.2, §4.2 | 整合 |
| exploratory → required は design doc では authorize しない | path_comparability §5.2 | 整合 |
| terminal policy は object logic の外側 | v4.3.2 §2.3 | 言及あり、整合 |
| PASS 射程宣言の継承 | v4.3.2 §0.1 | 暗黙だが矛盾なし |

---

## E. 監査結論

| severity | 件数 | 判断 |
|---|---|---|
| BLOCKING | 1 | A.1 denominator supersede 宣言の欠如 |
| contract issue | 2 | A.2 observation_bundle.json 出自不明, A.3 filename UNKNOWN + required |
| 表記不整合 | 2 | B.1 VN 番号照合, B.2 cap_batch_eval 出自不明 |
| 明確化推奨 | 3 | C.1 四状態 enum, C.2 WP dependency, C.3 acceptance/regression mapping |

**判定**: A.1 を解消すれば adoptable。A.2, A.3 は adopt 前に解消が望ましいが、adopt 後の immediate follow-up でも許容可能。B, C は品質改善であり、adopt を阻害しない。

---

*End of audit report*
