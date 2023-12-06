from __future__ import annotations

from typing import Any
import uuid

import pandas as pd

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ContainerType,
    DataSystemDocument,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    Model,
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
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.unchained_labs_lunatic.constants import (
    NO_DATE_OR_TIME_ERROR_MSG,
    NO_WAVELENGHT_COLUMN_ERROR_MSG,
    WAVELENGHT_COLUMNS_RE,
)
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_reader import (
    UnchainedLabsLunaticReader,
)
from allotropy.parsers.utils.values import assert_not_none
from allotropy.parsers.vendor_parser import VendorParser


def _get_device_identifier(data: pd.Series[Any]) -> str:
    device_identifier = assert_not_none(data.get("Instrument ID"), "Instrument ID")

    return str(device_identifier)


def _get_datetime_from_plate(plate: pd.Series[Any]) -> str:
    date = plate.get("Date")
    time = plate.get("Time")

    if not date or not time:
        raise AllotropeConversionError(NO_DATE_OR_TIME_ERROR_MSG)

    return f"{date} {time}"


class UnchainedLabsLunaticParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        raw_contents, filename = named_file_contents
        reader = UnchainedLabsLunaticReader(raw_contents)
        return self._get_model(reader.data, filename)

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        wavelenght_columns = list(filter(WAVELENGHT_COLUMNS_RE.match, data.columns))
        if not wavelenght_columns:
            raise AllotropeConversionError(NO_WAVELENGHT_COLUMN_ERROR_MSG)
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=_get_device_identifier(data.iloc[0]),
                    model_number="Lunatic",
                    product_manufacturer="Unchained Labs",
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name="Lunatic and Stunner Analysis",
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                plate_reader_document=[
                    self._get_plate_reader_document_item(
                        data.iloc[i], wavelenght_columns
                    )
                    for i in range(len(data.index))
                ],
            ),
        )

    def _get_plate_reader_document_item(
        self, plate: pd.Series[Any], wavelenght_columns: list[str]
    ) -> PlateReaderDocumentItem:
        measurement_time = _get_datetime_from_plate(plate)

        return PlateReaderDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(measurement_time),
                analytical_method_identifier=plate.get("Application"),  # type: ignore[arg-type]
                container_type=ContainerType.well_plate,
                plate_well_count=TQuantityValueNumber(value=96),
                measurement_document=[
                    self._get_measurement_document_item(plate, wavelenght_column)
                    for wavelenght_column in wavelenght_columns
                ],
            )
        )

    def _get_measurement_document_item(
        self, plate: pd.Series[Any], wavelenght_column: str
    ) -> UltravioletAbsorbancePointDetectionMeasurementDocumentItems:
        wavelenght = float(wavelenght_column[1:])
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=str(uuid.uuid4()),
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type="plate reader",
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=wavelenght
                        ),
                    )
                ]
            ),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=plate.get(wavelenght_column)  # type: ignore[arg-type]
            ),
            sample_document=SampleDocument(
                sample_identifier=plate.get("Sample name"),  # type: ignore[arg-type]
                location_identifier=assert_not_none(plate.get("Plate ID"), "Plate ID"),  # type: ignore[arg-type]
                well_plate_identifier=assert_not_none(plate.get("Plate Position"), "Plate Position"),  # type: ignore[arg-type]
            ),
        )
