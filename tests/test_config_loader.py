from __future__ import annotations

import pytest

from crisp.config.loader import (
    DEPRECATED_CONFIG_FILENAMES,
    EXPECTED_ATOM,
    _atom_from_dict,
    _require_exact_keys,
    _require_mapping,
    _require_string_list,
)
from crisp.config.models import AtomSpec


# ---------------------------------------------------------------------------
# _require_mapping
# ---------------------------------------------------------------------------


def test_require_mapping_dict_input_returns_dict() -> None:
    d = {"key": "value"}
    result = _require_mapping("MySection", d)

    assert result is d


def test_require_mapping_list_raises_type_error() -> None:
    with pytest.raises(TypeError, match="MySection"):
        _require_mapping("MySection", [1, 2, 3])


def test_require_mapping_string_raises_type_error() -> None:
    with pytest.raises(TypeError):
        _require_mapping("pdb", "not_a_dict")


def test_require_mapping_none_raises_type_error() -> None:
    with pytest.raises(TypeError):
        _require_mapping("section", None)


# ---------------------------------------------------------------------------
# _require_exact_keys
# ---------------------------------------------------------------------------


def test_require_exact_keys_exact_match_does_not_raise() -> None:
    _require_exact_keys("section", {"a": 1, "b": 2}, {"a", "b"})


def test_require_exact_keys_missing_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="missing"):
        _require_exact_keys("section", {"a": 1}, {"a", "b"})


def test_require_exact_keys_extra_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="extra"):
        _require_exact_keys("section", {"a": 1, "b": 2, "c": 3}, {"a", "b"})


def test_require_exact_keys_empty_dict_exact_match() -> None:
    _require_exact_keys("section", {}, set())


def test_require_exact_keys_error_message_includes_section_name() -> None:
    with pytest.raises(ValueError, match="my_section"):
        _require_exact_keys("my_section", {}, {"required_key"})


# ---------------------------------------------------------------------------
# _require_string_list
# ---------------------------------------------------------------------------


def test_require_string_list_valid_list_of_strings() -> None:
    result = _require_string_list("field", ["a", "b", "c"])

    assert result == ["a", "b", "c"]


def test_require_string_list_non_list_raises_type_error() -> None:
    with pytest.raises(TypeError, match="field"):
        _require_string_list("field", "not_a_list")


def test_require_string_list_list_with_int_raises_type_error() -> None:
    with pytest.raises(TypeError):
        _require_string_list("field", ["a", 1])


def test_require_string_list_empty_list_is_valid() -> None:
    result = _require_string_list("field", [])

    assert result == []


# ---------------------------------------------------------------------------
# _atom_from_dict
# ---------------------------------------------------------------------------


def _valid_atom_dict() -> dict:
    return {
        "chain": "A",
        "residue_number": 328,
        "insertion_code": "",
        "atom_name": "SG",
    }


def test_atom_from_dict_returns_atom_spec_with_correct_fields() -> None:
    atom = _atom_from_dict("target_cysteine", _valid_atom_dict())

    assert isinstance(atom, AtomSpec)
    assert atom.chain == "A"
    assert atom.residue_number == 328
    assert atom.insertion_code == ""
    assert atom.atom_name == "SG"


def test_atom_from_dict_residue_number_is_int() -> None:
    d = _valid_atom_dict()
    d["residue_number"] = "328"  # string input
    atom = _atom_from_dict("target_cysteine", d)

    assert atom.residue_number == 328
    assert isinstance(atom.residue_number, int)


def test_atom_from_dict_wrong_keys_raises_value_error() -> None:
    with pytest.raises(ValueError, match="keys mismatch"):
        _atom_from_dict("target_cysteine", {"chain": "A"})


# ---------------------------------------------------------------------------
# DEPRECATED_CONFIG_FILENAMES
# ---------------------------------------------------------------------------


def test_deprecated_config_filenames_maps_old_to_new() -> None:
    assert "9kr6_cys328.yaml" in DEPRECATED_CONFIG_FILENAMES
    assert DEPRECATED_CONFIG_FILENAMES["9kr6_cys328.yaml"].endswith(".lowsampling.yaml")


# ---------------------------------------------------------------------------
# EXPECTED_ATOM constant
# ---------------------------------------------------------------------------


def test_expected_atom_keys_match_atom_spec_fields() -> None:
    assert EXPECTED_ATOM == {"chain", "residue_number", "insertion_code", "atom_name"}
