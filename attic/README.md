# Attic

CRISPv3 実装に直接関わらないアーカイブ・旧版資料・ローカル設定を隔離する場所です。

## 方針
- 実装やテストに必須でない資料・成果物はここに移動する。
- 参照が必要になった場合のみ明示的に復帰する。

## 収容物
- `docs/archive/` -> `attic/docs/archive/`
- `docs/legacy/` -> `attic/docs/legacy/`
- `docs/CRISP_v4.3.2.md` -> `attic/docs/CRISP_v4.3.2.md`
- `docs/.obsidian/` -> `attic/docs/.obsidian/` (ローカル設定)
- `README.md` (v2.9.5) -> `attic/legacy/README.v2.9.5.md`
- `audit/` -> `attic/legacy/audit/`
- `configs/` -> `attic/legacy/configs/`
- `data/` -> `attic/legacy/data/`
- `manifests/` -> `attic/legacy/manifests/`
- `outputs/` -> `attic/legacy/outputs/`
- `scripts/audit_smoke_config_semantic_drift.py` -> `attic/legacy/scripts/audit_smoke_config_semantic_drift.py`
- `crisp/cli` など v3 非依存の実装 -> `attic/legacy/crisp/`
- `crisp/v29` の大半 -> `attic/legacy/crisp/v29/`
- `tests/v29` と v3 非依存のテスト -> `attic/legacy/tests/`
