from __future__ import annotations

import json
from pathlib import Path

from crisp.v3.keep_path_rc_audit_io import hash_loaded_files, load_json_object, load_text


# ---------------------------------------------------------------------------
# load_json_object
# ---------------------------------------------------------------------------


def test_load_json_object_returns_payload_and_empty_findings(tmp_path: Path) -> None:
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"key": "value"}), encoding="utf-8")

    payload, findings = load_json_object(p, label="TEST")

    assert payload == {"key": "value"}
    assert findings == []


def test_load_json_object_missing_file_returns_none_and_read_error(tmp_path: Path) -> None:
    p = tmp_path / "missing.json"

    payload, findings = load_json_object(p, label="MY_ARTIFACT")

    assert payload is None
    assert any("MY_ARTIFACT_READ_ERROR" in f for f in findings)


def test_load_json_object_invalid_json_returns_none_and_decode_error(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json {{{", encoding="utf-8")

    payload, findings = load_json_object(p, label="BAD")

    assert payload is None
    assert any("BAD_JSON_DECODE_ERROR" in f for f in findings)


def test_load_json_object_non_object_json_returns_none_and_type_error(tmp_path: Path) -> None:
    p = tmp_path / "list.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    payload, findings = load_json_object(p, label="LIST")

    assert payload is None
    assert any("LIST_NOT_OBJECT" in f for f in findings)


# ---------------------------------------------------------------------------
# load_text
# ---------------------------------------------------------------------------


def test_load_text_returns_content_and_empty_findings(tmp_path: Path) -> None:
    p = tmp_path / "notes.md"
    p.write_text("hello world", encoding="utf-8")

    text, findings = load_text(p, label="NOTES")

    assert text == "hello world"
    assert findings == []


def test_load_text_missing_file_returns_none_and_read_error(tmp_path: Path) -> None:
    p = tmp_path / "missing.md"

    text, findings = load_text(p, label="NOTES")

    assert text is None
    assert any("NOTES_READ_ERROR" in f for f in findings)


# ---------------------------------------------------------------------------
# hash_loaded_files
# ---------------------------------------------------------------------------


def test_hash_loaded_files_returns_relative_path_keys(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    f = repo_root / "subdir" / "file.json"
    f.parent.mkdir()
    f.write_text("{}", encoding="utf-8")

    result = hash_loaded_files([f], repo_root=repo_root)

    assert "subdir/file.json" in result or "subdir\\file.json" in result


def test_hash_loaded_files_values_are_sha256_prefixed(tmp_path: Path) -> None:
    repo_root = tmp_path
    f = tmp_path / "a.json"
    f.write_text('{"x":1}', encoding="utf-8")

    result = hash_loaded_files([f], repo_root=repo_root)

    assert all(v.startswith("sha256:") for v in result.values())


def test_hash_loaded_files_skips_nonexistent_paths(tmp_path: Path) -> None:
    missing = tmp_path / "ghost.json"

    result = hash_loaded_files([missing], repo_root=tmp_path)

    assert result == {}


def test_hash_loaded_files_empty_list_returns_empty_dict(tmp_path: Path) -> None:
    result = hash_loaded_files([], repo_root=tmp_path)

    assert result == {}
