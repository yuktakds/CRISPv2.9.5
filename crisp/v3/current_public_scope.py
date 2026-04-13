from __future__ import annotations

from typing import Mapping

from crisp.v3.contracts import ComparisonScope
from crisp.v3.policy import CAP_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME, PATH_CHANNEL_NAME

CURRENT_PUBLIC_COMPARATOR_SCOPE = ComparisonScope.PATH_AND_CATALYTIC_PARTIAL.value
CURRENT_PUBLIC_COMPARABLE_CHANNELS = (PATH_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME)
CURRENT_PUBLIC_V3_ONLY_CHANNELS = (CAP_CHANNEL_NAME,)


def derive_v3_only_evidence_channels(
    channel_lifecycle_states: Mapping[str, str],
) -> tuple[str, ...]:
    return tuple(
        channel_name
        for channel_name in CURRENT_PUBLIC_V3_ONLY_CHANNELS
        if channel_lifecycle_states.get(channel_name) == "observation_materialized"
    )
