from __future__ import annotations

import io
from typing import Any, Optional
import uuid

import pandas as pd

from allotropy.allotrope.models.cell_counting_benchling_2023_11_cell_counting import (
    CellCountingAggregateDocument,
    CellCountingDetectorDeviceControlAggregateDocument,
    CellCountingDetectorMeasurementDocumentItem,
    CellCountingDocumentItem,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlDocumentItemModel,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    Model,
    ProcessedDataAggregateDocument1,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueMicrometer,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parsers.beckman_vi_cell_blu.constants import (
    DEFAULT_ANALYST,
    DEFAULT_MODEL_NUMBER,
    VICELL_BLU_SOFTWARE_NAME,
)
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_reader import ViCellBluReader
from allotropy.parsers.vendor_parser import VendorParser

property_lookup = {
    "Average viable diameter (μm)": TQuantityValueMicrometer,
    "Average circularity": TQuantityValueUnitless,
    "Average diameter (μm)": TQuantityValueMicrometer,
    "Average viable circularity": TQuantityValueUnitless,
    "Dilution": TQuantityValueUnitless,
    "Maximum Diameter (μm)": TQuantityValueMicrometer,
    "Minimum Diameter (μm)": TQuantityValueMicrometer,
    "Cell count": TQuantityValueCell,
    "Total (x10^6) cells/mL": TQuantityValueMillionCellsPerMilliliter,
    "Viability (%)": TQuantityValuePercent,
    "Viable cells": TQuantityValueCell,
    "Viable (x10^6) cells/mL": TQuantityValueMillionCellsPerMilliliter,
}


def _get_value(sample: pd.Series[Any], column: str) -> Optional[Any]:
    return sample.get(column)


def get_property_from_sample(sample: pd.Series[Any], property_name: str) -> Any:
    return (
        property_lookup[property_name](value=value)
        if (value := _get_value(sample, property_name))
        else None
    )


class ViCellBluParser(VendorParser):
    def _parse(self, contents: io.IOBase, filename: str) -> Model:
        return self._get_model(ViCellBluReader.read(contents), filename)

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=DEFAULT_MODEL_NUMBER,
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=VICELL_BLU_SOFTWARE_NAME,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                cell_counting_document=self._get_cell_counting_document(data),
            ),
        )

    def _get_cell_counting_document(
        self, data: pd.DataFrame
    ) -> list[CellCountingDocumentItem]:
        return [
            self._get_cell_counting_document_item(sample)
            for _, sample in data.iterrows()
            if _get_value(sample, "Cell count")
        ]

    def _get_cell_counting_document_item(
        self, sample: pd.Series[Any]
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=_get_value(sample, "Analysis by") or DEFAULT_ANALYST,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_time=self.get_date_time(
                            _get_value(sample, "Analysis date/time")
                        ),
                        measurement_identifier=str(uuid.uuid4()),
                        sample_document=SampleDocument(sample_identifier=_get_value(sample, "Sample ID")),  # type: ignore[arg-type]
                        device_control_aggregate_document=CellCountingDetectorDeviceControlAggregateDocument(
                            device_control_document=[
                                DeviceControlDocumentItemModel(
                                    device_type="brightfield imager (cell counter)",
                                    detection_type="brightfield",
                                )
                            ]
                        ),
                        processed_data_aggregate_document=ProcessedDataAggregateDocument1(
                            processed_data_document=[
                                ProcessedDataDocumentItem(
                                    data_processing_document=DataProcessingDocument(
                                        cell_type_processing_method=_get_value(
                                            sample, "Cell type"
                                        ),
                                        minimum_cell_diameter_setting=get_property_from_sample(
                                            sample, "Minimum Diameter (μm)"
                                        ),
                                        maximum_cell_diameter_setting=get_property_from_sample(
                                            sample, "Maximum Diameter (μm)"
                                        ),
                                        cell_density_dilution_factor=get_property_from_sample(
                                            sample, "Dilution"
                                        ),
                                    ),
                                    viability__cell_counter_=get_property_from_sample(
                                        sample, "Viability (%)"
                                    ),
                                    viable_cell_density__cell_counter_=get_property_from_sample(
                                        sample, "Viable (x10^6) cells/mL"
                                    ),
                                    total_cell_count=get_property_from_sample(
                                        sample, "Cell count"
                                    ),
                                    total_cell_density__cell_counter_=get_property_from_sample(
                                        sample, "Total (x10^6) cells/mL"
                                    ),
                                    average_total_cell_diameter=get_property_from_sample(
                                        sample, "Average diameter (μm)"
                                    ),
                                    average_live_cell_diameter__cell_counter_=get_property_from_sample(
                                        sample, "Average viable diameter (μm)"
                                    ),
                                    viable_cell_count=get_property_from_sample(
                                        sample, "Viable cells"
                                    ),
                                    average_total_cell_circularity=get_property_from_sample(
                                        sample, "Average circularity"
                                    ),
                                    average_viable_cell_circularity=get_property_from_sample(
                                        sample, "Average viable circularity"
                                    ),
                                ),
                            ]
                        ),
                    )
                ],
            ),
        )
