from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliOsmolesPerKilogram,
)


@dataclass(frozen=True, kw_only=True)
class OsmolalityDetectorMixin:
    osmolality: float

    def measurement_kwargs(self, **_: Any) -> dict[str, Any]:
        return {
            "osmolality": TQuantityValueMilliOsmolesPerKilogram(value=self.osmolality),
        }
