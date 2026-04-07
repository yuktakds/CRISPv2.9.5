from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

ComparatorScope = Literal["path_only_partial", "full_bridge"]
VerdictComparability = Literal["not_comparable", "partially_comparable", "fully_comparable"]


@dataclass(frozen=True, slots=True)
class BridgeHeader:
    semantic_policy_version: str
    comparator_scope: ComparatorScope
    verdict_comparability: VerdictComparability
    comparable_channels: tuple[str, ...]
    rc2_policy_version: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
