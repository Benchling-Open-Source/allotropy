from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueMicrometer,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValueNanometer,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True, kw_only=True)
class DeviceControlDocumentMixin:
    excitation_wavelength_setting: float | None = None
    detector_wavelength_setting: float | None = None

    def device_control_document_kwargs(self) -> dict[str, Any]:
        return {
            "excitation_wavelength_setting": quantity_or_none(
                TQuantityValueNanometer, self.excitation_wavelength_setting
            ),
            "detector_wavelength_setting": quantity_or_none(
                TQuantityValueNanometer, self.detector_wavelength_setting
            ),
        }


@dataclass(frozen=True, kw_only=True)
class DataProcessingDocumentMixin:
    cell_type_processing_method: str | None = None
    cell_density_dilution_factor: float | None = None
    minimum_cell_diameter_setting: float | None = None
    maximum_cell_diameter_setting: float | None = None

    def data_processing_document_kwargs(self) -> dict[str, Any]:
        return {
            "cell_type_processing_method": self.cell_type_processing_method,
            "cell_density_dilution_factor": quantity_or_none(
                TQuantityValueUnitless, self.cell_density_dilution_factor
            ),
            "minimum_cell_diameter_setting": quantity_or_none(
                TQuantityValueMicrometer, self.minimum_cell_diameter_setting
            ),
            "maximum_cell_diameter_setting": quantity_or_none(
                TQuantityValueMicrometer, self.maximum_cell_diameter_setting
            ),
        }


@dataclass(frozen=True, kw_only=True)
class ProcessedDataDocumentMixin(DataProcessingDocumentMixin):
    viability: float
    viable_cell_density: float
    total_cell_density: float | None = None
    dead_cell_density: float | None = None
    average_total_cell_diameter: float | None = None
    average_live_cell_diameter: float | None = None
    average_dead_cell_diameter: float | None = None
    total_cell_diameter_distribution: float | None = None
    total_cell_count: float | None = None
    viable_cell_count: float | None = None
    dead_cell_count: float | None = None
    average_total_cell_circularity: float | None = None
    average_viable_cell_circularity: float | None = None

    def processed_data_document_kwargs(self) -> dict[str, Any]:
        return {
            "viability__cell_counter_": TQuantityValuePercent(value=self.viability),
            "viable_cell_density__cell_counter_": TQuantityValueMillionCellsPerMilliliter(
                value=self.viable_cell_density
            ),
            "total_cell_density__cell_counter_": quantity_or_none(
                TQuantityValueMillionCellsPerMilliliter, self.total_cell_density
            ),
            "dead_cell_density__cell_counter_": quantity_or_none(
                TQuantityValueMillionCellsPerMilliliter, self.dead_cell_density
            ),
            "average_total_cell_diameter": quantity_or_none(
                TQuantityValueNanometer, self.average_total_cell_diameter
            ),
            "average_live_cell_diameter__cell_counter_": quantity_or_none(
                TQuantityValueMicrometer, self.average_live_cell_diameter
            ),
            "average_dead_cell_diameter__cell_counter_": quantity_or_none(
                TQuantityValueMicrometer, self.average_dead_cell_diameter
            ),
            # "total_cell_diameter_distribution": quantity_or_none(
            #     TQuantityValueNanometer, self.total_cell_diameter_distribution
            # ),
            "total_cell_count": quantity_or_none(
                TQuantityValueCell, self.total_cell_count
            ),
            "viable_cell_count": quantity_or_none(
                TQuantityValueCell, self.viable_cell_count
            ),
            "dead_cell_count": quantity_or_none(
                TQuantityValueCell, self.dead_cell_count
            ),
            "average_total_cell_circularity": quantity_or_none(
                TQuantityValueUnitless, self.average_total_cell_circularity
            ),
            "average_viable_cell_circularity": quantity_or_none(
                TQuantityValueUnitless, self.average_viable_cell_circularity
            ),
        }


@dataclass(frozen=True, kw_only=True)
class CellCountingDetectorMixin(ProcessedDataDocumentMixin, DeviceControlDocumentMixin):
    # TODO: make processed data required
    ...
