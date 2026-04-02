from __future__ import annotations

from pathlib import Path

from crisp.repro.hashing import parse_smiles_library, read_smiles_file


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
