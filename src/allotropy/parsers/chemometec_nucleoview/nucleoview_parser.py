from typing import Any, Optional

import pandas as pd
from pandas import Timestamp

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
    TQuantityValueMicrometer,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    TDateTimeValue,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.chemometec_nucleoview.constants import (
    DEFAULT_ANALYST,
    DEFAULT_MODEL_NUMBER,
    NUCLEOCOUNTER_SOFTWARE_NAME,
)
from allotropy.parsers.chemometec_nucleoview.nucleoview_reader import NucleoviewReader
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

_PROPERTY_LOOKUP = {
    "Dead (cells/ml)": TQuantityValueMillionCellsPerMilliliter,
    "Estimated cell diameter (um)": TQuantityValueMicrometer,
    "Live (cells/ml)": TQuantityValueMillionCellsPerMilliliter,
    "Multiplication factor": TQuantityValueUnitless,
    "Total (cells/ml)": TQuantityValueMillionCellsPerMilliliter,
    "Viability (%)": TQuantityValuePercent,
}


def _get_value(data_frame: pd.DataFrame, row: int, column: str) -> Optional[Any]:
    if column not in data_frame.columns:
        return None
    return data_frame[column][row]


def get_property_from_sample(
    data_frame: pd.DataFrame, row: int, property_name: str
) -> Optional[Any]:
    value = _get_value(data_frame, row, property_name)
    if value is None:
        return None

    property_type = _PROPERTY_LOOKUP[property_name]

    try:
        value = float(value)
    except ValueError:
        return property_type(value=InvalidJsonFloat.NaN)

    # if the porperty type is measured in million cells per ml convert cells per ml
    if property_type == TQuantityValueMillionCellsPerMilliliter:
        return property_type(value=float(value) / 1e6)

    return property_type(value=float(value))


class ChemometecNucleoviewParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        filename = named_file_contents.original_file_name
        return self._get_model(NucleoviewReader.read(contents), filename)

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=_get_value(data, 0, "Instrument type")
                    or DEFAULT_MODEL_NUMBER,
                    equipment_serial_number=_get_value(data, 0, "Instrument s/n"),
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=NUCLEOCOUNTER_SOFTWARE_NAME,
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
            self._get_cell_counting_document_item(data, i)
            for i in range(len(data.index))
            if _get_value(data, i, "Total (cells/ml)")
        ]

    def _get_date_time_or_epoch(self, time_val: Optional[Timestamp]) -> TDateTimeValue:
        if time_val is None:
            # return epoch time 1970-01-01
            return self._get_date_time("1970-01-01")
        return self._get_date_time_from_timestamp(time_val)

    def _get_cell_counting_document_item(
        self, data_frame: pd.DataFrame, row: int
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=_get_value(data_frame, row, "Operator") or DEFAULT_ANALYST,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_identifier=random_uuid_str(),
                        measurement_time=self._get_date_time_or_epoch(
                            _get_value(data_frame, row, "datetime")
                        ),
                        sample_document=SampleDocument(
                            sample_identifier=str(
                                _get_value(data_frame, row, "Sample ID")
                            )
                        ),
                        device_control_aggregate_document=CellCountingDetectorDeviceControlAggregateDocument(
                            device_control_document=[
                                DeviceControlDocumentItemModel(
                                    device_type="dark field imager (cell counter)",
                                    detection_type="dark field",
                                )
                            ]
                        ),
                        processed_data_aggregate_document=ProcessedDataAggregateDocument1(
                            processed_data_document=[
                                ProcessedDataDocumentItem(
                                    data_processing_document=DataProcessingDocument(
                                        cell_density_dilution_factor=get_property_from_sample(
                                            data_frame, row, "Multiplication factor"
                                        ),
                                    ),
                                    viability__cell_counter_=get_property_from_sample(  # type: ignore[arg-type]
                                        data_frame, row, "Viability (%)"
                                    ),
                                    viable_cell_density__cell_counter_=get_property_from_sample(  # type: ignore[arg-type]
                                        data_frame, row, "Live (cells/ml)"
                                    ),
                                    dead_cell_density__cell_counter_=get_property_from_sample(
                                        data_frame, row, "Dead (cells/ml)"
                                    ),
                                    total_cell_density__cell_counter_=get_property_from_sample(
                                        data_frame, row, "Total (cells/ml)"
                                    ),
                                    average_total_cell_diameter=get_property_from_sample(
                                        data_frame, row, "Estimated cell diameter (um)"
                                    ),
                                )
                            ]
                        ),
                    )
                ],
            ),
        )
