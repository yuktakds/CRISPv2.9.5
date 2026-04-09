from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping


def _metric(payload: Mapping[str, Any], key: str) -> float | None:
    quantitative_metrics = payload.get("quantitative_metrics", {})
    value = quantitative_metrics.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def project_catalytic_rule3a_to_anchoring_input(payload: Mapping[str, Any]) -> SimpleNamespace:
    best_target_distance = _metric(payload, "best_target_distance")
    if best_target_distance is None:
        raise ValueError("catalytic Rule3A projector requires quantitative_metrics.best_target_distance")
    return SimpleNamespace(best_target_distance=best_target_distance)


def project_thin_offtarget_to_offtarget_input(payload: Mapping[str, Any]) -> SimpleNamespace:
    best_offtarget_distance = _metric(payload, "best_offtarget_distance")
    if best_offtarget_distance is None:
        raise ValueError("offtarget projector requires quantitative_metrics.best_offtarget_distance")
    return SimpleNamespace(best_offtarget_distance=best_offtarget_distance)
