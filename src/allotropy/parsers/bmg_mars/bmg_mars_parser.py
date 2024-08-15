from __future__ import annotations

from collections import defaultdict
from typing import Any, cast, TypeVar

import pandas as pd

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ContainerType,
    DataSystemDocument,
    DeviceControlDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    LuminescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    OpticalImagingMeasurementDocumentItems,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    SampleDocument,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import valid_value_or_raise
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.bmg_mars.bmg_mars_structure import (
    get_plate_data,
    get_plate_well_count,
    Header,
    ReadType,
    Wavelength,
)
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser

MeasurementDocumentItems = (
    FluorescencePointDetectionMeasurementDocumentItems
    | UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    | OpticalImagingMeasurementDocumentItems
    | LuminescencePointDetectionMeasurementDocumentItems
)

DeviceControlAggregateDocument = (
    FluorescencePointDetectionDeviceControlAggregateDocument
    | UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument
)

T = TypeVar("T")


def safe_value(cls: type[T], value: Any | None) -> T | None:
    return None if value is None else cls(value=value)  # type: ignore[call-arg]


class BmgMarsParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "BMG MARS"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        filename = named_file_contents.original_file_name
        lines = read_to_lines(named_file_contents)
        read_type = self._get_read_type(lines)

        reader = LinesReader(lines)
        raw_header = list(reader.pop_until("^,?Raw Data"))
        header = Header.create(raw_header)

        csv_data = list(reader.pop_until_empty())
        wavelength = Wavelength.create(csv_data)
        plate_well_count = get_plate_well_count(csv_data)
        data = get_plate_data(csv_data)

        return self._get_model(
            header,
            data,
            filename,
            read_type,
            wavelength,
            plate_well_count,
        )

    def _get_model(
        self,
        header: Header,
        data: pd.DataFrame,
        filename: str,
        read_type: ReadType,
        wavelength: Wavelength,
        plate_well_count: TQuantityValueNumber,
    ) -> Model:

        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                plate_reader_document=self._get_plate_reader_document(
                    data, read_type, header, wavelength, plate_well_count
                ),
                device_system_document=DeviceSystemDocument(
                    device_identifier="N/A",
                    model_number="N/A",
                    product_manufacturer="BMG LABTECH",
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    UNC_path=header.path,
                    software_name="BMG MARS",
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
            ),
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
        )

    def _get_read_type(self, lines: list[str]) -> ReadType:
        content = "\n".join(lines).lower()
        read_types = {
            read_type for read_type in ReadType if read_type.value.lower() in content
        }
        return valid_value_or_raise("read type", read_types, ReadType)

    def _get_device_control_aggregate_document(
        self,
        wavelength: Wavelength,
        read_type: ReadType,
    ) -> DeviceControlAggregateDocument:

        if read_type == ReadType.ABSORBANCE:
            return UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type="absorbance detector",
                        detection_type="absorbance",
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=wavelength.wavelength
                        ),
                    )
                ]
            )

        elif read_type == ReadType.FLUORESCENCE:
            return FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    FluorescencePointDetectionDeviceControlDocumentItem(
                        device_type="fluorescence detector",
                        detection_type="fluorescence",
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=wavelength.wavelength
                        ),
                        excitation_wavelength_setting=TQuantityValueNanometer(
                            value=wavelength.ex_wavelength
                        ),
                    )
                ]
            )

    def _get_measurement_document(
        self,
        read_type: ReadType,
        header: Header,
        result: pd.Series[Any],
        device_control_document: list[DeviceControlDocument],
    ) -> MeasurementDocumentItems:
        plate_barcode = header.id1
        well_location = f"{result.row}{result.col}"
        sample_document = SampleDocument(
            sample_identifier=f"{plate_barcode} {well_location}",
            location_identifier=well_location,
            well_plate_identifier=plate_barcode,
        )
        if read_type == ReadType.ABSORBANCE:
            return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                measurement_identifier=result.uuid,
                sample_document=sample_document,
                device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                    device_control_document=cast(
                        list[
                            UltravioletAbsorbancePointDetectionDeviceControlDocumentItem
                        ],
                        device_control_document,
                    )
                ),
                absorbance=TQuantityValueMilliAbsorbanceUnit(value=result.value),
            )
        elif read_type == ReadType.FLUORESCENCE:
            return FluorescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=result.uuid,
                sample_document=sample_document,
                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=cast(
                        list[FluorescencePointDetectionDeviceControlDocumentItem],
                        device_control_document,
                    )
                ),
                fluorescence=TQuantityValueRelativeFluorescenceUnit(value=result.value),
            )

    def _get_plate_reader_document(
        self,
        data: pd.DataFrame,
        read_type: ReadType,
        header: Header,
        wavelength: Wavelength,
        plate_well_count: TQuantityValueNumber,
    ) -> list[PlateReaderDocumentItem]:
        items = []
        measurement_docs_dict = defaultdict(list)
        measurement_time = self._get_date_time(f"{header.date} {header.time}")
        device_control_aggregate_document = self._get_device_control_aggregate_document(
            wavelength, read_type
        )

        for _, result in data.iterrows():
            measurement_docs_dict[(result.row, result.col)].append(
                self._get_measurement_document(
                    read_type,
                    header,
                    result,
                    cast(
                        list[DeviceControlDocument],
                        device_control_aggregate_document.device_control_document,
                    ),
                )
            )

        for well_location in sorted(measurement_docs_dict.keys()):
            items.append(
                PlateReaderDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_time=measurement_time,
                        plate_well_count=plate_well_count,
                        measurement_document=measurement_docs_dict[well_location],
                        experiment_type=header.test_name,
                        experimental_data_identifier=header.id2,
                        container_type=ContainerType.well_plate,
                    ),
                    analyst=header.user,
                )
            )

        return items
