import io
from typing import Any
import uuid

import pandas as pd

from allotropy.allotrope.models.cell_counter_benchling_2023_09_cell_counter import (
    CellCountingAggregateDocument,
    CellCountingDocumentItem,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataDocument,
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


def get_property_from_sample(sample: pd.Series, property_name: str) -> Any:
    return property_lookup[property_name](value=value) if (value := sample.get(property_name)) else None  # type: ignore[arg-type]


class ViCellBluParser(VendorParser):
    def _parse(self, contents: io.IOBase, filename: str) -> Model:
        return self._get_model(ViCellBluReader.read(contents), filename)

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        return Model(
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
            if sample.get("Cell count")
        ]

    def _get_cell_counting_document_item(
        self, sample: pd.Series
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=sample.get("Analysis by") or DEFAULT_ANALYST,  # type: ignore[arg-type]
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    MeasurementDocumentItem(
                        measurement_identifier=str(uuid.uuid4()),
                        measurement_time=self.get_date_time(
                            sample.get("Analysis date/time")
                        ),
                        sample_document=SampleDocument(sample_identifier=sample.get("Sample ID")),  # type: ignore[arg-type]
                        device_control_aggregate_document=DeviceControlAggregateDocument(
                            device_control_document=[
                                DeviceControlDocumentItem(
                                    device_type="brightfield imager (cell counter)",
                                    detection_type="brightfield",
                                )
                            ]
                        ),
                        processed_data_document=ProcessedDataDocument(
                            data_processing_document=DataProcessingDocument(
                                cell_type_processing_method=sample.get("Cell type"),  # type: ignore[arg-type]
                                minimum_cell_diameter=get_property_from_sample(
                                    sample, "Minimum Diameter (μm)"
                                ),
                                maximum_cell_diameter=get_property_from_sample(
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
                    )
                ],
            ),
        )
