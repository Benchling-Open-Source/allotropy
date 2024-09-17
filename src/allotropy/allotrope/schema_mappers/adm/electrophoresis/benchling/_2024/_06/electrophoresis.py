from dataclasses import dataclass

from allotropy.allotrope.models.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataRegionAggregateDocument,
    DataRegionDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ElectrophoresisAggregateDocument,
    ElectrophoresisDocumentItem,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    PeakItem,
    PeakList,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    TQuantityValueModel,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValuePercent,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import (
    quantity_or_none,
    quantity_or_none_from_unit,
)


@dataclass(frozen=True)
class ProcessedDataFeature:
    identifier: str
    start: JsonFloat
    start_unit: str
    end: JsonFloat
    end_unit: str
    area: JsonFloat
    relative_area: JsonFloat
    position: JsonFloat | None = None
    position_unit: str | None = None
    height: JsonFloat | None = None
    relative_corrected_area: JsonFloat | None = None
    name: str | None = None
    comment: str | None = None


@dataclass(frozen=True)
class ProcessedData:
    peaks: list[ProcessedDataFeature]
    data_regions: list[ProcessedDataFeature]


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
class Error:
    error: str
    feature: str | None = None


@dataclass(frozen=True)
class Measurement:
    # Measurement metadata
    identifier: str
    measurement_time: str
    sample_identifier: str

    # Processed data
    processed_data: ProcessedData

    # Optional metadata
    description: str | None = None
    location_identifier: str | None = None

    # Optional settings
    compartment_temperature: float | None = None

    # Optional processed data
    calculated_data: list[CalculatedDataItem] | None = None

    # Errors
    errors: list[Error] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]


@dataclass(frozen=True)
class Metadata:
    device_type: str
    device_identifier: str | None = None
    model_number: str | None = None
    software_name: str | None = None
    detection_type: str | None = None
    unc_path: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None

    file_name: str | None = None
    data_system_instance_identifier: str | None = None

    analyst: str | None = None
    measurement_time: str | None = None
    analytical_method_identifier: str | None = None
    method_version: str | None = None
    experimental_data_identifier: str | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDataItem] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/electrophoresis/BENCHLING/2024/06/electrophoresis.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            electrophoresis_aggregate_document=ElectrophoresisAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    brand_name=data.metadata.brand_name,
                    product_manufacturer=data.metadata.product_manufacturer,
                    device_identifier=data.metadata.device_identifier,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    file_name=data.metadata.file_name,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                ),
                electrophoresis_document=[
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
    ) -> ElectrophoresisDocumentItem:
        return ElectrophoresisDocumentItem(
            analyst=metadata.analyst,
            analytical_method_identifier=metadata.analytical_method_identifier,
            method_version=metadata.method_version,
            experimental_data_identifier=metadata.experimental_data_identifier,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    self._get_measurement_document_item(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.measurement_time),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius,
                measurement.compartment_temperature,
            ),
            sample_document=self._get_sample_document(measurement),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detection_type=metadata.detection_type,
                    ),
                ]
            ),
            calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                measurement.calculated_data
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            description=measurement.description,
            location_identifier=measurement.location_identifier,
        )

    def _get_processed_data_aggregate_document(
        self, data: ProcessedData
    ) -> ProcessedDataAggregateDocument:
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    peak_list=PeakList(
                        peak=[
                            PeakItem(
                                peak_identifier=peak.identifier,
                                peak_name=peak.name,
                                peak_height=quantity_or_none(
                                    TQuantityValueRelativeFluorescenceUnit, peak.height
                                ),
                                # TODO(nstender): figure out how to limit possible classes from get_quantity_class for typing.
                                peak_start=quantity_or_none_from_unit(peak.start_unit, peak.start),  # type: ignore[arg-type]
                                peak_end=quantity_or_none_from_unit(peak.end_unit, peak.end),  # type: ignore[arg-type]
                                peak_position=quantity_or_none_from_unit(peak.position_unit, peak.position),  # type: ignore[arg-type]
                                peak_area=quantity_or_none(
                                    TQuantityValueUnitless, peak.area
                                ),
                                relative_peak_area=quantity_or_none(
                                    TQuantityValuePercent, peak.relative_area
                                ),
                                relative_corrected_peak_area=quantity_or_none(
                                    TQuantityValuePercent, peak.relative_corrected_area
                                ),
                                comment=peak.comment,
                            )
                            for peak in data.peaks
                        ]
                    ),
                    data_region_aggregate_document=DataRegionAggregateDocument(
                        data_region_document=[
                            DataRegionDocumentItem(
                                region_identifier=data_region.identifier,
                                region_name=data_region.name,
                                # TODO(nstender): figure out how to limit possible classes from get_quantity_class for typing.
                                region_start=quantity_or_none_from_unit(data_region.start_unit, data_region.start),  # type: ignore[arg-type]
                                region_end=quantity_or_none_from_unit(data_region.end_unit, data_region.end),  # type: ignore[arg-type]
                                region_area=TQuantityValueUnitless(
                                    value=data_region.area
                                ),
                                relative_region_area=TQuantityValuePercent(
                                    value=data_region.relative_area
                                ),
                                comment=data_region.comment,
                            )
                            for data_region in data.data_regions
                        ]
                    )
                    if data.data_regions
                    else None,
                )
            ]
        )

    def _get_calculated_data_aggregate_document(
        self, calculated_data_items: list[CalculatedDataItem] | None
    ) -> CalculatedDataAggregateDocument | None:
        if not calculated_data_items:
            return None

        return CalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calculated_data_item.identifier,
                    calculated_data_name=calculated_data_item.name,
                    calculated_result=TQuantityValueModel(
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
                ErrorDocumentItem(error=error.error, error_feature=error.feature)
                for error in errors
            ]
        )
