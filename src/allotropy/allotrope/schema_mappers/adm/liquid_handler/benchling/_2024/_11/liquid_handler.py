from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    LiquidHandlerAggregateDocument,
    LiquidHandlerDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class Error:
    error: str
    feature: str | None = None


@dataclass(frozen=True)
class Device:
    identifier: str
    serial_number: str
    product_manufacturer: str
    device_type: str


@dataclass(frozen=True)
class Measurement:
    # Measurement metadata
    identifier: str
    measurement_time: str
    sample_identifier: str

    # Optional metadata
    source_plate: str | None = None
    source_well: str | None = None
    source_location: str | None = None
    destination_plate: str | None = None
    destination_well: str | None = None
    destination_location: str | None = None

    # Measurements
    aspiration_volume: float | None = None
    transfer_volume: float | None = None

    # Optional settings
    injection_volume_setting: float | None = None

    # Errors
    errors: list[Error] | None = None

    custom_info: dict[str, Any] | None = None
    device_control_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    analyst: str
    measurements: list[Measurement]
    analytical_method_identifier: str | None = None
    experimental_data_identifier: str | None = None

    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Metadata:
    asm_file_identifier: str
    data_system_instance_identifier: str
    file_name: str
    unc_path: str
    device_type: str
    software_name: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None
    model_number: str | None = None
    devices: list[Device] | None = None

    custom_info: dict[str, Any] | None = None
    device_system_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/liquid-handler/BENCHLING/2024/11/liquid-handler.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            liquid_handler_aggregate_document=add_custom_information_document(
                LiquidHandlerAggregateDocument(
                    liquid_handler_document=[
                        self._get_technique_document(group, data.metadata)
                        for group in data.measurement_groups
                    ],
                    device_system_document=add_custom_information_document(
                        DeviceSystemDocument(
                            equipment_serial_number=data.metadata.equipment_serial_number,
                            product_manufacturer=data.metadata.product_manufacturer,
                            model_number=data.metadata.model_number,
                            device_document=[
                                DeviceDocumentItem(
                                    device_type=device.device_type,
                                    device_identifier=device.identifier,
                                    equipment_serial_number=device.serial_number,
                                    product_manufacturer=device.product_manufacturer,
                                )
                                for device in data.metadata.devices
                            ]
                            if data.metadata.devices
                            else None,
                        ),
                        data.metadata.device_system_custom_info,
                    ),
                    data_system_document=DataSystemDocument(
                        ASM_file_identifier=data.metadata.asm_file_identifier,
                        file_name=data.metadata.file_name,
                        UNC_path=data.metadata.unc_path,
                        data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                        software_name=data.metadata.software_name,
                        ASM_converter_name=self.converter_name,
                        ASM_converter_version=ASM_CONVERTER_VERSION,
                        software_version=data.metadata.software_version,
                    ),
                ),
                data.metadata.custom_info,
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> LiquidHandlerDocumentItem:
        return LiquidHandlerDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=add_custom_information_document(
                MeasurementAggregateDocument(
                    analytical_method_identifier=measurement_group.analytical_method_identifier,
                    experimental_data_identifier=measurement_group.experimental_data_identifier,
                    measurement_document=[
                        self._get_measurement_document_item(measurement, metadata)
                        for measurement in measurement_group.measurements
                    ],
                ),
                measurement_group.custom_info,
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocumentItem:
        doc = MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.measurement_time),
            sample_document=self._get_sample_document(measurement),
            aspiration_volume=quantity_or_none(
                TQuantityValueMicroliter, measurement.aspiration_volume
            ),
            transfer_volume=quantity_or_none(
                TQuantityValueMicroliter, measurement.transfer_volume
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        DeviceControlDocumentItem(
                            device_type=metadata.device_type,
                            injection_volume_setting=quantity_or_none(
                                TQuantityValueMicroliter,
                                measurement.injection_volume_setting,
                            ),
                        ),
                        measurement.device_control_custom_info,
                    )
                ]
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
        )
        return add_custom_information_document(doc, measurement.custom_info)

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            source_well_location_identifier=measurement.source_well,
            source_well_plate_identifier=measurement.source_plate,
            source_location_identifier=measurement.source_location,
            destination_well_location_identifier=measurement.destination_well,
            destination_well_plate_identifier=measurement.destination_plate,
            destination_location_identifier=measurement.destination_location,
        )

    def _get_error_aggregate_document(
        self, errors: list[Error] | None
    ) -> ErrorAggregateDocument | None:
        if not errors:
            return None

        return ErrorAggregateDocument(
            error_document=[
                ErrorDocumentItem(error=error.error, error_feature=error.feature)
                for error in errors
            ]
        )
