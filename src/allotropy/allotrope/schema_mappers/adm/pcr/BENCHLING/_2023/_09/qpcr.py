from dataclasses import dataclass
from typing import Any, TypeVar

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import (
    BaselineCorrectedReporterDataCube,
    CalculatedDataDocumentItem,
    ContainerType,
    DataProcessingDocument,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ExperimentType,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    MeltingCurveDataCube,
    Model,
    NormalizedReporterDataCube,
    PassiveReferenceDyeDataCube,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    QPCRAggregateDocument,
    QPCRDocumentItem,
    ReporterDyeDataCube,
    SampleDocument,
    TCalculatedDataAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueUnitless,
    TQuantityValueNumber,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import InvalidJsonFloat
from allotropy.allotrope.schema_mappers.data_cube import DataCube, get_data_cube
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none


@dataclass
class DataSource:
    identifier: str
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
    reference_dna_description: str | None = None
    reference_sample_description: str | None = None


@dataclass
class ProcessedData:
    # Settings
    cycle_threshold_value_setting: float
    automatic_cycle_threshold_enabled_setting: bool | None = None
    automatic_baseline_determination_enabled_setting: bool | None = None
    baseline_determination_start_cycle_setting: int | None = None
    baseline_determination_end_cycle_setting: int | None = None
    genotyping_determination_method_setting: float | None = None

    # Results
    genotyping_determination_result: str | None = None
    cycle_threshold_result: float | None = None
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
    group_identifier: str | None = None

    # Settings
    pcr_detection_chemistry: str | None = None

    # Optional measurement metadata
    sample_role_type: str | None = None
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


@dataclass
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: int | InvalidJsonFloat
    analyst: str | None = None
    experimental_data_identifier: str | None = None


@dataclass
class Metadata:
    device_identifier: str
    device_type: str
    device_serial_number: str
    model_number: str
    file_name: str
    measurement_method_identifier: str
    unc_path: str | None = None
    experiment_type: ExperimentType | None = None
    container_type: ContainerType | None = None
    data_system_instance_identifier: str | None = None
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
    MANIFEST = "http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            qPCR_aggregate_document=QPCRAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    device_serial_number=data.metadata.device_serial_number,
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
                ),
                qPCR_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data
                ),
            )
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> QPCRDocumentItem:
        return QPCRDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                experimental_data_identifier=measurement_group.experimental_data_identifier,
                experiment_type=metadata.experiment_type,
                container_type=metadata.container_type,
                plate_well_count=TQuantityValueNumber(
                    value=measurement_group.plate_well_count
                ),
                measurement_document=[
                    self._get_measurement_document_item(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
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
                            TQuantityValueNumber, measurement.total_cycle_number_setting
                        ),
                        PCR_detection_chemistry=measurement.pcr_detection_chemistry,
                        reporter_dye_setting=measurement.reporter_dye_setting,
                        quencher_dye_setting=measurement.quencher_dye_setting,
                        passive_reference_dye_setting=measurement.passive_reference_dye_setting,
                    )
                ],
            ),
            processed_data_aggregate_document=assert_not_none(
                self._get_processed_data_aggregate_document(measurement.processed_data)
            ),
            reporter_dye_data_cube=get_data_cube(
                measurement.reporter_dye_data_cube, ReporterDyeDataCube
            ),
            passive_reference_dye_data_cube=get_data_cube(
                measurement.passive_reference_dye_data_cube, PassiveReferenceDyeDataCube
            ),
            melting_curve_data_cube=get_data_cube(
                measurement.melting_curve_data_cube, MeltingCurveDataCube
            ),
        )
        return add_custom_information_document(measurement_doc, measurement.custom_info)

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        # TODO(ASM gaps): we believe these values should be added to ASM.
        custom_info_doc = {"group identifier": measurement.group_identifier}
        sample_doc = SampleDocument(
            sample_identifier=measurement.sample_identifier,
            sample_role_type=measurement.sample_role_type,
            well_location_identifier=measurement.well_location_identifier,
            well_plate_identifier=measurement.well_plate_identifier,
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
                cycle_threshold_value_setting=TQuantityValueUnitless(
                    value=data.cycle_threshold_value_setting,
                ),
                automatic_baseline_determination_enabled_setting=data.automatic_baseline_determination_enabled_setting,
                genotyping_determination_method_setting=quantity_or_none(
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
            cycle_threshold_result=TNullableQuantityValueUnitless(
                value=data.cycle_threshold_result,
            ),
            normalized_reporter_result=quantity_or_none(
                TQuantityValueUnitless, data.normalized_reporter_result
            ),
            baseline_corrected_reporter_result=quantity_or_none(
                TQuantityValueUnitless,
                data.baseline_corrected_reporter_result,
            ),
            genotyping_determination_result=data.genotyping_determination_result,
            normalized_reporter_data_cube=get_data_cube(
                data.normalized_reporter_data_cube, NormalizedReporterDataCube
            ),
            baseline_corrected_reporter_data_cube=get_data_cube(
                data.baseline_corrected_reporter_data_cube,
                BaselineCorrectedReporterDataCube,
            ),
        )
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                add_custom_information_document(doc, data.custom_info)
            ]
        )

    def _get_calculated_data_aggregate_document(
        self, data: Data
    ) -> TCalculatedDataAggregateDocument | None:
        if not data.calculated_data or not data.calculated_data.items:
            return None

        if data.calculated_data.reference_sample_description:
            data_processing_document = DataProcessingDocument(
                reference_DNA_description=data.calculated_data.reference_dna_description,
                reference_sample_description=data.calculated_data.reference_sample_description,
            )
        else:
            data_processing_document = None

        return TCalculatedDataAggregateDocument(
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
                    data_processing_document=data_processing_document,
                    calculated_data_name=calc_doc.name,
                    calculated_data_description=None,
                    calculated_datum=TQuantityValueUnitless(
                        value=calc_doc.value, unit=calc_doc.unit
                    ),
                )
                for calc_doc in data.calculated_data.items
            ],
        )
