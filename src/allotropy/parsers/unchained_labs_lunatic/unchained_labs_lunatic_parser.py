from __future__ import annotations

import uuid

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
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_reader import (
    UnchainedLabsLunaticReader,
)
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_structure import (
    Data,
    Measurement,
    WellPlate,
)
from allotropy.parsers.vendor_parser import VendorParser


class UnchainedLabsLunaticParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        raw_contents, filename = named_file_contents
        reader = UnchainedLabsLunaticReader(raw_contents)
        return self._get_model(Data.create(reader.data), filename)

    def _get_model(self, data: Data, filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.device_identifier,
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
                    for plate in data.well_plate_list
                ],
            ),
        )

    def _get_plate_reader_document_item(
        self, plate: WellPlate
    ) -> PlateReaderDocumentItem:
        return PlateReaderDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(plate.measurement_time),
                analytical_method_identifier=plate.analytical_method_identifier,
                container_type=ContainerType.well_plate,
                plate_well_count=TQuantityValueNumber(value=96),
                measurement_document=[
                    self._get_measurement_document_item(measurement)
                    for measurement in plate.measurements
                ],
            )
        )

    def _get_measurement_document_item(
        self, measurement: Measurement
    ) -> UltravioletAbsorbancePointDetectionMeasurementDocumentItems:
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=str(uuid.uuid4()),
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type="plate reader",
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=measurement.wavelenght
                        ),
                    )
                ]
            ),
            absorbance=TQuantityValueMilliAbsorbanceUnit(value=measurement.absorbance),
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                location_identifier=measurement.location_identifier,
                well_plate_identifier=measurement.well_plate_identifier,
            ),
        )
