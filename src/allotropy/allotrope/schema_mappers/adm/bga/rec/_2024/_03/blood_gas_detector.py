from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMillimeterOfMercury,
    TQuantityValuePercent,
)
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True, kw_only=True)
class BloodGasDetectorMixin:
    po2: float
    pco2: float
    carbon_dioxide_saturation: float | None = None
    oxygen_saturation: float | None = None

    def measurement_kwargs(self, **_: Any) -> dict[str, Any]:
        return {
            "pO2": TQuantityValueMillimeterOfMercury(value=self.po2),
            "pCO2": TQuantityValueMillimeterOfMercury(value=self.pco2),
            "carbon_dioxide_saturation": quantity_or_none(
                TQuantityValuePercent, self.carbon_dioxide_saturation
            ),
            "oxygen_saturation": quantity_or_none(
                TQuantityValuePercent, self.oxygen_saturation
            ),
        }
