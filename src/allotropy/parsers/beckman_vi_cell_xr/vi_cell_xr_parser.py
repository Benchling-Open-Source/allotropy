from __future__ import annotations

from enum import Enum
import tempfile
from typing import Any, Optional
import zipfile

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
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DATE_HEADER,
    DEFAULT_ANALYST,
    MODEL_NUMBER,
    SOFTWARE_NAME,
    XrVersion,
)
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import ViCellXRReader
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser
from allotropy.types import IOType


class SampleProperty(Enum):
    DILUTION_FACTOR = ("Dilution factor", TQuantityValueUnitless)
    TOTAL_CELLS_ML = ("Total cells/ml (x10^6)", TQuantityValueMillionCellsPerMilliliter)
    TOTAL_CELLS = ("Total cells", TQuantityValueCell)
    AVERAGE_DIAMETER = ("Avg. diam. (microns)", TQuantityValueMicrometer)
    VIABLE_CELLS = ("Viable cells", TQuantityValueCell)
    AVERAGE_CIRCULARITY = ("Avg. circ.", TQuantityValueUnitless)

    def __init__(self, column_name: str, data_type: Any) -> None:
        self.column_name: str = column_name
        self.data_type: Any = data_type


def get_property_from_sample(
    sample: pd.Series[Any], sample_property: SampleProperty
) -> Any:
    value = sample.get(sample_property.column_name)
    return sample_property.data_type(value=value) if value else None


def remove_style_xml_file(contents: IOType) -> IOType:
    # Removes styles.xml from an xlsx file IO stream. xlsx files produced by VI-Cell XR
    # instrument may have an invalid <fill> tag in their styles.xml file which causes a
    # bug when reading with pandas (via openpyxl library).

    # zipfile only accepts a filename, so write contents to a named temp file.
    tmp = tempfile.NamedTemporaryFile()
    file_contents = contents.read()
    if isinstance(file_contents, str):
        file_contents = file_contents.encode()
    tmp.write(file_contents)

    # Write zip contents to a new file, skipping styles.xml
    new = tempfile.NamedTemporaryFile()
    with zipfile.ZipFile(tmp.name) as zin:
        with zipfile.ZipFile(new.name, "w") as zout:
            for item in zin.infolist():
                if item.filename == "xl/styles.xml":
                    continue
                zout.writestr(item, zin.read(item.filename))

    return open(new.name, "rb")


class ViCellXRParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        filename = named_file_contents.original_file_name

        if filename.endswith("xlsx"):
            contents = remove_style_xml_file(contents)
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
        required_fields_list = [
            "Viability (%)",
            "Viable cells/ml (x10^6)",
        ]
        # Required fields
        try:
            viability__cell_counter_ = TQuantityValuePercent(
                value=sample["Viability (%)"]
            )
            viable_cell_density__cell_counter_ = (
                TQuantityValueMillionCellsPerMilliliter(
                    value=sample["Viable cells/ml (x10^6)"]
                )
            )
        except KeyError as e:
            error = f"Expected to find lines with all of these headers: {required_fields_list}."
            raise AllotropeConversionError(error) from e

        return CellCountingDocumentItem(
            analyst=DEFAULT_ANALYST,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_identifier=random_uuid_str(),
                        measurement_time=self._get_date_time(
                            str(sample.get(DATE_HEADER[file_version]))
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
                                            sample,
                                            SampleProperty.DILUTION_FACTOR,
                                        ),
                                    ),
                                    viability__cell_counter_=viability__cell_counter_,
                                    viable_cell_density__cell_counter_=viable_cell_density__cell_counter_,
                                    total_cell_count=get_property_from_sample(
                                        sample, SampleProperty.TOTAL_CELLS
                                    ),
                                    total_cell_density__cell_counter_=get_property_from_sample(
                                        sample, SampleProperty.TOTAL_CELLS_ML
                                    ),
                                    average_total_cell_diameter=get_property_from_sample(
                                        sample, SampleProperty.AVERAGE_DIAMETER
                                    ),
                                    viable_cell_count=get_property_from_sample(
                                        sample, SampleProperty.VIABLE_CELLS
                                    ),
                                    average_total_cell_circularity=get_property_from_sample(
                                        sample, SampleProperty.AVERAGE_CIRCULARITY
                                    ),
                                ),
                            ]
                        ),
                    )
                ],
            ),
        )
