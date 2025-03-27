from dataclasses import dataclass
from enum import Enum

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.binding_affinity_analyzer.wd._2024._12.binding_affinity_analyzer import (
    BindingAffinityAnalyzerAggregateDocument,
    BindingAffinityAnalyzerDocumentItem,
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
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
    ReportPointAggregateDocument,
    ReportPointDocumentItem,
    SampleDocument,
    SensorChipDocument,
    TQuantityValueModel,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMicroliterPerMinute,
    TQuantityValueNanomolar,
    TQuantityValuePercent,
    TQuantityValueResonanceUnits,
    TQuantityValueSecondTime,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDatacube
from allotropy.allotrope.schema_mappers.data_cube import DataCube, get_data_cube
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none
from allotropy.types import DictType


class MeasurementType(Enum):
    SURFACE_PLASMON_RESONANCE = "SURFACE_PLASMON_RESONANCE"


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
    lot_number: str | None = None
    sensor_chip_custom_info: DictType | None = None


@dataclass(frozen=True)
class ReportPoint:
    identifier: str
    identifier_role: str
    absolute_resonance: float
    time_setting: float
    relative_resonance: float | None = None
    custom_info: DictType | None = None


@dataclass(frozen=True)
class Measurement:
    identifier: str
    sample_identifier: str
    device_type: str
    type_: MeasurementType
    location_identifier: str | None = None
    batch_identifier: str | None = None
    well_plate_identifier: str | None = None
    sample_role_type: str | None = None
    concentration: float | None = None
    method_name: str | None = None
    ligand_identifier: str | None = None
    flow_cell_identifier: str | None = None
    flow_path: str | None = None
    flow_rate: float | None = None
    contact_time: float | None = None
    dilution: float | None = None
    device_control_custom_info: DictType | None = None
    sample_custom_info: DictType | None = None

    # Sensorgram
    sensorgram_data_cube: DataCube | None = None

    # Report point
    report_point_data: list[ReportPoint] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurement_time: str
    measurements: list[Measurement]
    experiment_type: str | None = None
    analytical_method_identifier: str | None = None
    analyst: str | None = None
    measurement_aggregate_custom_info: DictType | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDocument] | None = None


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
                        if data.metadata.device_document
                        else None
                    ),
                ),
                binding_affinity_analyzer_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data.calculated_data
                ),
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
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocument:
        if measurement.type_ == MeasurementType.SURFACE_PLASMON_RESONANCE:
            return self._get_surface_plasmon_resonance_measurement_document(
                measurement, metadata
            )
        else:
            msg = f"Invalid measurement type: {measurement.type_}"
            raise AllotropyParserError(msg)

    def _get_surface_plasmon_resonance_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocument:
        return MeasurementDocument(
            measurement_identifier=measurement.identifier,
            sample_document=add_custom_information_document(
                SampleDocument(
                    sample_identifier=measurement.sample_identifier,
                    sample_role_type=measurement.sample_role_type,
                    location_identifier=measurement.location_identifier,
                    concentration=quantity_or_none(
                        TQuantityValueNanomolar, measurement.concentration
                    ),
                ),
                custom_info_doc=measurement.sample_custom_info,
            ),
            detection_type=metadata.detection_type,
            method_name=measurement.method_name,
            ligand_identifier=measurement.ligand_identifier,
            sensorgram_data_cube=get_data_cube(
                measurement.sensorgram_data_cube, TDatacube
            ),
            sensor_chip_document=add_custom_information_document(
                SensorChipDocument(
                    sensor_chip_identifier=metadata.sensor_chip_identifier,
                    sensor_chip_type=metadata.sensor_chip_type,
                    lot_number=metadata.lot_number,
                    product_manufacturer=metadata.product_manufacturer,
                ),
                custom_info_doc=metadata.sensor_chip_custom_info,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        DeviceControlDocumentItem(
                            flow_cell_identifier=measurement.flow_cell_identifier,
                            flow_path=measurement.flow_path,
                            flow_rate=quantity_or_none(
                                TQuantityValueMicroliterPerMinute,
                                measurement.flow_rate,
                            ),
                            contact_time=quantity_or_none(
                                TQuantityValueSecondTime, measurement.contact_time
                            ),
                            dilution_factor=quantity_or_none(
                                TQuantityValuePercent, measurement.dilution
                            ),
                            device_type=measurement.device_type,
                        ),
                        custom_info_doc=measurement.device_control_custom_info,
                    )
                ]
            ),
            processed_data_aggregate_document=(
                ProcessedDataAggregateDocument(
                    processed_data_document=[
                        ProcessedDataDocumentItem(
                            report_point_aggregate_document=ReportPointAggregateDocument(
                                report_point_document=[
                                    add_custom_information_document(
                                        ReportPointDocumentItem(
                                            report_point_identifier=report_point.identifier,
                                            identifier_role=report_point.identifier_role,
                                            absolute_resonance=TQuantityValueResonanceUnits(
                                                value=report_point.absolute_resonance
                                            ),
                                            relative_resonance=quantity_or_none(
                                                TQuantityValueResonanceUnits,
                                                report_point.relative_resonance,
                                            ),
                                            time_setting=TQuantityValueSecondTime(
                                                value=report_point.time_setting
                                            ),
                                        ),
                                        # TODO: probably this should be at the processed document level.
                                        custom_info_doc=report_point.custom_info,
                                    )
                                    for report_point in measurement.report_point_data
                                ]
                            )
                        ),
                    ]
                )
                if measurement.report_point_data
                else None
            ),
        )

    def _get_calculated_data_aggregate_document(
        self, calculated_data_items: list[CalculatedDocument] | None
    ) -> CalculatedDataAggregateDocument | None:
        if not calculated_data_items:
            return None

        return CalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calculated_data_item.uuid,
                    calculated_data_name=calculated_data_item.name,
                    calculation_description=calculated_data_item.description,
                    calculated_result=TQuantityValueModel(
                        value=calculated_data_item.value,
                        unit=assert_not_none(calculated_data_item.unit),
                    ),
                    data_source_aggregate_document=DataSourceAggregateDocument(
                        data_source_document=[
                            DataSourceDocumentItem(
                                data_source_identifier=item.reference.uuid,
                                data_source_feature=item.feature,
                            )
                            for item in calculated_data_item.data_sources
                        ]
                    ),
                )
                for calculated_data_item in calculated_data_items
            ]
        )
