from __future__ import annotations

from pathlib import Path

from crisp.repro.hashing import parse_smiles_library, read_smiles_file, sha256_bytes, sha256_json


def test_parse_smiles_library_preserves_cxsmiles_and_identifier(tmp_path: Path) -> None:
    path = tmp_path / "library.smi"
    path.write_text(
        "\n".join([
            "C=CC(=O)N1CCC(C)CC1 |&1:5,10,r| Z3569402359 197.231",
            "CCO Z0002 46.07",
            "",
        ]),
        encoding="utf-8",
    )

    entries = parse_smiles_library(path)

    assert entries == [
        ("C=CC(=O)N1CCC(C)CC1 |&1:5,10,r|", "Z3569402359"),
        ("CCO", "Z0002"),
    ]


def test_read_smiles_file_preserves_cxsmiles(tmp_path: Path) -> None:
    path = tmp_path / "library.smi"
    path.write_text(
        "\n".join([
            "# comment",
            "C=CC(=O)N1CCC(C)CC1 |&1:5,10,r| Z3569402359 197.231",
            "CCO",
            "",
        ]),
        encoding="utf-8",
    )

    smiles = read_smiles_file(path)

    assert smiles == [
        "C=CC(=O)N1CCC(C)CC1 |&1:5,10,r|",
        "CCO",
    ]


def test_sha256_bytes_returns_hex_digest_prefixed() -> None:
    digest = sha256_bytes(b"hello")

    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64


def test_sha256_bytes_is_deterministic() -> None:
    assert sha256_bytes(b"test") == sha256_bytes(b"test")


def test_sha256_bytes_differs_for_different_input() -> None:
    assert sha256_bytes(b"a") != sha256_bytes(b"b")


def test_sha256_json_returns_hex_digest_prefixed() -> None:
    digest = sha256_json({"key": "value"})

    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64


def test_sha256_json_is_order_independent_for_dict_keys() -> None:
    # sha256_json should use canonical JSON (sorted keys)
    d1 = sha256_json({"a": 1, "b": 2})
    d2 = sha256_json({"b": 2, "a": 1})

    assert d1 == d2
