from io import IOBase
import uuid

import pandas as pd

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
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
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_reader import (
    UnchainedLabsLunaticReader,
)
from allotropy.parsers.utils.values import assert_not_none
from allotropy.parsers.vendor_parser import VendorParser


def get_device_identifier(data: pd.DataFrame) -> str:
    device_identifier = assert_not_none(data.get("Instrument ID"), 'Instrument ID')

    return str(device_identifier[0])


def get_datetime_from_plate(plate: pd.Series) -> str:
    date = assert_not_none(plate.get("Date"), "Date")
    time = assert_not_none(plate.get("Time"), "Time")

    return f"{date} {time}"


class UnchainedLabsLunaticParser(VendorParser):
    def _parse(self, raw_contents: IOBase, filename: str) -> Model:
        reader = UnchainedLabsLunaticReader(raw_contents)
        return self._get_model(reader.data, filename)

    def _get_model(self, data: pd.DataFrame, filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=get_device_identifier(data),
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
                    self._get_plate_reader_document_item(plate)
                    for _, plate in data.iterrows()
                ],
            ),
        )

    def _get_plate_reader_document_item(
        self, plate: pd.Series
    ) -> PlateReaderDocumentItem:
        measurement_time = get_datetime_from_plate(plate)
        wavelenght = self._get_wavelength_setting()
        return PlateReaderDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self.get_date_time(measurement_time),
                analytical_method_identifier=plate.get("Application"),
                container_type="well plate",
                plate_well_count=TQuantityValueNumber(value=96),
                measurement_document=[
                    # TODO: There should be one measurement document item for each wavelenght recorded in
                    # the output file.
                    UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
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
                            value=plate.get(f"A{wavelenght}")
                        ),
                        sample_document=SampleDocument(
                            sample_identifier=assert_not_none(plate.get("Sample name")),
                            location_identifier=assert_not_none(
                                plate.get("Plate ID"), "Plate ID"
                            ),
                            well_plate_identifier=assert_not_none(
                                plate.get("Plate Position"), "Plate Position"
                            ),
                        ),
                    )
                ],
            )
        )

    def _get_wavelength_setting(self) -> int:
        return 260
