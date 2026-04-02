from __future__ import annotations

import hashlib
from collections.abc import Iterable
from importlib import metadata
from pathlib import Path

from crisp.config.models import TargetConfig
from crisp.utils.jsonx import canonical_json_bytes

RUNTIME_PACKAGES = {
    "numpy": "numpy",
    "rdkit": "rdkit",
    "scipy": "scipy",
    "biopython": "biopython",
    "PyYAML": "PyYAML",
}


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def sha256_json(obj: object) -> str:
    return sha256_bytes(canonical_json_bytes(obj))


def compute_requirements_hash() -> str:
    versions: dict[str, str] = {}
    for logical_name, dist_name in RUNTIME_PACKAGES.items():
        versions[logical_name] = metadata.version(dist_name)
    return sha256_json(versions)


def compute_input_hash(smiles: str, requirements_hash: str) -> str:
    return sha256_json({"smiles": smiles, "requirements_hash": requirements_hash})


def compute_config_hash(config: TargetConfig) -> str:
    return sha256_json(config.to_canonical_dict())


def read_smiles_file(path: str | Path) -> list[str]:
    smiles: list[str] = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split()[0]
        smiles.append(token)
    return smiles


def parse_smiles_library(path: str | Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for i, raw_line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        smiles = parts[0]
        name = parts[1] if len(parts) > 1 else f"compound_{i:05d}"
        entries.append((smiles, name))
    return entries


def compute_library_hash(path: str | Path) -> str:
    return sha256_file(path)


def compute_compound_order_hash(smiles_list: Iterable[str]) -> str:
    return sha256_json(list(smiles_list))


def compute_stageplan_hash(path: str | Path) -> str:
    return sha256_file(path)
