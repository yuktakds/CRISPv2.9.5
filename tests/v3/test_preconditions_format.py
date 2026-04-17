from __future__ import annotations

from crisp.v3.preconditions_format import _parse_operator_summary_fields


# ---------------------------------------------------------------------------
# empty / default state
# ---------------------------------------------------------------------------


def test_empty_string_returns_all_none_and_empty_labels() -> None:
    result = _parse_operator_summary_fields("")

    assert result["comparable_channels"] is None
    assert result["v3_only_evidence_channels"] is None
    assert result["v3_only_labels"] == {}


def test_unrecognized_lines_do_not_populate_fields() -> None:
    text = "some other line\n## heading\n* bullet"
    result = _parse_operator_summary_fields(text)

    assert result["comparable_channels"] is None
    assert result["v3_only_evidence_channels"] is None
    assert result["v3_only_labels"] == {}


# ---------------------------------------------------------------------------
# comparable_channels
# ---------------------------------------------------------------------------


def test_comparable_channels_single_item() -> None:
    result = _parse_operator_summary_fields("- comparable_channels: `path`")

    assert result["comparable_channels"] == ["path"]


def test_comparable_channels_multiple_items() -> None:
    result = _parse_operator_summary_fields("- comparable_channels: `path, cap`")

    assert result["comparable_channels"] == ["path", "cap"]


def test_comparable_channels_none_value_returns_empty_list() -> None:
    result = _parse_operator_summary_fields("- comparable_channels: `none`")

    assert result["comparable_channels"] == []


# ---------------------------------------------------------------------------
# v3_only_evidence_channels
# ---------------------------------------------------------------------------


def test_v3_only_evidence_channels_single_item() -> None:
    result = _parse_operator_summary_fields("- v3_only_evidence_channels: `catalytic`")

    assert result["v3_only_evidence_channels"] == ["catalytic"]


def test_v3_only_evidence_channels_none_value_returns_empty_list() -> None:
    result = _parse_operator_summary_fields("- v3_only_evidence_channels: `none`")

    assert result["v3_only_evidence_channels"] == []


# ---------------------------------------------------------------------------
# v3_only_labels
# ---------------------------------------------------------------------------


def test_v3_only_label_single_entry() -> None:
    result = _parse_operator_summary_fields("- [v3-only] cap: `observation_materialized`")

    assert result["v3_only_labels"] == {"cap": "observation_materialized"}


def test_v3_only_label_multiple_entries() -> None:
    text = (
        "- [v3-only] cap: `observation_materialized`\n"
        "- [v3-only] catalytic: `applicability_only`"
    )
    result = _parse_operator_summary_fields(text)

    assert result["v3_only_labels"]["cap"] == "observation_materialized"
    assert result["v3_only_labels"]["catalytic"] == "applicability_only"
    assert len(result["v3_only_labels"]) == 2


# ---------------------------------------------------------------------------
# multiline summary — all fields parsed together
# ---------------------------------------------------------------------------


def test_multiline_summary_populates_all_fields() -> None:
    text = "\n".join(
        [
            "- comparable_channels: `path, cap`",
            "- v3_only_evidence_channels: `catalytic`",
            "- [v3-only] catalytic: `applicability_only`",
        ]
    )
    result = _parse_operator_summary_fields(text)

    assert result["comparable_channels"] == ["path", "cap"]
    assert result["v3_only_evidence_channels"] == ["catalytic"]
    assert result["v3_only_labels"] == {"catalytic": "applicability_only"}


def test_leading_whitespace_on_lines_is_stripped() -> None:
    text = "  - comparable_channels: `path`"
    result = _parse_operator_summary_fields(text)

    assert result["comparable_channels"] == ["path"]
