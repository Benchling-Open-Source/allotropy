from dataclasses import dataclass
from enum import Enum
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.binding_affinity_analyzer.wd._2024._12.binding_affinity_analyzer import (
    BindingAffinityAnalyzerAggregateDocument,
    BindingAffinityAnalyzerDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SensorChipDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    # TQuantityValueMicroliterPerMinute,
    TQuantityValueMolar,
    TQuantityValuePercent,
    # TQuantityValueNanomolar,
    TQuantityValuePerSecond,
    TQuantityValueSecondTime,
    TQuantityValueTODO,
)
from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none


class MeasurementType(Enum):
    SURFACE_PLASMON_RESONANCE = "SURFACE_PLASMON_RESONANCE"


@dataclass(frozen=True)
class DataSource:
    identifier: str
    feature: str


@dataclass(frozen=True)
class CalculatedDataItem:
    identifier: str
    name: str
    value: float
    unit: str
    data_sources: list[DataSource]
    description: str | None = None


@dataclass(frozen=True)
class DeviceDocument:
    device_type: str
    device_identifier: str


@dataclass(frozen=True)
class Metadata:
    device_identifier: str
    asm_file_identifier: str
    data_system_instance_identifier: str
    model_number: str
    sensor_chip_identifier: str
    brand_name: str | None = None
    product_manufacturer: str | None = None
    software_name: str | None = None
    software_version: str | None = None
    file_name: str | None = None
    unc_path: str | None = None
    device_document: list[DeviceDocument] | None = None
    detection_type: str | None = None
    equipment_serial_number: str | None = None
    compartment_temperature: float | None = None
    sensor_chip_type: str | None = None
    sensor_chip_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Measurements:
    identifier: str
    sample_identifier: str
    device_type: str
    type_: MeasurementType
    sensorgram_posix_path: str
    location_identifier: str | None = None
    batch_identifier: str | None = None
    well_plate_identifier: str | None = None
    sample_role_type: str | None = None
    concentration: JsonFloat | None = None
    method_name: str | None = None
    ligand_identifier: str | None = None
    flow_cell_identifier: str | None = None
    flow_path: str | None = None
    flow_rate: float | None = None
    contact_time: float | None = None
    dilution: float | None = None
    device_control_custom_info: dict[str, Any] | None = None
    binding_on_rate_measurement: JsonFloat | None = None
    binding_off_rate_measurement: JsonFloat | None = None
    equilibrium_dissociation_constant: JsonFloat | None = None
    Rmax: JsonFloat | None = None
    sensorgram_posix_path_identifier: str | None = None
    rpoint_posix_path: str | None = None
    rpoint_posix_path_identifier: str | None = None
    sample_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurement_time: str
    measurements: list[Measurements]
    experiment_type: str | None = None
    analytical_method_identifier: str | None = None
    analyst: str | None = None
    measurement_aggregate_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDataItem] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST: str = "http://purl.allotrope.org/manifests/binding-affinity-analyzer/WD/2024/12/binding-affinity-analyzer.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            binding_affinity_analyzer_aggregate_document=BindingAffinityAnalyzerAggregateDocument(
                data_system_document=DataSystemDocument(
                    ASM_file_identifier=data.metadata.asm_file_identifier,
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_version=data.metadata.software_version,
                    software_name=data.metadata.software_name,
                ),
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    brand_name=data.metadata.brand_name,
                    product_manufacturer=data.metadata.product_manufacturer,
                    device_document=(
                        [
                            DeviceDocumentItem(
                                device_type=device_document_item.device_type,
                                device_identifier=device_document_item.device_identifier,
                            )
                            for device_document_item in data.metadata.device_document
                        ]
                        if data.metadata.device_document is not None
                        else None
                    ),
                ),
                binding_affinity_analyzer_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
            )
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> BindingAffinityAnalyzerDocumentItem:
        return BindingAffinityAnalyzerDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=add_custom_information_document(
                MeasurementAggregateDocument(
                    measurement_time=self.get_date_time(
                        assert_not_none(measurement_group.measurement_time)
                    ),
                    experiment_type=measurement_group.experiment_type,
                    analytical_method_identifier=measurement_group.analytical_method_identifier,
                    compartment_temperature=quantity_or_none(
                        TQuantityValueDegreeCelsius, metadata.compartment_temperature
                    ),
                    measurement_document=[
                        self._get_measurement_document_item(measurements, metadata)
                        for measurements in measurement_group.measurements
                    ],
                ),
                custom_info_doc=measurement_group.measurement_aggregate_custom_info,
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurements, metadata: Metadata
    ) -> MeasurementDocument:
        if measurement.type_ == MeasurementType.SURFACE_PLASMON_RESONANCE:
            return self._get_surface_plasmon_resonance_measurement_document(
                measurement, metadata
            )
        else:
            msg = f"Invalid measurement type: {measurement.type_}"
            raise AllotropyParserError(msg)

    def _get_surface_plasmon_resonance_measurement_document(
        self, measurements: Measurements, metadata: Metadata
    ) -> MeasurementDocument:
        return MeasurementDocument(
            measurement_identifier=measurements.identifier,
            POSIX_path=measurements.sensorgram_posix_path,
            identifier=measurements.sensorgram_posix_path_identifier,
            sample_document=add_custom_information_document(
                SampleDocument(
                    sample_identifier=measurements.sample_identifier,
                    sample_role_type=measurements.sample_role_type,
                    location_identifier=measurements.location_identifier,
                    # concentration=quantity_or_none(
                    #     TQuantityValueNanomolar, measurements.concentration
                    # ),
                ),
                custom_info_doc=measurements.sample_custom_info,
            ),
            detection_type=metadata.detection_type,
            method_name=measurements.method_name,
            ligand_identifier=measurements.ligand_identifier,
            sensor_chip_document=add_custom_information_document(
                SensorChipDocument(
                    sensor_chip_identifier=metadata.sensor_chip_identifier,
                    sensor_chip_type=metadata.sensor_chip_type,
                    product_manufacturer=metadata.product_manufacturer,
                ),
                custom_info_doc=metadata.sensor_chip_custom_info,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        DeviceControlDocumentItem(
                            flow_cell_identifier=measurements.flow_cell_identifier,
                            flow_path=measurements.flow_path,
                            # flow_rate=quantity_or_none(
                            #     TQuantityValueMicroliterPerMinute,
                            #     measurements.flow_rate,
                            # ),
                            contact_time=quantity_or_none(
                                TQuantityValueSecondTime, measurements.contact_time
                            ),
                            dilution_factor=quantity_or_none(
                                TQuantityValuePercent, measurements.dilution
                            ),
                            device_type=measurements.device_type,
                        ),
                        custom_info_doc=measurements.device_control_custom_info,
                    )
                ]
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(
                        POSIX_path=measurements.rpoint_posix_path,
                        identifier=measurements.rpoint_posix_path_identifier,
                        binding_on_rate_measurement_datum__kon_=quantity_or_none(
                            TQuantityValueTODO, measurements.binding_on_rate_measurement
                        ),
                        binding_off_rate_measurement_datum__koff_=quantity_or_none(
                            TQuantityValuePerSecond,
                            measurements.binding_off_rate_measurement,
                        ),
                        equilibrium_dissociation_constant__KD_=quantity_or_none(
                            TQuantityValueMolar,
                            measurements.equilibrium_dissociation_constant,
                        ),
                        maximum_binding_capacity__Rmax_=quantity_or_none(
                            TQuantityValueTODO,
                            measurements.Rmax,
                        ),
                    )
                ]
            ),
        )
