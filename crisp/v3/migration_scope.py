from __future__ import annotations

from typing import Literal

from crisp.v3.contracts import ComparisonScope

MappingStatus = Literal["FROZEN", "VALIDATED", "CANDIDATE", "UNKNOWN"]

_SCV_COMPONENT_MAPPING_STATUS: dict[str, MappingStatus] = {
    "scv_pat": "FROZEN",
    "scv_anchoring": "FROZEN",
    "scv_offtarget": "FROZEN",
}
_REQUIRED_SCV_COMPONENTS = ("scv_pat", "scv_anchoring", "scv_offtarget")
_SCV_COMPONENT_SOURCES: dict[str, str] = {
    "scv_pat": "path_channel_projector",
    "scv_anchoring": "catalytic_rule3a_projector",
    "scv_offtarget": "thin_offtarget_channel_wrapper",
}
_INTERNAL_FULL_SCV_COMPONENT_CHANNELS: dict[str, str] = {
    "scv_pat": "path",
    "scv_anchoring": "scv_anchoring",
    "scv_offtarget": "scv_offtarget",
}


def get_mapping_status(component_name: str) -> MappingStatus:
    return _SCV_COMPONENT_MAPPING_STATUS[str(component_name)]


def required_scv_components() -> tuple[str, ...]:
    return _REQUIRED_SCV_COMPONENTS


def get_mapping_source(component_name: str) -> str:
    return _SCV_COMPONENT_SOURCES[str(component_name)]


def get_internal_full_scv_channel(component_name: str) -> str:
    return _INTERNAL_FULL_SCV_COMPONENT_CHANNELS[str(component_name)]


def all_required_components_frozen() -> bool:
    return all(get_mapping_status(component_name) == "FROZEN" for component_name in _REQUIRED_SCV_COMPONENTS)


def get_comparator_scope(scope: str | ComparisonScope) -> str:
    return scope.value if isinstance(scope, ComparisonScope) else str(scope)


def resolve_pr03_metric(scope: str | ComparisonScope) -> str:
    normalized_scope = get_comparator_scope(scope)
    return "path_component_match_rate" if normalized_scope == ComparisonScope.PATH_ONLY_PARTIAL.value else "verdict_match_rate"
