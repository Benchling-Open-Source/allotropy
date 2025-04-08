from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.flow_cytometry.benchling._2025._03.flow_cytometry import (
    CompensationMatrixAggregateDocument,
    CompensationMatrixDocumentItem,
    DataProcessingDocument,
    DataRegionAggregateDocument,
    DataRegionDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    FlowCytometryAggregateDocument,
    FlowCytometryDocumentItem,
    MatrixAggregateDocument,
    MatrixDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    PopulationAggregateDocumentItem,
    PopulationDocumentItem,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    StatisticDimensionAggregateDocument,
    StatisticDimensionDocumentItem,
    StatisticsAggregateDocument,
    StatisticsDocumentItem,
    VertexAggregateDocument,
    VertexDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCounts,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TQuantityValue,
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import quantity_or_none, quantity_or_none_from_unit


@dataclass(frozen=True)
class Vertex:
    x_coordinate: float
    y_coordinate: float
    x_unit: str
    y_unit: str
    vertex_role: str | None = None


@dataclass(frozen=True)
class DataRegion:
    region_data_identifier: str | None
    region_data_type: str | None
    parent_data_region_identifier: str | None = None
    x_coordinate_dimension_identifier: str | None = None
    y_coordinate_dimension_identifier: str | None = None
    vertices: list[Vertex] | None = None


@dataclass(frozen=True)
class CompensationMatrix:
    dimension_identifier: str | None
    compensation_value: float | None


@dataclass(frozen=True)
class CompensationMatrixGroup:
    dimension_identifier: str | None
    compensation_matrices: list[CompensationMatrix] | None = None


@dataclass(frozen=True)
class StatisticDimension:
    value: float
    unit: str
    has_statistic_datum_role: str | None = None
    dimension_identifier: str | None = None


@dataclass(frozen=True)
class Statistic:
    statistic_dimension: list[StatisticDimension]
    statistical_feature: str


@dataclass(frozen=True)
class Population:
    population_identifier: str
    written_name: str | None = None
    data_region_identifier: str | None = None
    count: int | None = None
    parent_population_identifier: str | None = None
    sub_populations: list[Population] | None = None
    statistics: list[Statistic] | None = None
    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Measurement:
    measurement_identifier: str
    sample_identifier: str
    device_type: str

    location_identifier: str | None = None
    well_plate_identifier: str | None = None
    batch_identifier: str | None = None
    written_name: str | None = None
    method_version: str | None = None
    data_processing_time: str | None = None
    processed_data_identifier: str | None = None
    populations: list[Population] | None = None
    data_regions: list[DataRegion] | None = None

    sample_custom_info: dict[str, Any] | None = None
    processed_data_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    compensation_matrix_groups: list[CompensationMatrixGroup] | None = None
    analyst: str | None = None
    measurement_time: str | None = None
    experimental_data_identifier: str | None = None
    experiment_identifier: str | None = None


@dataclass
class Metadata:
    asm_file_identifier: str
    data_system_instance_identifier: str
    model_number: str | None = None
    software_name: str | None = None
    file_name: str | None = None
    unc_path: str | None = None
    equipment_serial_number: str | None = None
    software_version: str | None = None
    device_identifier: str | None = None

    custom_info: dict[str, Any] | None = None


@dataclass
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/flow-cytometry/BENCHLING/2025/03/flow-cytometry.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            manifest=self.MANIFEST,
            flow_cytometry_aggregate_document=add_custom_information_document(
                FlowCytometryAggregateDocument(
                    device_system_document=DeviceSystemDocument(
                        device_identifier=data.metadata.device_identifier,
                        model_number=data.metadata.model_number,
                        equipment_serial_number=data.metadata.equipment_serial_number,
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
                    flow_cytometry_document=[
                        self._get_technique_document(measurement_group)
                        for measurement_group in data.measurement_groups
                    ],
                ),
                data.metadata.custom_info,
            ),
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup
    ) -> FlowCytometryDocumentItem:
        return FlowCytometryDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    self._get_measurement_document(measurement)
                    for measurement in measurement_group.measurements
                ],
                analyst=measurement_group.analyst,
                measurement_time=self.get_date_time(measurement_group.measurement_time)
                if measurement_group.measurement_time
                else None,
                experimental_data_identifier=measurement_group.experimental_data_identifier,
                experiment_identifier=measurement_group.experiment_identifier,
            ),
            compensation_matrix_aggregate_document=CompensationMatrixAggregateDocument(
                compensation_matrix_document=[
                    self._get_compensation_matrix_document(compensation_matrix)
                    for compensation_matrix in measurement_group.compensation_matrix_groups
                ]
                if measurement_group.compensation_matrix_groups
                else None,
            ),
        )

    def _get_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=measurement.measurement_identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=measurement.device_type,
                    )
                ],
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    add_custom_information_document(
                        ProcessedDataDocumentItem(
                            data_processing_document=DataProcessingDocument(
                                method_version=measurement.method_version,
                                data_processing_time=self.get_date_time(
                                    measurement.data_processing_time
                                )
                                if measurement.data_processing_time
                                else None,
                            ),
                            processed_data_identifier=measurement.processed_data_identifier,
                            population_aggregate_document=[
                                PopulationAggregateDocumentItem(
                                    population_document=[
                                        self._get_population_document(population)
                                        for population in measurement.populations
                                    ]
                                    if measurement.populations
                                    else None
                                )
                            ],
                            data_region_aggregate_document=DataRegionAggregateDocument(
                                data_region_document=[
                                    self._get_data_region_document(data_region)
                                    for data_region in measurement.data_regions
                                ]
                                if measurement.data_regions
                                else None
                            ),
                        ),
                        measurement.processed_data_custom_info,
                    )
                ]
            ),
        )

    def _get_data_region_document(
        self, data_region: DataRegion
    ) -> DataRegionDocumentItem:
        return DataRegionDocumentItem(
            data_region_identifier=data_region.region_data_identifier,
            region_type=data_region.region_data_type,
            parent_data_region_identifier=data_region.parent_data_region_identifier,
            x_coordinate_dimension_identifier=data_region.x_coordinate_dimension_identifier,
            y_coordinate_dimension_identifier=data_region.y_coordinate_dimension_identifier,
            vertex_aggregate_document=self._get_vertex_aggregate_document(
                data_region.vertices
            ),
        )

    def _get_vertex_aggregate_document(
        self, vertices: list[Vertex] | None
    ) -> VertexAggregateDocument | None:
        if not vertices:
            return None
        return VertexAggregateDocument(
            vertex_document=[
                VertexDocumentItem(
                    x_coordinate=quantity_or_none_from_unit(vertex.x_unit, vertex.x_coordinate),  # type: ignore[arg-type]
                    y_coordinate=quantity_or_none_from_unit(vertex.y_unit, vertex.y_coordinate),  # type: ignore[arg-type]
                    vertex_role=vertex.vertex_role,
                )
                for vertex in vertices
            ]
        )

    def _get_population_document(
        self, population: Population
    ) -> PopulationDocumentItem:
        return add_custom_information_document(
            PopulationDocumentItem(
                population_identifier=population.population_identifier,
                written_name=population.written_name,
                data_region_identifier=population.data_region_identifier,
                count=quantity_or_none(TQuantityValueCounts, value=population.count),
                parent_population_identifier=population.parent_population_identifier,
                population_aggregate_document=[
                    PopulationAggregateDocumentItem(
                        population_document=[
                            self._get_population_document(sub_population)
                            for sub_population in population.sub_populations
                        ]
                    )
                ]
                if population.sub_populations
                else None,
                statistics_aggregate_document=self._get_statistics_aggregate_document(
                    population.statistics
                ),
            ),
            population.custom_info,
        )

    def _get_compensation_matrix_document(
        self, compensation_matrix_group: CompensationMatrixGroup
    ) -> CompensationMatrixDocumentItem:
        return CompensationMatrixDocumentItem(
            dimension_identifier=compensation_matrix_group.dimension_identifier,
            matrix_aggregate_document=MatrixAggregateDocument(
                matrix_document=[
                    MatrixDocumentItem(
                        dimension_identifier=compensation.dimension_identifier,
                        compensation_value=quantity_or_none(
                            TQuantityValueUnitless, compensation.compensation_value
                        ),
                    )
                    for compensation in compensation_matrix_group.compensation_matrices
                ]
                if compensation_matrix_group.compensation_matrices
                else None,
            ),
        )

    def _get_statistics_aggregate_document(
        self, statistics: list[Statistic] | None
    ) -> StatisticsAggregateDocument | None:
        if not statistics:
            return None
        return StatisticsAggregateDocument(
            statistics_document=[
                StatisticsDocumentItem(
                    statistical_feature=statistic.statistical_feature,
                    statistic_dimension_aggregate_document=StatisticDimensionAggregateDocument(
                        statistic_dimension_document=[
                            StatisticDimensionDocumentItem(
                                dimension_identifier=statistic_dimension.dimension_identifier,
                                statistical_value=TQuantityValue(
                                    value=statistic_dimension.value,
                                    unit=statistic_dimension.unit,
                                    has_statistic_datum_role=TStatisticDatumRole(
                                        statistic_dimension.has_statistic_datum_role
                                    )
                                    if statistic_dimension.has_statistic_datum_role
                                    in {role.value for role in TStatisticDatumRole}
                                    else None,
                                ),
                            )
                            for statistic_dimension in statistic.statistic_dimension
                        ]
                    ),
                )
                for statistic in statistics
            ]
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return add_custom_information_document(
            SampleDocument(
                sample_identifier=measurement.sample_identifier,
                location_identifier=measurement.location_identifier,
                well_plate_identifier=measurement.well_plate_identifier,
                written_name=measurement.written_name,
                batch_identifier=measurement.batch_identifier,
            ),
            measurement.sample_custom_info,
        )
