from __future__ import annotations

import json

from crisp.utils.jsonx import canonical_json_bytes


def test_canonical_json_bytes_returns_bytes() -> None:
    result = canonical_json_bytes({"a": 1})

    assert isinstance(result, bytes)


def test_canonical_json_bytes_keys_sorted() -> None:
    result = canonical_json_bytes({"z": 1, "a": 2, "m": 3})
    parsed = json.loads(result)

    assert list(parsed.keys()) == ["a", "m", "z"]


def test_canonical_json_bytes_no_whitespace_separators() -> None:
    result = canonical_json_bytes({"a": 1, "b": [1, 2]})
    text = result.decode("utf-8")

    assert " " not in text


def test_canonical_json_bytes_utf8_encoded() -> None:
    result = canonical_json_bytes({"key": "日本語"})

    assert "日本語".encode("utf-8") in result


def test_canonical_json_bytes_deterministic() -> None:
    obj = {"b": [3, 1, 2], "a": {"z": True, "m": None}}
    assert canonical_json_bytes(obj) == canonical_json_bytes(obj)


def test_canonical_json_bytes_nested_keys_sorted() -> None:
    result = canonical_json_bytes({"outer": {"z": 1, "a": 2}})
    parsed = json.loads(result)

    assert list(parsed["outer"].keys()) == ["a", "z"]


def test_canonical_json_bytes_empty_object() -> None:
    result = canonical_json_bytes({})

    assert result == b"{}"


def test_canonical_json_bytes_null_and_bool() -> None:
    result = canonical_json_bytes({"n": None, "t": True, "f": False})
    parsed = json.loads(result)

    assert parsed["n"] is None
    assert parsed["t"] is True
    assert parsed["f"] is False
