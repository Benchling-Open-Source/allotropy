from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNanometer,
    TQuantityValuePicogramPerMilliliter,
)
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True, kw_only=True)
class DeviceControlDocumentMixin:
    detector_wavelength_setting: float | None = None
    detector_bandwidth_setting: float | None = None
    electronic_absorbance_wavelength_setting: float | None = None
    electronic_absorbance_bandwidth_setting: float | None = None
    electronic_absorbance_reference_bandwidth_setting: float | None = None
    electronic_absorbance_reference_wavelength_setting: float | None = None

    def device_control_document_kwargs(self) -> dict[str, Any]:
        return {
            "detector_wavelength_setting": quantity_or_none(
                TQuantityValueNanometer, self.detector_wavelength_setting
            ),
            "detector_bandwidth_setting": quantity_or_none(
                TQuantityValueNanometer, self.detector_bandwidth_setting
            ),
            "electronic_absorbance_wavelength_setting": quantity_or_none(
                TQuantityValueNanometer, self.electronic_absorbance_wavelength_setting
            ),
            "electronic_absorbance_bandwidth_setting": quantity_or_none(
                TQuantityValueNanometer, self.electronic_absorbance_bandwidth_setting
            ),
            "electronic_absorbance_reference_wavelength_setting": quantity_or_none(
                TQuantityValueNanometer,
                self.electronic_absorbance_reference_wavelength_setting,
            ),
            "electronic_absorbance_reference_bandwidth_setting": quantity_or_none(
                TQuantityValueNanometer,
                self.electronic_absorbance_reference_bandwidth_setting,
            ),
        }


@dataclass(frozen=True, kw_only=True)
class UltravioletAbsorbancePointDetectionMixin(DeviceControlDocumentMixin):
    absorbance: float
    mass_concentration: float | None = None

    def measurement_kwargs(self, **_: Any) -> dict[str, Any]:
        return {
            "absorbance": TQuantityValueMilliAbsorbanceUnit(value=self.absorbance),
            "mass_concentration": quantity_or_none(
                TQuantityValuePicogramPerMilliliter, self.mass_concentration
            ),
        }
