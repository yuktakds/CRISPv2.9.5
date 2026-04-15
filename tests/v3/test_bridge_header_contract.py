from __future__ import annotations

from crisp.v3.contracts.bridge_header import BridgeHeader


def test_bridge_header_path_only_partial_contract() -> None:
    header = BridgeHeader(
        semantic_policy_version="v3x-path-first",
        comparator_scope="path_only_partial",
        verdict_comparability="partially_comparable",
        comparable_channels=("path",),
        rc2_policy_version="v2.9.5-rc2",
    )
    data = header.to_dict()

    assert data["semantic_policy_version"] == "v3x-path-first"
    assert data["comparator_scope"] == "path_only_partial"
    assert data["verdict_comparability"] == "partially_comparable"
    assert data["comparable_channels"] == ("path",)


def test_bridge_header_accepts_path_and_catalytic_partial_scope() -> None:
    header = BridgeHeader(
        semantic_policy_version="v3x-path-first",
        comparator_scope="path_and_catalytic_partial",
        verdict_comparability="partially_comparable",
        comparable_channels=("path", "catalytic"),
        rc2_policy_version="v2.9.5-rc2",
    )

    assert header.to_dict()["comparator_scope"] == "path_and_catalytic_partial"
