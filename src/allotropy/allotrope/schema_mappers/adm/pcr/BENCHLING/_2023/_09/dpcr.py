from dataclasses import dataclass
from typing import Any, TypeVar

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import (
    CalculatedDataDocumentItem,
    ContainerType,
    DataProcessingDocument,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    DPCRAggregateDocument,
    DPCRDocumentItem,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    PassiveReferenceDyeDataCube,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    ReporterDyeDataCube,
    SampleDocument,
    TCalculatedDataAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
    TQuantityValueNumberPerMicroliter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.schema_mappers.data_cube import DataCube, get_data_cube
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class DataSource:
    identifier: str
    feature: str


@dataclass(frozen=True)
class Error:
    error: str
    error_feature: str


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
    sample_identifier: str
    location_identifier: str
    measurement_time: str
    target_identifier: str

    # Measurements
    concentration: float
    positive_partition_count: float
    total_partition_count: float
    negative_partition_count: float | None = None
    confidence_interval__95__: float | None = None
    reporter_dye_data_cube: DataCube | None = None
    passive_reference_dye_data_cube: DataCube | None = None

    # Optional metadata
    sample_role_type: str | None = None
    plate_identifier: str | None = None

    # Optional settings
    reporter_dye_setting: str | None = None
    passive_reference_dye_setting: str | None = None
    fluorescence_intensity_threshold_setting: float | None = None

    # error documents
    errors: list[Error] | None = None

    # custom
    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float
    experimental_data_identifier: str | None = None
    # error documents
    errors: list[Error] | None = None


@dataclass(frozen=True)
class Metadata:
    device_identifier: str
    device_type: str
    software_name: str
    model_number: str | None = None
    detection_type: str | None = None
    unc_path: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None
    file_name: str | None = None
    data_system_instance_id: str | None = None
    analyst: str | None = None
    measurement_time: str | None = None
    brand_name: str | None = None
    container_type: ContainerType | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDataItem] | None = None


CubeClass = TypeVar("CubeClass")


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/dpcr.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            dPCR_aggregate_document=DPCRAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    brand_name=data.metadata.brand_name,
                    product_manufacturer=data.metadata.product_manufacturer,
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                dPCR_document=[
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
    ) -> DPCRDocumentItem:
        return DPCRDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                experimental_data_identifier=measurement_group.experimental_data_identifier,
                plate_well_count=TQuantityValueNumber(
                    value=measurement_group.plate_well_count
                ),
                error_aggregate_document=self._get_error_aggregate_document(
                    measurement_group.errors
                ),
                container_type=metadata.container_type,
                measurement_document=[
                    self._get_measurement_document(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
            )
        )

    def _get_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocumentItem:
        measurement_doc = MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.measurement_time),
            target_DNA_description=measurement.target_identifier,
            total_partition_count=TQuantityValueNumber(
                value=measurement.total_partition_count
            ),
            reporter_dye_data_cube=get_data_cube(
                measurement.reporter_dye_data_cube, ReporterDyeDataCube
            ),
            passive_reference_dye_data_cube=get_data_cube(
                measurement.passive_reference_dye_data_cube, PassiveReferenceDyeDataCube
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                well_location_identifier=measurement.location_identifier,
                well_plate_identifier=measurement.plate_identifier,
                sample_role_type=measurement.sample_role_type,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        # TODO(nstender): I think these should prob be removed for now, since every example
                        # we have so far is constant over the whole doc (or at least moved to a nullable
                        # per-measurement metadata for overrides). Going with being consistent/adding more
                        # info than needed for now.
                        device_type=metadata.device_type,
                        device_identifier=metadata.device_identifier,
                        reporter_dye_setting=measurement.reporter_dye_setting,
                        passive_reference_dye_setting=measurement.passive_reference_dye_setting,
                    )
                ]
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(
                        number_concentration=TQuantityValueNumberPerMicroliter(
                            value=measurement.concentration
                        ),
                        positive_partition_count=TQuantityValueNumber(
                            value=measurement.positive_partition_count
                        ),
                        negative_partition_count=quantity_or_none(
                            TQuantityValueNumber, measurement.negative_partition_count
                        ),
                        confidence_interval__95__=quantity_or_none(
                            TQuantityValueNumber, measurement.confidence_interval__95__
                        ),
                        data_processing_document=DataProcessingDocument(
                            fluorescence_intensity_threshold_setting=TQuantityValueUnitless(
                                value=measurement.fluorescence_intensity_threshold_setting
                            )
                        )
                        if measurement.fluorescence_intensity_threshold_setting
                        else None,
                    )
                ]
            ),
        )
        return add_custom_information_document(measurement_doc, measurement.custom_info)

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
                    calculated_datum=TQuantityValue(
                        value=calculated_data_item.value,
                        unit=calculated_data_item.unit,
                    ),
                    data_source_aggregate_document=DataSourceAggregateDocument(
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

    def _get_error_aggregate_document(
        self, errors: list[Error] | None
    ) -> ErrorAggregateDocument | None:
        if not errors:
            return None
        return ErrorAggregateDocument(
            error_document=[
                ErrorDocumentItem(error=error.error, error_feature=error.error_feature)
                for error in errors
            ]
        )
