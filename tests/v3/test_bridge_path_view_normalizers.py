from __future__ import annotations

from crisp.v3.bridge.path_view import (
    normalize_bool_or_none,
    normalize_int,
    normalize_numeric,
    normalize_str_list,
)


# ---------------------------------------------------------------------------
# normalize_numeric
# ---------------------------------------------------------------------------


def test_normalize_numeric_returns_float_for_int() -> None:
    assert normalize_numeric(3) == 3.0
    assert isinstance(normalize_numeric(3), float)


def test_normalize_numeric_returns_float_for_float() -> None:
    assert normalize_numeric(0.75) == 0.75


def test_normalize_numeric_returns_none_for_bool() -> None:
    # bool is a subtype of int in Python; must be treated as non-numeric
    assert normalize_numeric(True) is None
    assert normalize_numeric(False) is None


def test_normalize_numeric_returns_none_for_none() -> None:
    assert normalize_numeric(None) is None


def test_normalize_numeric_returns_none_for_string() -> None:
    assert normalize_numeric("0.5") is None


def test_normalize_numeric_returns_none_for_list() -> None:
    assert normalize_numeric([1.0]) is None


def test_normalize_numeric_zero_is_valid() -> None:
    assert normalize_numeric(0) == 0.0
    assert normalize_numeric(0.0) == 0.0


# ---------------------------------------------------------------------------
# normalize_bool_or_none
# ---------------------------------------------------------------------------


def test_normalize_bool_or_none_passes_true() -> None:
    assert normalize_bool_or_none(True) is True


def test_normalize_bool_or_none_passes_false() -> None:
    assert normalize_bool_or_none(False) is False


def test_normalize_bool_or_none_returns_none_for_none() -> None:
    assert normalize_bool_or_none(None) is None


def test_normalize_bool_or_none_returns_none_for_int() -> None:
    # integers are not booleans in this context
    assert normalize_bool_or_none(1) is None
    assert normalize_bool_or_none(0) is None


def test_normalize_bool_or_none_returns_none_for_string() -> None:
    assert normalize_bool_or_none("true") is None


# ---------------------------------------------------------------------------
# normalize_int
# ---------------------------------------------------------------------------


def test_normalize_int_returns_int_for_int() -> None:
    assert normalize_int(5) == 5
    assert isinstance(normalize_int(5), int)


def test_normalize_int_returns_none_for_bool() -> None:
    # bool is a subtype of int; must not be passed as an int count
    assert normalize_int(True) is None
    assert normalize_int(False) is None


def test_normalize_int_returns_none_for_float() -> None:
    assert normalize_int(3.0) is None


def test_normalize_int_returns_none_for_none() -> None:
    assert normalize_int(None) is None


def test_normalize_int_zero_is_valid() -> None:
    assert normalize_int(0) == 0


# ---------------------------------------------------------------------------
# normalize_str_list
# ---------------------------------------------------------------------------


def test_normalize_str_list_converts_list_of_strings() -> None:
    result = normalize_str_list(["a", "b", "c"])

    assert result == ["a", "b", "c"]


def test_normalize_str_list_converts_tuple() -> None:
    result = normalize_str_list(("x", "y"))

    assert result == ["x", "y"]


def test_normalize_str_list_stringifies_non_string_items() -> None:
    result = normalize_str_list([1, 2, 3])

    assert result == ["1", "2", "3"]


def test_normalize_str_list_returns_none_for_none() -> None:
    assert normalize_str_list(None) is None


def test_normalize_str_list_returns_none_for_non_sequence() -> None:
    assert normalize_str_list("not-a-list") is None
    assert normalize_str_list(42) is None


def test_normalize_str_list_returns_empty_list_for_empty_input() -> None:
    assert normalize_str_list([]) == []
