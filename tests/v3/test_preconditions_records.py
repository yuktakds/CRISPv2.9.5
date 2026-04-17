from __future__ import annotations

from crisp.v3.preconditions_records import (
    _artifact_generator_id,
    _artifact_ref,
    _descriptor_claim,
    _validate_artifact_ref,
)
from crisp.v3.preconditions_types import ARTIFACT_GENERATOR_IDS


# ---------------------------------------------------------------------------
# _artifact_generator_id
# ---------------------------------------------------------------------------


def test_artifact_generator_id_known_artifact() -> None:
    result = _artifact_generator_id("verdict_record.json")

    assert result == ARTIFACT_GENERATOR_IDS["verdict_record.json"]


def test_artifact_generator_id_unknown_artifact_returns_fallback() -> None:
    result = _artifact_generator_id("nonexistent_artifact.json")

    assert result == "v3.unknown_artifact/v1"


def test_artifact_generator_id_observation_bundle() -> None:
    result = _artifact_generator_id("observation_bundle.json")

    assert result == "v3.observation_bundle/v1"


# ---------------------------------------------------------------------------
# _artifact_ref
# ---------------------------------------------------------------------------


def test_artifact_ref_populates_all_fields() -> None:
    ref = _artifact_ref("verdict_record.json", section_id="p7_manifest_entry")

    assert ref.artifact_name == "verdict_record.json"
    assert ref.generator_id == ARTIFACT_GENERATOR_IDS["verdict_record.json"]
    assert ref.section_id == "p7_manifest_entry"


def test_artifact_ref_unknown_uses_fallback_generator_id() -> None:
    ref = _artifact_ref("unknown.json", section_id="my_section")

    assert ref.generator_id == "v3.unknown_artifact/v1"


# ---------------------------------------------------------------------------
# _validate_artifact_ref
# ---------------------------------------------------------------------------


def test_validate_artifact_ref_valid_ref_returns_no_findings() -> None:
    ref = {
        "artifact_name": "verdict_record.json",
        "generator_id": ARTIFACT_GENERATOR_IDS["verdict_record.json"],
        "section_id": "my_section",
    }
    findings = _validate_artifact_ref(
        ref=ref,
        expected_artifact_name=None,
        expected_section_id=None,
        finding_prefix="P7",
    )

    assert findings == []


def test_validate_artifact_ref_none_ref_returns_missing_message() -> None:
    findings = _validate_artifact_ref(
        ref=None,
        expected_artifact_name=None,
        expected_section_id=None,
        finding_prefix="P7",
    )

    assert len(findings) == 1
    assert "P7" in findings[0]
    assert "missing" in findings[0]


def test_validate_artifact_ref_missing_artifact_name_raises_finding() -> None:
    ref = {
        "generator_id": "v3.some/v1",
        "section_id": "my_section",
    }
    findings = _validate_artifact_ref(
        ref=ref,
        expected_artifact_name=None,
        expected_section_id=None,
        finding_prefix="P7",
    )

    assert any("artifact_name" in f for f in findings)


def test_validate_artifact_ref_wrong_expected_artifact_name_raises_finding() -> None:
    ref = {
        "artifact_name": "verdict_record.json",
        "generator_id": ARTIFACT_GENERATOR_IDS["verdict_record.json"],
        "section_id": "my_section",
    }
    findings = _validate_artifact_ref(
        ref=ref,
        expected_artifact_name="other_artifact.json",
        expected_section_id=None,
        finding_prefix="P7",
    )

    assert any("artifact_name" in f for f in findings)


def test_validate_artifact_ref_wrong_generator_id_raises_finding() -> None:
    ref = {
        "artifact_name": "verdict_record.json",
        "generator_id": "v3.wrong/v1",
        "section_id": "my_section",
    }
    findings = _validate_artifact_ref(
        ref=ref,
        expected_artifact_name=None,
        expected_section_id=None,
        finding_prefix="P7",
    )

    assert any("generator_id" in f for f in findings)


def test_validate_artifact_ref_wrong_section_id_raises_finding() -> None:
    ref = {
        "artifact_name": "verdict_record.json",
        "generator_id": ARTIFACT_GENERATOR_IDS["verdict_record.json"],
        "section_id": "actual_section",
    }
    findings = _validate_artifact_ref(
        ref=ref,
        expected_artifact_name=None,
        expected_section_id="expected_section",
        finding_prefix="P7",
    )

    assert any("section_id" in f for f in findings)


# ---------------------------------------------------------------------------
# _descriptor_claim
# ---------------------------------------------------------------------------


def test_descriptor_claim_extracts_all_fields() -> None:
    descriptor = {
        "relative_path": "verdict_record.json",
        "layer": "output",
        "content_type": "application/json",
        "sha256": "sha256:abc123",
        "byte_count": 1024,
    }
    claim = _descriptor_claim(descriptor)

    assert claim["relative_path"] == "verdict_record.json"
    assert claim["layer"] == "output"
    assert claim["content_type"] == "application/json"
    assert claim["sha256"] == "sha256:abc123"
    assert claim["byte_count"] == 1024


def test_descriptor_claim_missing_fields_return_none() -> None:
    claim = _descriptor_claim({})

    assert claim["relative_path"] is None
    assert claim["layer"] is None
    assert claim["content_type"] is None
    assert claim["sha256"] is None
    assert claim["byte_count"] is None


def test_descriptor_claim_has_exactly_five_keys() -> None:
    claim = _descriptor_claim({})

    assert set(claim.keys()) == {"relative_path", "layer", "content_type", "sha256", "byte_count"}
