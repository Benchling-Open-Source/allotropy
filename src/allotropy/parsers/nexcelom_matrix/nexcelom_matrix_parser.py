from __future__ import annotations

from enum import Enum
from typing import Any

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
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.nexcelom_matrix.constants import EPOCH_STR
from allotropy.parsers.nexcelom_matrix.nexcelom_matrix_reader import (
    NexcelomMatrixReader,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class SampleProperty(Enum):
    LIVE_COUNT = ("Live Count", TQuantityValueCell)
    LIVE_MEAN_SIZE = ("Live Mean Size", TQuantityValueMicrometer)
    DEAD_COUNT = ("Dead Count", TQuantityValueCell)
    DEAD_CELLS_ML = ("Dead Cells/mL", TQuantityValueMillionCellsPerMilliliter)
    DEAD_MEAN_SIZE = ("Dead Mean Size", TQuantityValueMicrometer)
    TOTAL_COUNT = ("Total Count", TQuantityValueCell)
    TOTAL_CELLS_ML = ("Total Cells/mL", TQuantityValueMillionCellsPerMilliliter)
    TOTAL_MEAN_SIZE = ("Total Mean Size", TQuantityValueMicrometer)

    def __init__(self, column_name: str, data_type: Any) -> None:
        self.column_name: str = column_name
        self.data_type: Any = data_type


def get_property_from_sample(
    sample: pd.Series[Any], sample_property: SampleProperty
) -> Any:
    value = sample.get(sample_property.column_name)
    return sample_property.data_type(value=value) if value else None


class NexcelomMatrixParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        filename = named_file_contents.original_file_name
        # TODO: can we get filepath?
        reader = NexcelomMatrixReader(contents)

        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(),  # Empty reqs  # TODO do we leave empty documents in?
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    # software_name=SOFTWARE_NAME,  # TODO
                    # software_version=reader.file_version.value,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                cell_counting_document=[
                    self._get_cell_counting_document_item(sample)
                    for _, sample in reader.data.iterrows()
                ],
            ),
        )

    def _get_cell_counting_document_item(
        self, sample: pd.Series[Any]
    ) -> CellCountingDocumentItem:
        required_fields_list = [
            "Viability",
            "Live Cells/mL",
        ]
        # Required fields
        try:
            viability__cell_counter_ = TQuantityValuePercent(value=sample["Viability"])
            viable_cell_density__cell_counter_ = (
                TQuantityValueMillionCellsPerMilliliter(value=sample["Live Cells/mL"])
            )
        except KeyError as e:
            error = f"Expected to find lines with all of these headers: {required_fields_list}."
            raise AllotropeConversionError(error) from e

        return CellCountingDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_identifier=random_uuid_str(),
                        measurement_time=self._get_date_time(EPOCH_STR),
                        sample_document=SampleDocument(
                            sample_identifier=sample["Well Name"]
                        ),
                        device_control_aggregate_document=CellCountingDetectorDeviceControlAggregateDocument(
                            device_control_document=[
                                DeviceControlDocumentItemModel(
                                    device_type="cell counter"
                                )
                            ]
                        ),
                        processed_data_aggregate_document=ProcessedDataAggregateDocument1(
                            processed_data_document=[
                                ProcessedDataDocumentItem(
                                    data_processing_document=DataProcessingDocument(),  # TODO not needed? What do I do with notes and errors?
                                    viability__cell_counter_=viability__cell_counter_,
                                    viable_cell_density__cell_counter_=viable_cell_density__cell_counter_,
                                    total_cell_count=get_property_from_sample(
                                        sample, SampleProperty.TOTAL_COUNT
                                    ),
                                    total_cell_density__cell_counter_=get_property_from_sample(
                                        sample, SampleProperty.TOTAL_CELLS_ML
                                    ),
                                    average_total_cell_diameter=get_property_from_sample(
                                        sample, SampleProperty.TOTAL_MEAN_SIZE
                                    ),
                                    viable_cell_count=get_property_from_sample(
                                        sample, SampleProperty.LIVE_COUNT
                                    ),
                                    average_live_cell_diameter__cell_counter_=get_property_from_sample(
                                        sample, SampleProperty.LIVE_MEAN_SIZE
                                    ),
                                    dead_cell_count=get_property_from_sample(
                                        sample, SampleProperty.DEAD_COUNT
                                    ),
                                    dead_cell_density__cell_counter_=get_property_from_sample(
                                        sample, SampleProperty.DEAD_CELLS_ML
                                    ),
                                    average_dead_cell_diameter__cell_counter_=get_property_from_sample(
                                        sample, SampleProperty.DEAD_MEAN_SIZE
                                    ),
                                ),
                            ]
                        ),
                    )
                ],
            ),
        )
