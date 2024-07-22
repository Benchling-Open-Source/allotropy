from collections.abc import Callable
from dataclasses import dataclass

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
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    TCalculatedDataAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
    TQuantityValueNumberPerMicroliter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TDateTimeValue,
    TQuantityValue,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import quantity_or_none


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
    sample_identifier: str
    location_identifier: str
    measurement_time: str
    target_identifier: str

    # Measurements
    concentration: float
    positive_partition_count: float
    total_partition_count: float
    negative_partition_count: float | None = None

    # Optional metadata
    sample_role_type: str | None = None
    plate_identifier: str | None = None

    # Optional settings
    reporter_dye_setting: str | None = None
    flourescence_intensity_threshold_setting: float | None = None

    # Processed data
    calculated_data: list[CalculatedDataItem] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float
    experimental_data_identifier: str | None = None


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

    def get_calculated_data_items(self) -> list[CalculatedDataItem]:
        return (self.calculated_data or []) + [
            calculated_data_item
            for measurement_group in self.measurement_groups
            for measurement in measurement_group.measurements
            for calculated_data_item in (measurement.calculated_data or [])
        ]


class Mapper:
    MANIFEST = "http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/dpcr.manifest"

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

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
                    software_name=data.metadata.software_name,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                dPCR_document=[
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
    ) -> DPCRDocumentItem:
        return DPCRDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                experimental_data_identifier=measurement_group.experimental_data_identifier,
                plate_well_count=TQuantityValueNumber(
                    value=measurement_group.plate_well_count
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
        return MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.measurement_time),
            target_DNA_description=measurement.target_identifier,
            total_partition_count=TQuantityValueNumber(
                value=measurement.total_partition_count
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
                        data_processing_document=DataProcessingDocument(
                            flourescence_intensity_threshold_setting=TQuantityValueUnitless(
                                value=measurement.flourescence_intensity_threshold_setting
                            )
                        )
                        if measurement.flourescence_intensity_threshold_setting
                        else None,
                    )
                ]
            ),
        )

    def _get_calculated_data_aggregate_document(
        self, data: Data
    ) -> TCalculatedDataAggregateDocument | None:
        if not (calculated_data_document := data.get_calculated_data_items()):
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
                for calculated_data_item in calculated_data_document
            ]
        )
