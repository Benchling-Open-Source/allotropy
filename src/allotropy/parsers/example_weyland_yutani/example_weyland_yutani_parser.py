from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    ContainerType,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
)
from allotropy.allotrope.models.shared.components.plate_reader import (
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.example_weyland_yutani.example_weyland_yutani_structure import (
    Data,
)
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class ExampleWeylandYutaniParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        return self._get_model(Data.create(reader))

    def _get_model(self, data: Data) -> Model:
        if data.number_of_wells is None:
            msg = "Unable to determine the number of wells in the plate."
            raise AllotropeConversionError(msg)

        return Model(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_identifier=random_uuid_str(),
                measurement_time=self._get_measurement_time(data),
                analytical_method_identifier=data.basic_assay_info.protocol_id,
                experimental_data_identifier=data.basic_assay_info.assay_id,
                container_type=ContainerType.well_plate,
                plate_well_count=TQuantityValueNumber(value=data.number_of_wells),
                device_system_document=DeviceSystemDocument(
                    model_number=data.instrument.serial_number,
                    device_identifier=data.instrument.nickname,
                ),
                measurement_document=self._get_measurement_document(data),
            )
        )

    # TODO: extract and return actual measurement time
    def _get_measurement_time(self, data: Data) -> TDateTimeValue:  # noqa: ARG002
        return self._get_date_time("2022-12-31")

    def _get_measurement_document(self, data: Data) -> list[MeasurementDocumentItem]:
        device_control_aggregate_document = (
            self._get_device_control_aggregate_document()
        )
        return [
            MeasurementDocumentItem(
                sample_document=SampleDocument(
                    well_location_identifier=f"{result.col}{result.row}"
                ),
                device_control_aggregate_document=device_control_aggregate_document,
                processed_data_aggregate_document=ProcessedDataAggregateDocument(
                    processed_data_document=[
                        ProcessedDataDocumentItem(
                            processed_data=result.value,
                            data_processing_description="processed data",
                        ),
                    ]
                ),
            )
            for result in data.plates[0].results
        ]

    def _get_device_control_aggregate_document(self) -> DeviceControlAggregateDocument:
        return DeviceControlAggregateDocument(
            [
                DeviceControlDocumentItem(
                    device_type="fluorescence detector",
                )
            ]
        )
