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

## Git 方針

- `.gitattributes` でテキストは基本 LF、`*.ps1`/`*.bat`/`*.cmd` は CRLF に固定
- `.venv` と `.uv-cache` はコミットしない
- 共有は `pyproject.toml` と `uv.lock` を基準に行う
