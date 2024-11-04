from dataclasses import dataclass

from allotropy.allotrope.models.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    CalculatedDataDocumentItem,
    DataProcessingDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceDocumentItem,
    DeviceSystemDocument,
    DistributionAggregateDocument,
    DistributionDocumentItem,
    DistributionItem,
    LightObscurationAggregateDocument,
    LightObscurationDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    TCalculatedDataAggregateDocument,
    TDataSourceAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCountsPerMilliliter,
    TQuantityValueMicrometer,
    TQuantityValueMilliliter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TQuantityValue,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class ProcessedDataFeature:
    identifier: str
    particle_size: float
    cumulative_count: float
    cumulative_particle_density: float
    differential_particle_density: float | None = None
    differential_count: float | None = None


@dataclass(frozen=True)
class ProcessedData:
    dilution_factor_setting: float
    distributions: list[ProcessedDataFeature]


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


@dataclass(frozen=True)
class Measurement:
    # Measurement metadata
    identifier: str
    measurement_time: str
    sample_identifier: str
    flush_volume_setting: float
    detector_view_volume: float
    repetition_setting: int
    sample_volume_setting: float

    # Processed data
    processed_data: ProcessedData

    # Optional processed data
    calculated_data: list[CalculatedDataItem] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    analyst: str
    measurements: list[Measurement]


@dataclass(frozen=True)
class Metadata:
    file_name: str
    unc_path: str
    equipment_serial_number: str
    detector_identifier: str
    detector_model_number: str
    software_version: str
    software_name: str


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDataItem] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/light-obscuration/BENCHLING/2023/12/light-obscuration.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            light_obscuration_aggregate_document=LightObscurationAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    device_document=[
                        DeviceDocumentItem(
                            detector_identifier=data.metadata.detector_identifier,
                            detector_model_number=data.metadata.detector_model_number,
                        )
                    ],
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    software_name=data.metadata.software_name,
                    UNC_path=data.metadata.unc_path,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                light_obscuration_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data.calculated_data
                ),
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> LightObscurationDocumentItem:
        return LightObscurationDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                analyst=measurement_group.analyst,
                measurement_document=[
                    self._get_measurement_document_item(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurement, _: Metadata
    ) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.measurement_time),
            sample_document=self._get_sample_document(measurement),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        flush_volume_setting=TQuantityValueMilliliter(
                            value=measurement.flush_volume_setting
                        ),
                        detector_view_volume=TQuantityValueMilliliter(
                            value=measurement.detector_view_volume
                        ),
                        repetition_setting=measurement.repetition_setting,
                        sample_volume_setting=TQuantityValueMilliliter(
                            value=measurement.sample_volume_setting,
                        ),
                    )
                ]
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
        )

    def _get_processed_data_aggregate_document(
        self, data: ProcessedData
    ) -> ProcessedDataAggregateDocument:
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    data_processing_document=DataProcessingDocument(
                        dilution_factor_setting=TQuantityValueUnitless(
                            value=data.dilution_factor_setting,
                        )
                    ),
                    distribution_aggregate_document=DistributionAggregateDocument(
                        distribution_document=[
                            DistributionDocumentItem(
                                distribution=[
                                    DistributionItem(
                                        distribution_identifier=feature.identifier,
                                        particle_size=TQuantityValueMicrometer(
                                            value=feature.particle_size
                                        ),
                                        cumulative_count=TQuantityValueUnitless(
                                            value=feature.cumulative_count
                                        ),
                                        cumulative_particle_density=TQuantityValueCountsPerMilliliter(
                                            value=feature.cumulative_particle_density
                                        ),
                                        differential_particle_density=quantity_or_none(
                                            TQuantityValueCountsPerMilliliter,
                                            feature.differential_particle_density,
                                        ),
                                        differential_count=quantity_or_none(
                                            TQuantityValueUnitless,
                                            feature.differential_count,
                                        ),
                                    )
                                    for feature in data.distributions
                                ]
                            )
                        ]
                    ),
                )
            ]
        )

    def _get_calculated_data_aggregate_document(
        self, calculated_data_items: list[CalculatedDataItem] | None
    ) -> TCalculatedDataAggregateDocument | None:
        if not calculated_data_items:
            return None

        return TCalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calculated_data_item.identifier,
                    calculated_data_name=calculated_data_item.name,
                    # TODO(nstender): figure out how to convince typing that unit is correct.
                    calculated_result=TQuantityValue(  # type:ignore[arg-type]
                        value=calculated_data_item.value,
                        unit=calculated_data_item.unit,
                    ),
                    data_source_aggregate_document=TDataSourceAggregateDocument(
                        data_source_document=[
                            DataSourceDocumentItem(
                                data_source_identifier=item.identifier,
                                data_source_feature=item.feature,
                            )
                            for item in calculated_data_item.data_sources
                        ]
                    ),
                )
                for calculated_data_item in calculated_data_items
            ]
        )
