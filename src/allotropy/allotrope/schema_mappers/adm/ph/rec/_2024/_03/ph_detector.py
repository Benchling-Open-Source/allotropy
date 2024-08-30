from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValuePH,
)
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True, kw_only=True)
class PhDetectorMixin:
    ph: float
    temperature: float | None = None

    def measurement_kwargs(self, **_: Any) -> dict[str, Any]:
        return {
            "pH": TQuantityValuePH(value=self.ph),
            "temperature": quantity_or_none(
                TQuantityValueDegreeCelsius, self.temperature
            ),
        }
