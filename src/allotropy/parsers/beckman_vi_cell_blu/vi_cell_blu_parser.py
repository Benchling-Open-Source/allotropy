from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import numpy as np
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
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_blu.constants import (
    DEFAULT_ANALYST,
    DEFAULT_MODEL_NUMBER,
    VICELL_BLU_SOFTWARE_NAME,
)
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_reader import ViCellBluReader
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class SampleProperty(Enum):
    AVERAGE_VIABLE_DIAMETER = ("Average viable diameter (μm)", TQuantityValueMicrometer)
    AVERAGE_CIRCULARITY = ("Average circularity", TQuantityValueUnitless)
    AVERAGE_DIAMETER = ("Average diameter (μm)", TQuantityValueMicrometer)
    AVERAGE_VIABLE_CIRCULARITY = ("Average viable circularity", TQuantityValueUnitless)
    DILUTION = ("Dilution", TQuantityValueUnitless)
    MAXIMUM_DIAMETER = ("Maximum Diameter (μm)", TQuantityValueMicrometer)
    MINIMUM_DIAMETER = ("Minimum Diameter (μm)", TQuantityValueMicrometer)
    CELL_COUNT = ("Cell count", TQuantityValueCell)
    TOTAL_CELLS_ML = ("Total (x10^6) cells/mL", TQuantityValueMillionCellsPerMilliliter)
    VIABILITY = ("Viability (%)", TQuantityValuePercent)
    VIABLE_CELLS = ("Viable cells", TQuantityValueCell)
    VIABLE_CELLS_ML = (
        "Viable (x10^6) cells/mL",
        TQuantityValueMillionCellsPerMilliliter,
    )

    def __init__(self, column_name: str, data_type: Any) -> None:
        self.column_name: str = column_name
        self.data_type: Any = data_type


@dataclass(frozen=True)
class _Sample:
    data_frame: pd.DataFrame
    row: int

    def get_value(self, column: str) -> Optional[Any]:
        if column not in self.data_frame.columns:
            return None
        value = self.data_frame[column][self.row]

        # https://stackoverflow.com/questions/50916422/python-typeerror-object-of-type-int64-is-not-json-serializable
        if isinstance(value, np.int64):
            return int(value)

        return value

    def get_value_not_none(self, column: str) -> Any:
        value = self.get_value(column)
        if value is None:
            msg = f"Missing value for column '{column}'."
            raise AllotropeConversionError(msg)
        return value

    def get_property_value(self, sample_property: SampleProperty) -> Any:
        return (
            sample_property.data_type(value=value)
            if (value := self.get_value(sample_property.column_name))
            else None
        )


class ViCellBluParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        filename = named_file_contents.original_file_name
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
            self._get_cell_counting_document_item(_Sample(data, i))
            for i in range(len(data.index))
            if (_Sample(data, i).get_value("Cell count"))
        ]

    def _get_cell_counting_document_item(
        self, sample: _Sample
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=sample.get_value("Analysis by") or DEFAULT_ANALYST,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_time=self._get_date_time(
                            sample.get_value_not_none("Analysis date/time")
                        ),
                        measurement_identifier=random_uuid_str(),
                        sample_document=SampleDocument(sample_identifier=sample.get_value("Sample ID")),  # type: ignore[arg-type]
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
                                        cell_type_processing_method=sample.get_value(
                                            "Cell type"
                                        ),
                                        minimum_cell_diameter_setting=sample.get_property_value(
                                            SampleProperty.MINIMUM_DIAMETER
                                        ),
                                        maximum_cell_diameter_setting=sample.get_property_value(
                                            SampleProperty.MAXIMUM_DIAMETER
                                        ),
                                        cell_density_dilution_factor=sample.get_property_value(
                                            SampleProperty.DILUTION
                                        ),
                                    ),
                                    viability__cell_counter_=sample.get_property_value(
                                        SampleProperty.VIABILITY
                                    ),
                                    viable_cell_density__cell_counter_=sample.get_property_value(
                                        SampleProperty.VIABLE_CELLS_ML
                                    ),
                                    total_cell_count=sample.get_property_value(
                                        SampleProperty.CELL_COUNT
                                    ),
                                    total_cell_density__cell_counter_=sample.get_property_value(
                                        SampleProperty.TOTAL_CELLS_ML
                                    ),
                                    average_total_cell_diameter=sample.get_property_value(
                                        SampleProperty.AVERAGE_DIAMETER
                                    ),
                                    average_live_cell_diameter__cell_counter_=sample.get_property_value(
                                        SampleProperty.AVERAGE_VIABLE_DIAMETER
                                    ),
                                    viable_cell_count=sample.get_property_value(
                                        SampleProperty.VIABLE_CELLS
                                    ),
                                    average_total_cell_circularity=sample.get_property_value(
                                        SampleProperty.AVERAGE_CIRCULARITY
                                    ),
                                    average_viable_cell_circularity=sample.get_property_value(
                                        SampleProperty.AVERAGE_VIABLE_CIRCULARITY
                                    ),
                                ),
                            ]
                        ),
                    )
                ],
            ),
        )
