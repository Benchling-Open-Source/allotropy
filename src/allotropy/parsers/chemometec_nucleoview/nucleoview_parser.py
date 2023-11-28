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
from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parsers.chemometec_nucleoview.constants import (
    DEFAULT_ANALYST,
    DEFAULT_MODEL_NUMBER,
    NUCLEOCOUNTER_SOFTWARE_NAME,
)
from allotropy.parsers.chemometec_nucleoview.nucleoview_reader import NucleoviewReader
from allotropy.parsers.vendor_parser import VendorParser

_PROPERTY_LOOKUP = {
    "Cell count": TQuantityValueCell,
    "Dead (cells/ml)": TQuantityValueMillionCellsPerMilliliter,
    "Estimated cell diameter (um)": TQuantityValueMicrometer,
    "Live (cells/ml)": TQuantityValueMillionCellsPerMilliliter,
    "Multiplication factor": TQuantityValueUnitless,
    "Total (cells/ml)": TQuantityValueMillionCellsPerMilliliter,
    "Viability (%)": TQuantityValuePercent,
}


def get_property_from_sample(sample: pd.Series, property_name: str) -> Any:
    if (value := sample.get(property_name)) is not None:
        property_type = _PROPERTY_LOOKUP[property_name]

        # if the porperty type is measured in million cells per ml convert cells per ml
        if property_type == TQuantityValueMillionCellsPerMilliliter:
            return property_type(value=float(str(value)) / 1e6)

        return property_type(value=value)  # type: ignore[arg-type]
    # special case for cell count since nucleoview doesn't provide total cell count
    elif property_name == "Cell count":
        property_type = _PROPERTY_LOOKUP[property_name]
        return property_type(value=float("NaN"))
    else:
        return None


class ChemometecNucleoviewParser(VendorParser):
    def _parse(self, contents: io.IOBase, filename: str) -> Model:
        return self._get_model(NucleoviewReader.read(contents), filename)

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=self._get_device_identifier(data),
                    equipment_serial_number=self._get_device_serial_number(data),
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

    def _get_device_serial_number(
        self,
        data: pd.DataFrame,
    ) -> Optional[str]:
        try:
            return str(data["Instrument s/n"].iloc[0])
        except KeyError:
            return None

    def _get_device_identifier(
        self,
        data: pd.DataFrame,
    ) -> str:
        try:
            return str(data["Instrument type"].iloc[0])
        except KeyError:
            return DEFAULT_MODEL_NUMBER

    def _get_cell_counting_document(
        self, data: pd.DataFrame
    ) -> list[CellCountingDocumentItem]:
        return [
            self._get_cell_counting_document_item(sample)
            for _, sample in data.iterrows()
            if sample.get("Total (cells/ml)")
        ]

    def _get_sample_datetime(self, sample: pd.Series) -> Optional[TDateTimeValue]:
        time = sample.get("datetime")
        if time is not None:
            return self.get_date_time(time)
        return time

    def _get_cell_counting_document_item(
        self, sample: pd.Series
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=sample.get("Operator") or DEFAULT_ANALYST,  # type: ignore[arg-type]
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_identifier=str(uuid.uuid4()),
                        measurement_time=self._get_sample_datetime(sample),
                        sample_document=SampleDocument(sample_identifier=sample.get("Sample ID")),  # type: ignore[arg-type]
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
                                            sample, "Multiplication factor"
                                        ),
                                    ),
                                    viability__cell_counter_=get_property_from_sample(
                                        sample, "Viability (%)"
                                    ),
                                    viable_cell_density__cell_counter_=get_property_from_sample(
                                        sample, "Live (cells/ml)"
                                    ),
                                    dead_cell_density__cell_counter_=get_property_from_sample(
                                        sample, "Dead (cells/ml)"
                                    ),
                                    total_cell_density__cell_counter_=get_property_from_sample(
                                        sample, "Total (cells/ml)"
                                    ),
                                    average_total_cell_diameter=get_property_from_sample(
                                        sample, "Estimated cell diameter (um)"
                                    ),
                                    total_cell_count=get_property_from_sample(
                                        sample, "Cell count"
                                    ),
                                )
                            ]
                        ),
                    )
                ],
            ),
        )
