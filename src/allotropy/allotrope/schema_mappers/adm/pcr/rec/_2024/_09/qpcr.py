from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.pcr.rec._2024._09.qpcr import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataProcessingDocument,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    QpcrAggregateDocument,
    QpcrDocumentItem,
    SampleDocument,
    TQuantityValueModel,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
    TQuantityValueNumber,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TDatacube,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, get_data_cube
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none


# TODO: These Enumn should be autogenerated from the schema
class ContainerType(Enum):
    reactor = "reactor"
    controlled_lab_reactor = "controlled lab reactor"
    tube = "tube"
    well_plate = "well plate"
    differential_scanning_calorimetry_pan = "differential scanning calorimetry pan"
    PCR_reaction_block = "PCR reaction block"
    vial_rack = "vial rack"
    pan = "pan"
    reservoir = "reservoir"
    array_card_block = "array card block"
    capillary = "capillary"
    disintegration_apparatus_basket = "disintegration apparatus basket"
    jar = "jar"
    container = "container"
    tray = "tray"
    basket = "basket"
    cell_holder = "cell holder"


class SampleRoleType(str, Enum):
    control_sample_role = "control sample role"
    standard_sample_role = "standard sample role"
    validation_sample_role = "validation sample role"
    experiment_sample_role = "experiment sample role"
    sample_role = "sample role"
    spiked_sample_role = "spiked sample role"
    blank_role = "blank role"
    unknown_sample_role = "unknown sample role"
    calibration_sample_role = "calibration sample role"
    unspiked_sample_role = "unspiked sample role"
    specimen_role = "specimen role"
    quality_control_sample_role = "quality control sample role"
    reference_sample_role = "reference sample role"


@dataclass
class DataSource:
    identifier: str
    feature: str


@dataclass
class Error:
    error: str
    feature: str


@dataclass
class CalculatedDataItem:
    identifier: str
    name: str
    value: float
    unit: str
    data_sources: list[DataSource]


@dataclass
class CalculatedData:
    items: list[CalculatedDataItem]


@dataclass
class ProcessedData:
    # Settings
    cycle_threshold_value_setting: float | None = None
    cycle_threshold_result: float | None = None
    automatic_cycle_threshold_enabled_setting: bool | None = None
    automatic_baseline_determination_enabled_setting: bool | None = None
    baseline_determination_start_cycle_setting: int | None = None
    baseline_determination_end_cycle_setting: int | None = None
    genotyping_determination_method_setting: float | None = None

    # Results
    genotyping_determination_result: str | None = None
    normalized_reporter_result: float | None = None
    baseline_corrected_reporter_result: float | None = None
    normalized_reporter_data_cube: DataCube | None = None
    baseline_corrected_reporter_data_cube: DataCube | None = None

    # Metadata
    comments: str | None = None

    custom_info: dict[str, Any] | None = None


@dataclass
class Measurement:
    # Measurement metadata
    identifier: str
    timestamp: str
    sample_identifier: str
    target_identifier: str
    location_identifier: str
    group_identifier: str | None = None

    # Settings
    pcr_detection_chemistry: str | None = None

    # Optional measurement metadata
    sample_role_type: SampleRoleType | None = None
    well_location_identifier: str | None = None
    well_plate_identifier: str | None = None

    # Optional settings
    total_cycle_number_setting: float | None = None
    reporter_dye_setting: str | None = None
    quencher_dye_setting: str | None = None
    passive_reference_dye_setting: str | None = None

    # Processed data
    processed_data: ProcessedData | None = None
    reporter_dye_data_cube: DataCube | None = None
    passive_reference_dye_data_cube: DataCube | None = None
    melting_curve_data_cube: DataCube | None = None

    # Custom metadata
    custom_info: dict[str, Any] | None = None
    sample_custom_info: dict[str, Any] | None = None
    device_control_custom_info: dict[str, Any] | None = None

    # Error document
    error_document: list[Error] | None = None


@dataclass
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: int | None
    experimental_data_identifier: str
    well_volume: float
    analyst: str | None = None

    # Error document
    error_document: list[Error] | None = None


@dataclass
class Metadata:
    device_identifier: str
    asm_file_identifier: str
    data_system_instance_identifier: str
    device_type: str
    device_serial_number: str
    model_number: str
    file_name: str
    measurement_method_identifier: str
    experiment_type: str
    container_type: ContainerType
    unc_path: str | None = None
    software_name: str | None = None
    software_version: str | None = None
    product_manufacturer: str | None = None


@dataclass
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: CalculatedData | None = None


