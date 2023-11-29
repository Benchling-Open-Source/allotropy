from __future__ import annotations

import io
from typing import Any, Optional
import uuid

import pandas as pd

from allotropy.allotrope.allotrope import AllotropeConversionError
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
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DATE_HEADER,
    DEFAULT_ANALYST,
    MODEL_NUMBER,
    SOFTWARE_NAME,
    XrVersion,
)
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import ViCellXRReader
from allotropy.parsers.vendor_parser import VendorParser

property_lookup = {
    "Dilution factor": TQuantityValueUnitless,
    "Total cells/ml (x10^6)": TQuantityValueMillionCellsPerMilliliter,
    "Avg. diam. (microns)": TQuantityValueMicrometer,
    "Viable cells": TQuantityValueCell,
    "Avg. circ.": TQuantityValueUnitless,
}


def get_property_from_sample(sample: pd.Series[Any], property_name: str) -> Any:
    return property_lookup[property_name](value=value) if (value := sample.get(property_name)) else None  # type: ignore[arg-type]


class ViCellXRParser(VendorParser):
    def _parse(self, contents: io.IOBase, filename: str) -> Model:
        reader = ViCellXRReader(contents)

        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=MODEL_NUMBER,
                    equipment_serial_number=self._get_device_serial_number(
                        reader.file_info
                    ),
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=SOFTWARE_NAME,
                    software_version=reader.file_version.value,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                cell_counting_document=[
                    self._get_cell_counting_document_item(sample, reader.file_version)
                    for _, sample in reader.data.iterrows()
                ],
            ),
        )

    def _get_device_serial_number(self, file_info: pd.Series[Any]) -> Optional[str]:
        serial = str(file_info["serial"])
        try:
            serial_number = serial[serial.rindex(":") + 1 :].strip()
        except ValueError:
            return None

        return serial_number

    def _get_cell_counting_document_item(
        self, sample: pd.Series[Any], file_version: XrVersion
    ) -> CellCountingDocumentItem:
        # Required fields
        try:
            viability__cell_counter_ = TQuantityValuePercent(
                value=sample["Viability (%)"]
            )
            total_cell_count = TQuantityValueCell(value=sample["Total cells"])
            viable_cell_density__cell_counter_ = (
                TQuantityValueMillionCellsPerMilliliter(
                    value=sample["Viable cells/ml (x10^6)"]
                )
            )
        except KeyError as e:
            error = f"required value not found {e}"
            raise AllotropeConversionError(error) from e

        return CellCountingDocumentItem(
            analyst=DEFAULT_ANALYST,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_identifier=str(uuid.uuid4()),
                        measurement_time=self.get_date_time(
                            sample.get(DATE_HEADER[file_version])
                        ),
                        sample_document=SampleDocument(
                            sample_identifier=sample["Sample ID"]
                        ),
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
                                        cell_type_processing_method=sample.get("Cell type"),  # type: ignore[arg-type]
                                        cell_density_dilution_factor=get_property_from_sample(
                                            sample, "Dilution factor"
                                        ),
                                    ),
                                    viability__cell_counter_=viability__cell_counter_,
                                    viable_cell_density__cell_counter_=viable_cell_density__cell_counter_,
                                    total_cell_count=total_cell_count,
                                    total_cell_density__cell_counter_=get_property_from_sample(
                                        sample, "Total cells/ml (x10^6)"
                                    ),
                                    average_total_cell_diameter=get_property_from_sample(
                                        sample, "Avg. diam. (microns)"
                                    ),
                                    viable_cell_count=get_property_from_sample(
                                        sample, "Viable cells"
                                    ),
                                    average_total_cell_circularity=get_property_from_sample(
                                        sample, "Avg. circ."
                                    ),
                                ),
                            ]
                        ),
                    )
                ],
            ),
        )
