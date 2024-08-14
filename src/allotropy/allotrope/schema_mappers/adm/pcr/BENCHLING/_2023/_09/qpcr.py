from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

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
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    InvalidJsonFloat,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
    TDateTimeValue,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none


@dataclass
class DataCubeComponent:
    type_: FieldComponentDatatype
    concept: str
    unit: str


@dataclass
class DataCube:
    label: str
    structure_dimensions: list[DataCubeComponent]
    structure_measures: list[DataCubeComponent]
    dimensions: list[list[float]]
    measures: list[list[float | None]]


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
    cycle_threshold_value_setting: float
    automatic_cycle_threshold_enabled_setting: bool | None = None
    automatic_baseline_determination_enabled_setting: bool | None = None
    genotyping_determination_method_setting: float | None = None
    genotyping_determination_result: str | None = None
    cycle_threshold_result: float | None = None
    normalized_reporter_result: float | None = None
    baseline_corrected_reporter_result: float | None = None
    data_cubes: list[DataCube] | None = None


@dataclass
class Measurement:
    # Measurement metadata
    identifier: str
    timestamp: str
    target_identifier: str
    sample_identifier: str

    # Settings
    pcr_detection_chemistry: str

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
    data_cubes: list[DataCube] | None = None


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
    software_name: str
    software_version: str
    data_system_instance_identifier: str
    file_name: str
    unc_path: str
    experiment_type: ExperimentType
    container_type: ContainerType
    measurement_method_identifier: str


@dataclass
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: CalculatedData


CubeClass = TypeVar("CubeClass")


class Mapper:
    MANIFEST = "http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest"

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

    def map_model(self, data: Data) -> Model:
        return Model(
            qPCR_aggregate_document=QPCRAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    device_serial_number=data.metadata.device_serial_number,
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
        return MeasurementDocumentItem(
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
            reporter_dye_data_cube=self._get_data_cube(
                ReporterDyeDataCube, "reporter dye", measurement.data_cubes
            ),
            passive_reference_dye_data_cube=self._get_data_cube(
                PassiveReferenceDyeDataCube,
                "passive reference dye",
                measurement.data_cubes,
            ),
            melting_curve_data_cube=self._get_data_cube(
                MeltingCurveDataCube, "melting curve", measurement.data_cubes
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            sample_role_type=measurement.sample_role_type,
            well_location_identifier=measurement.well_location_identifier,
            well_plate_identifier=measurement.well_plate_identifier,
        )

    def _get_processed_data_aggregate_document(
        self, data: ProcessedData | None
    ) -> ProcessedDataAggregateDocument | None:
        if not data:
            return None
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    data_processing_document=DataProcessingDocument(
                        automatic_cycle_threshold_enabled_setting=data.automatic_baseline_determination_enabled_setting,
                        cycle_threshold_value_setting=TQuantityValueUnitless(
                            value=data.cycle_threshold_value_setting,
                        ),
                        automatic_baseline_determination_enabled_setting=data.automatic_baseline_determination_enabled_setting,
                        genotyping_determination_method_setting=quantity_or_none(
                            TQuantityValueUnitless,
                            data.genotyping_determination_method_setting,
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
                    normalized_reporter_data_cube=self._get_data_cube(
                        NormalizedReporterDataCube,
                        "normalized reporter",
                        data.data_cubes,
                    ),
                    baseline_corrected_reporter_data_cube=self._get_data_cube(
                        BaselineCorrectedReporterDataCube,
                        "baseline corrected reporter",
                        data.data_cubes,
                    ),
                )
            ]
        )

    def _get_calculated_data_aggregate_document(
        self, data: Data
    ) -> TCalculatedDataAggregateDocument | None:
        if not data.calculated_data:
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

    def _get_data_cube(
        self,
        cube_class: Callable[..., CubeClass],
        label: str,
        data_cubes: list[DataCube] | None,
    ) -> CubeClass | None:
        if not (
            data_cube := get_first_not_none(
                lambda cube: cube if cube.label == label else None,
                data_cubes or [],
            )
        ):
            return None

        return cube_class(
            label=data_cube.label,
            cube_structure=TDatacubeStructure(
                dimensions=[
                    TDatacubeComponent(
                        field_componentDatatype=component.type_,
                        concept=component.concept,
                        unit=component.unit,
                    )
                    for component in data_cube.structure_dimensions
                ],
                measures=[
                    TDatacubeComponent(
                        field_componentDatatype=component.type_,
                        concept=component.concept,
                        unit=component.unit,
                    )
                    for component in data_cube.structure_measures
                ],
            ),
            data=TDatacubeData(
                dimensions=data_cube.dimensions, measures=data_cube.measures  # type: ignore[arg-type]
            ),
        )
