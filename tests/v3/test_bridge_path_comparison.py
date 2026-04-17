from __future__ import annotations

from crisp.v3.bridge.path_comparison import (
    bundle_index,
    derive_component_evidence_state,
    derive_component_verdict,
)
from crisp.v3.contracts import EvidenceState, SCVObservation, SCVObservationBundle, SCVVerdict


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _observation(
    *,
    channel_name: str = "path",
    verdict: SCVVerdict | None = None,
    evidence_state: EvidenceState | None = None,
) -> SCVObservation:
    return SCVObservation(
        channel_name=channel_name,
        family="PATH",
        verdict=verdict,
        evidence_state=evidence_state,
        payload={},
    )


def _path_payload(
    *,
    numeric_resolution_limited: bool | None = False,
    max_blockage_ratio: float | None = 0.5,
    blockage_pass_threshold: float | None = 0.4,
) -> dict:
    return {
        "quantitative_metrics": {
            "numeric_resolution_limited": numeric_resolution_limited,
            "max_blockage_ratio": max_blockage_ratio,
        },
        "blockage_pass_threshold": blockage_pass_threshold,
    }


def _bundle(observations: list[SCVObservation]) -> SCVObservationBundle:
    return SCVObservationBundle(
        schema_version="v1",
        run_id="test_run",
        semantic_policy_version="vtest",
        observations=observations,
    )


# ---------------------------------------------------------------------------
# derive_component_evidence_state
# ---------------------------------------------------------------------------


def test_derive_evidence_state_none_observation_returns_none() -> None:
    result = derive_component_evidence_state(None, _path_payload())

    assert result is None


def test_derive_evidence_state_uses_evidence_state_when_set() -> None:
    obs = _observation(evidence_state=EvidenceState.SUPPORTED)
    result = derive_component_evidence_state(obs, {})

    assert result == EvidenceState.SUPPORTED.value


def test_derive_evidence_state_numeric_resolution_limited_returns_insufficient() -> None:
    obs = _observation(evidence_state=None)
    result = derive_component_evidence_state(obs, _path_payload(numeric_resolution_limited=True))

    assert result == EvidenceState.INSUFFICIENT.value


def test_derive_evidence_state_max_blockage_ratio_none_returns_none() -> None:
    obs = _observation(evidence_state=None)
    result = derive_component_evidence_state(obs, _path_payload(max_blockage_ratio=None))

    assert result is None


def test_derive_evidence_state_ratio_above_threshold_returns_supported() -> None:
    obs = _observation(evidence_state=None)
    result = derive_component_evidence_state(obs, _path_payload(max_blockage_ratio=0.9, blockage_pass_threshold=0.5))

    assert result == EvidenceState.SUPPORTED.value


def test_derive_evidence_state_ratio_below_threshold_returns_refuted() -> None:
    obs = _observation(evidence_state=None)
    result = derive_component_evidence_state(obs, _path_payload(max_blockage_ratio=0.3, blockage_pass_threshold=0.5))

    assert result == EvidenceState.REFUTED.value


def test_derive_evidence_state_ratio_equal_to_threshold_returns_supported() -> None:
    obs = _observation(evidence_state=None)
    result = derive_component_evidence_state(obs, _path_payload(max_blockage_ratio=0.5, blockage_pass_threshold=0.5))

    assert result == EvidenceState.SUPPORTED.value


# ---------------------------------------------------------------------------
# derive_component_verdict
# ---------------------------------------------------------------------------


def test_derive_verdict_none_observation_returns_none() -> None:
    result = derive_component_verdict(None, _path_payload())

    assert result is None


def test_derive_verdict_uses_verdict_when_set() -> None:
    obs = _observation(verdict=SCVVerdict.PASS)
    result = derive_component_verdict(obs, {})

    assert result == SCVVerdict.PASS.value


def test_derive_verdict_supported_state_returns_pass() -> None:
    obs = _observation(verdict=None, evidence_state=EvidenceState.SUPPORTED)
    result = derive_component_verdict(obs, {})

    assert result == SCVVerdict.PASS.value


def test_derive_verdict_refuted_state_returns_fail() -> None:
    obs = _observation(verdict=None, evidence_state=EvidenceState.REFUTED)
    result = derive_component_verdict(obs, {})

    assert result == SCVVerdict.FAIL.value


def test_derive_verdict_insufficient_state_returns_unclear() -> None:
    obs = _observation(verdict=None, evidence_state=EvidenceState.INSUFFICIENT)
    result = derive_component_verdict(obs, {})

    assert result == SCVVerdict.UNCLEAR.value


def test_derive_verdict_none_state_returns_none() -> None:
    obs = _observation(verdict=None, evidence_state=None)
    result = derive_component_verdict(obs, _path_payload(max_blockage_ratio=None))

    assert result is None


# ---------------------------------------------------------------------------
# bundle_index
# ---------------------------------------------------------------------------


def test_bundle_index_single_observation() -> None:
    obs = _observation(channel_name="path")
    result = bundle_index(_bundle([obs]))

    assert "path" in result
    assert result["path"] is obs


def test_bundle_index_multiple_observations() -> None:
    obs_path = _observation(channel_name="path")
    obs_cap = _observation(channel_name="cap")
    result = bundle_index(_bundle([obs_path, obs_cap]))

    assert set(result.keys()) == {"path", "cap"}


def test_bundle_index_empty_bundle_returns_empty_dict() -> None:
    result = bundle_index(_bundle([]))

    assert result == {}