CubeClass = TypeVar("CubeClass")


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/pcr/REC/2024/09/qpcr.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest=self.MANIFEST,
            qpcr_aggregate_document=QpcrAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.device_serial_number,
                    product_manufacturer=data.metadata.product_manufacturer,
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    ASM_file_identifier=data.metadata.asm_file_identifier,
                ),
                qpcr_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data
                ),
            ),
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> QpcrDocumentItem:
        return QpcrDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                experimental_data_identifier=measurement_group.experimental_data_identifier,
                experiment_type=metadata.experiment_type,
                container_type=metadata.container_type.value,
                well_volume=TQuantityValueMicroliter(
                    value=measurement_group.well_volume
                ),
                plate_well_count=quantity_or_none(
                    TQuantityValueNumber, measurement_group.plate_well_count
                ),
                measurement_document=[
                    self._get_measurement_document_item(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
                error_aggregate_document=self._get_error_aggregate_document(
                    measurement_group.error_document
                ),
            ),
        )

    def _get_measurement_document_item(
        self,
        measurement: Measurement,
        metadata: Metadata,
    ) -> MeasurementDocumentItem:
        measurement_doc = MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.timestamp),
            target_DNA_description=measurement.target_identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        measurement_method_identifier=metadata.measurement_method_identifier,
                        total_cycle_number_setting=quantity_or_none(
                            TQuantityValueUnitless,
                            measurement.total_cycle_number_setting,
                        ),
                        qPCR_detection_chemistry=measurement.pcr_detection_chemistry,
                        reporter_dye_setting=measurement.reporter_dye_setting,
                        quencher_dye_setting=measurement.quencher_dye_setting,
                        passive_reference_dye_setting=measurement.passive_reference_dye_setting,
                    )
                ],
            ),
            processed_data_aggregate_document=assert_not_none(
                self._get_processed_data_aggregate_document(measurement.processed_data)
            ),
            reporter_data_cube=get_data_cube(
                measurement.reporter_dye_data_cube, TDatacube
            ),
            passive_reference_data_cube=get_data_cube(
                measurement.passive_reference_dye_data_cube, TDatacube
            ),
            melting_curve_data_cube=get_data_cube(
                measurement.melting_curve_data_cube, TDatacube
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.error_document
            ),
        )
        return add_custom_information_document(measurement_doc, measurement.custom_info)

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        # TODO(ASM gaps): we believe these values should be added to ASM.
        custom_info_doc = {"group identifier": measurement.group_identifier}
        sample_doc = SampleDocument(
            sample_identifier=measurement.sample_identifier,
            sample_role_type=(
                None
                if measurement.sample_role_type is None
                else measurement.sample_role_type.value
            ),
            well_location_identifier=measurement.well_location_identifier,
            well_plate_identifier=measurement.well_plate_identifier,
            location_identifier=measurement.location_identifier,
        )
        return add_custom_information_document(
            sample_doc, (measurement.sample_custom_info or {}) | custom_info_doc
        )

    def _get_processed_data_aggregate_document(
        self, data: ProcessedData | None
    ) -> ProcessedDataAggregateDocument | None:
        if not data:
            return None
        doc = ProcessedDataDocumentItem(
            data_processing_document=DataProcessingDocument(
                automatic_cycle_threshold_enabled_setting=data.automatic_cycle_threshold_enabled_setting,
                cycle_threshold_value_setting__qPCR_=quantity_or_none(
                    TQuantityValueUnitless, data.cycle_threshold_value_setting
                ),
                automatic_baseline_determination_enabled_setting=data.automatic_baseline_determination_enabled_setting,
                genotyping_qPCR_method_setting__qPCR_=quantity_or_none(
                    TQuantityValueUnitless,
                    data.genotyping_determination_method_setting,
                ),
                baseline_determination_start_cycle_setting=quantity_or_none(
                    TQuantityValueNumber,
                    data.baseline_determination_start_cycle_setting,
                ),
                baseline_determination_end_cycle_setting=quantity_or_none(
                    TQuantityValueNumber,
                    data.baseline_determination_end_cycle_setting,
                ),
            ),
            cycle_threshold_result__qPCR_=quantity_or_none(
                TQuantityValueUnitless, data.cycle_threshold_result
            ),
            normalized_reporter_result=quantity_or_none(
                TQuantityValueUnitless, data.normalized_reporter_result
            ),
            baseline_corrected_reporter_result=quantity_or_none(
                TQuantityValueUnitless,
                data.baseline_corrected_reporter_result,
            ),
            genotyping_qPCR_result=data.genotyping_determination_result,
            normalized_reporter_data_cube=get_data_cube(
                data.normalized_reporter_data_cube, TDatacube
            ),
            baseline_corrected_reporter_data_cube=get_data_cube(
                data.baseline_corrected_reporter_data_cube,
                TDatacube,
            ),
        )
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                add_custom_information_document(doc, data.custom_info)
            ]
        )

    def _get_calculated_data_aggregate_document(
        self, data: Data
    ) -> CalculatedDataAggregateDocument | None:
        if not data.calculated_data or not data.calculated_data.items:
            return None

        return CalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calc_doc.identifier,
                    data_source_aggregate_document=DataSourceAggregateDocument(
                        data_source_document=[
                            DataSourceDocumentItem(
                                data_source_identifier=data_source.identifier,
                                data_source_feature=data_source.feature,
                            )
                            for data_source in calc_doc.data_sources
                        ],
                    ),
                    calculated_data_name=calc_doc.name,
                    calculation_description=None,
                    calculated_result=TQuantityValueModel(
                        value=calc_doc.value, unit=calc_doc.unit
                    ),
                )
                for calc_doc in data.calculated_data.items
            ],
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