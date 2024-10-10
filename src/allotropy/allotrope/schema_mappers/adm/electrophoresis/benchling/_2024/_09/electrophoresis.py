from dataclasses import dataclass

from allotropy.allotrope.models.adm.electrophoresis.benchling._2024._09.electrophoresis import (
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
    MeasurementDocument,
    Model,
    Peak,
    PeakList,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValuePercent,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    JsonFloat,
    TQuantityValue,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import (
    quantity_or_none,
    quantity_or_none_from_unit,
)


@dataclass(frozen=True)
class ProcessedDataFeature:
    identifier: str
    start: JsonFloat | None = None
    start_unit: str | None = None
    end: JsonFloat | None = None
    end_unit: str | None = None
    area: JsonFloat | None = None
    relative_area: JsonFloat | None = None
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
    data_system_instance_identifier: str
    analyst: str
    file_identifier: str

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
    MANIFEST = "http://purl.allotrope.org/manifests/electrophoresis/BENCHLING/2024/09/electrophoresis.manifest"

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
                    UNC_path=data.metadata.unc_path,
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    file_name=data.metadata.file_name,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    ASM_file_identifier=data.metadata.file_identifier,
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
            measurement_aggregate_document=MeasurementAggregateDocument(
                analytical_method_identifier=metadata.analytical_method_identifier,
                method_version=metadata.method_version,
                experimental_data_identifier=metadata.experimental_data_identifier,
                measurement_document=[
                    self._get_measurement_document_item(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocument:
        return MeasurementDocument(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.measurement_time),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius,
                measurement.compartment_temperature,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_identifier=metadata.device_identifier,
                        device_type=metadata.device_type,
                        detection_type=metadata.detection_type,
                    ),
                ]
            ),
            sample_document=self._get_sample_document(measurement),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
            calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                measurement.calculated_data
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
                        peak=[self._get_peak(peak) for peak in data.peaks]
                    ),
                    data_region_aggregate_document=DataRegionAggregateDocument(
                        data_region_document=[
                            self._get_data_region_agg_document(data_region)
                            for data_region in data.data_regions
                        ]
                    )
                    if data.data_regions
                    else None,
                )
            ]
        )

    def _get_peak(self, peak: ProcessedDataFeature) -> Peak:
        return Peak(
            identifier=peak.identifier,
            peak_name=peak.name,
            comment=peak.comment,
            # TODO(nstender): figure out how to limit possible classes from get_quantity_class for typing.
            peak_height=(
                quantity_or_none(TQuantityValueRelativeFluorescenceUnit, peak.height)
                if peak.height
                else None
            ),
            peak_position=(
                quantity_or_none_from_unit(peak.position_unit, peak.position)  # type: ignore[arg-type]
                if peak.position
                else None
            ),
            relative_corrected_peak_area=(
                quantity_or_none(TQuantityValuePercent, peak.relative_corrected_area)
                if peak.relative_corrected_area
                else None
            ),
            peak_start=(
                quantity_or_none_from_unit(peak.start_unit, peak.start)  # type: ignore[arg-type]
                if peak.start
                else None
            ),
            peak_end=(
                quantity_or_none_from_unit(peak.end_unit, peak.end)  # type: ignore[arg-type]
                if peak.end
                else None
            ),
            peak_area=(
                quantity_or_none(TQuantityValueUnitless, peak.area)
                if peak.area
                else None
            ),
            relative_peak_area=(
                quantity_or_none(TQuantityValuePercent, peak.relative_area)
                if peak.relative_area
                else None
            ),
        )

    def _get_data_region_agg_document(
        self, data_region: ProcessedDataFeature
    ) -> DataRegionDocumentItem:
        return DataRegionDocumentItem(
            data_region_identifier=data_region.identifier,
            data_region_name=data_region.name,
            comment=data_region.comment,
            # TODO(nstender): figure out how to limit possible classes from get_quantity_class for typing.
            data_region_start=(
                quantity_or_none_from_unit(data_region.start_unit, data_region.start)  # type: ignore[arg-type]
                if data_region.start
                else None
            ),
            data_region_end=(
                quantity_or_none_from_unit(data_region.end_unit, data_region.end)  # type: ignore[arg-type]
                if data_region.end
                else None
            ),
            data_region_area=(
                TQuantityValueUnitless(value=data_region.area)
                if data_region.area
                else None
            ),
            relative_data_region_area=(
                TQuantityValuePercent(value=data_region.relative_area)
                if data_region.relative_area
                else None
            ),
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
                    calculated_result=TQuantityValue(
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
