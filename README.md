# CRISP v2.9.5

`D:\CRISPv2.9.5` を `uv` と `git` 前提の新規開発リポジトリとして運用するための最小セットアップです。Windows と macOS を対象に、依存は `uv.lock` で固定し、オフライン時は repo 内キャッシュを使って再同期できるようにしています。

## 前提

- Git
- `uv` 0.11 以降
- CPython 3.13

`uv` が未導入なら、公式インストーラを使ってください。

- Windows: `powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## 初回セットアップ

Windows:

```powershell
.\scripts\bootstrap.ps1
```

macOS:

```bash
bash ./scripts/bootstrap.sh
```

その後の確認:

```powershell
uv run pytest -q
uv run crisp doctor
```

## オフライン運用

1. 各 OS で一度だけオンライン状態で `bootstrap` を実行します。
2. 依存は `.uv-cache/<platform>` に保持されます。
3. 以後はオフライン同期を使います。

Windows:

```powershell
.\scripts\bootstrap.ps1 -Offline
```

macOS:

```bash
bash ./scripts/bootstrap.sh --offline
```

`.venv` は共有せず、Git で共有するのはソースと `uv.lock` のみです。Windows と macOS はそれぞれ自分の `.uv-cache` を持たせてください。

## クロスプラットフォーム検証

依存更新時は、Windows/macOS の lock 解決確認を必ず回します。

Windows:

```powershell
.\scripts\verify-lock.ps1
```

macOS:

```bash
bash ./scripts/verify-lock.sh
```

## 9KR6 Config Taxonomy

| config | role | n_conformers | n_rotations | n_translations | alpha | expected_use | allowed_comparisons | frozen_for_regression |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| `configs/9kr6_cys328.lowsampling.yaml` | `lowsampling` | 1 | 1 | 1 | 0.5 | Low-sampling diagnostic regime for search-collapse inspection only. | `cross-regime` | `false` |
| `configs/9kr6_cys328.benchmark.yaml` | `benchmark` | 4 | 16 | 8 | 0.4 | Frozen regression baseline for parser, search, and reason-taxonomy changes. | `same-config`, `cross-regime` | `true` |
| `configs/9kr6_cys328.smoke.yaml` | `smoke` | 8 | 64 | 32 | 0.35 | Pipeline health-check regime for end-to-end completion on real data. | `cross-regime` | `false` |
| `configs/9kr6_cys328.production.yaml` | `production` | 8 | 64 | 32 | 0.35 | Operational full-run regime for real-data execution; not a regression baseline. | `cross-regime` | `false` |

比較ルール:

- `allowed_comparisons` は閉じた語彙です。現在許可する値は `same-config`, `cross-regime`, `none` だけです。
- parser 修正、探索改良、reason taxonomy 変更の回帰比較は `benchmark` で固定します。
- `same-config` 比較を許可するのは `benchmark` だけです。
- `production` は regression baseline ではなく、`cross-regime` の reference comparison だけを許可します。
- config をまたぐ比較は `comparison_type: cross-regime` を必須にし、algorithm comparison と解釈しません。
- 旧 `configs/9kr6_cys328.yaml` は曖昧だったため廃止し、`lowsampling` に置き換えました。

Guard:

- `uv run crisp assert-regression-config --config configs/9kr6_cys328.benchmark.yaml`
- regression run では `run-mef-library`, `run-phase1-single`, `run-phase1-library`, `run-integrated-v29` に `--require-frozen-for-regression` を付けると、benchmark 以外の config を開始前に拒否します。
- 付け忘れを避けるには `uv run crisp-regression ...` を使います。これは benchmark guard を暗黙必須にした wrapper です。
- 運用向けの role-safe façade として `uv run crisp-v29 <benchmark|smoke|production|lowsampling> ...` を使えます。開始時に `role/comparison/truth-source/core-frozen` を固定 banner で表示し、subcommand と config role が不一致なら fail-fast します。

## v2.9.5 CI Boundary

Required CI set for `v2.9.5`:

- `required / benchmark-integrated-smoke`
- `required / production-integrated-smoke`
- `required / ci-sized-full-fixture`
- `required / config-guard-matrix`
- `required / replay-inventory-crosscheck`
- `required / cap-artifact-invariants`
- `required / v3-sidecar-determinism`
- `required / v2.9.5-matrix`

These checks protect contract stability, not local heavy-run readiness.
`required / ci-sized-full-fixture` is a deterministic fixture, not a substitute for real-data full runs.
The `v3` Path-first sidecar audit note is in [docs/archive/v3_path_first_milestone_audit_note.md](docs/archive/v3_path_first_milestone_audit_note.md).

Operator-owned local heavy runs:

- benchmark full on real libraries
- production full on real libraries

Use the local checklist in [docs/legacy/v2.9.5/v2.9.5_local_heavy_run_checklist.md](docs/legacy/v2.9.5/v2.9.5_local_heavy_run_checklist.md) before treating a heavy run as release evidence.

## crisp-v29 Operator Guide

Mode guide:

- `benchmark`: frozen regression baseline. Default `comparison_type` is `same-config`.
- `smoke`: health-check regime for integrated completion. Default `comparison_type` is `cross-regime`.
- `lowsampling`: diagnostic inspection path only. Do not read it as production readiness.
- `production`: operational run path. Use `cross-regime` labeling and keep it separate from regression claims.

comparison_type semantics:

- `same-config` is the benchmark-only label for identical config regression comparisons.
- `cross-regime` is a cross-config/regime label only. It must not be read as an algorithm comparison claim.

Role-safe examples:

```text
uv run crisp-v29 benchmark --config configs/9kr6_cys328.benchmark.yaml --library data/libraries/CYS-3200.smiles --stageplan configs/stageplan.empty.json --out outputs/runs/9kr6-benchmark-smoke
uv run crisp-v29 smoke --config configs/9kr6_cys328.smoke.yaml --library data/libraries/CYS-3200.smiles --stageplan configs/stageplan.empty.json --out outputs/runs/9kr6-smoke-cap --run-mode core+rule1+cap --caps outputs/fixtures/caps.parquet
uv run crisp-v29 production --config configs/9kr6_cys328.production.yaml --library data/libraries/fACR2240.smiles --stageplan configs/stageplan.empty.json --out outputs/runs/9kr6-production-full --run-mode full --caps outputs/fixtures/caps.parquet --assays outputs/fixtures/assays.parquet
uv run crisp-v29 lowsampling --config configs/9kr6_cys328.lowsampling.yaml --library data/libraries/CYS-3200.smiles --stageplan configs/stageplan.empty.json --out outputs/runs/9kr6-lowsampling-core
```

Regression wrapper 例:

- `uv run crisp-regression run-phase1-library --config configs/9kr6_cys328.benchmark.yaml --library outputs/audit-inputs/facr2240-sample100.smi --run-id regression-facr2240-benchmark --stageplan configs/stageplan.empty.json`

## Git 方針

- `.gitattributes` でテキストは基本 LF、`*.ps1`/`*.bat`/`*.cmd` は CRLF に固定
- `.venv` と `.uv-cache` はコミットしない
- 共有は `pyproject.toml` と `uv.lock` を基準に行う
