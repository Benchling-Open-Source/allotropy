from __future__ import annotations

from typing import Optional

import numpy as np

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    ContainerType,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
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
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.pandas_util import read_csv
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_structure import (
    Data,
    Measurement,
    WellPlate,
)
from allotropy.parsers.vendor_parser import VendorParser


class UnchainedLabsLunaticParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        raw_contents = named_file_contents.contents
        data = read_csv(filepath_or_buffer=raw_contents).replace(np.nan, None)

        filename = named_file_contents.original_file_name
        return self._get_model(Data.create(data), filename)

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
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data
                ),
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
            measurement_identifier=measurement.identifier,
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type="plate reader",
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=measurement.wavelength
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

    def _get_calculated_data_aggregate_document(
        self, data: Data
    ) -> Optional[CalculatedDataAggregateDocument]:
        if not (calculated_data_document := data.get_calculated_data_document()):
            return None

        return CalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calculated_data_item.identifier,
                    calculated_data_name=calculated_data_item.name,
                    calculated_result=TQuantityValue(
                        value=calculated_data_item.value,
                        unit=calculated_data_item.unit,
                    ),
                    data_source_aggregate_document=DataSourceAggregateDocument(
                        data_source_document=[
                            DataSourceDocumentItem(
                                data_source_identifier=item.identifier,
                                data_source_feature=item.feature,
                            )
                            for item in calculated_data_item.data_source_document
                        ]
                    ),
                )
                for calculated_data_item in calculated_data_document
            ]
        )
