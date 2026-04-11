from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueMicroliter,
    TQuantityValueMicrometer,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    JsonFloat,
)
from allotropy.allotrope.models_v2.adm.cell_counting.rec._2024._09.cell_counting import (
    AverageDeadCellDiameterCellCounter,
    AverageLiveCellDiameterCellCounter,
    AverageTotalCellCircularity,
    AverageTotalCellDiameter,
    AverageViableCellCircularity,
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    CellCountingAggregateDocument,
    CellCountingDocumentItem,
    CellDensityDilutionFactor,
    DataProcessingDocument,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeadCellCount,
    DeadCellDensityCellCounter,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    ImageAggregateDocument,
    ImageDocumentItem,
    MaximumCellDiameterSetting,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    MinimumCellDiameterSetting,
    Model,
    ProcessedDataAggregateDocument1,
    ProcessedDataDocumentItem,
    SampleDocument,
    SampleVolumeSetting,
    TotalCellCount,
    TotalCellDensityCellCounter,
    TQuantityValue,
    ViabilityCellCounter,
    ViableCellCount,
    ViableCellDensityCellCounter,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.calculated_data_documents.definition import DataSource
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class Error:
    error: str
    feature: str | None = None


@dataclass
class Measurement:
    # Metadata
    measurement_identifier: str
    timestamp: str
    sample_identifier: str

    # Measurements
    viability: float
    viable_cell_density: float

    # Optional metadata
    batch_identifier: str | None = None
    group_identifier: str | None = None
    sample_draw_time: str | None = None
    written_name: str | None = None
    processed_data_identifier: str | None = None

    # Optional settings
    cell_type_processing_method: str | None = None
    minimum_cell_diameter_setting: float | None = None
    maximum_cell_diameter_setting: float | None = None
    cell_density_dilution_factor: float | None = None
    sample_volume_setting: float | None = None
    dilution_volume: float | None = None

    # Optional measurements
    viable_cell_count: float | None = None
    total_cell_count: float | None = None
    total_cell_density: float | None = None
    dead_cell_count: float | None = None
    dead_cell_density: float | None = None

    average_total_cell_diameter: float | None = None
    average_live_cell_diameter: float | None = None
    average_dead_cell_diameter: float | None = None
    average_total_cell_circularity: float | None = None
    average_viable_cell_circularity: float | None = None

    average_compactness: float | None = None
    average_area: float | None = None
    average_perimeter: float | None = None
    average_segment_area: float | None = None
    total_object_count: float | None = None
    standard_deviation: float | None = None
    aggregate_rate: float | None = None
    experimental_data_identifier: str | None = None

    errors: list[Error] | None = None

    # customer information document fields
    debris_index: float | None = None
    cell_aggregation_percentage: float | None = None
    aggregate_size: float | None = None
    aggregate_count: float | None = None
    sample_custom_info: dict[str, Any] | None = None
    custom_info: dict[str, Any] | None = None

    # Custom information documents
    device_control_custom_info: dict[str, Any] | None = None
    image_processing_custom_info: dict[str, Any] | None = None
    data_processing_custom_info: dict[str, Any] | None = None
    processed_data_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    analyst: str | None = None
    custom_info: dict[str, Any] | None = None


@dataclass
class Metadata:
    asm_file_identifier: str
    data_system_instance_id: str
    device_type: str
    model_number: str | None = None
    device_identifier: str | None = None
    detection_type: str | None = None
    software_name: str | None = None
    file_name: str | None = None
    unc_path: str | None = None
    equipment_serial_number: str | None = None
    software_version: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None
    asset_management_identifier: str | None = None
    description: str | None = None
    data_system_custom_info: dict[str, Any] | None = None
    device_system_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class CalculatedDataItem:
    identifier: str
    name: str
    value: JsonFloat
    unit: str
    data_sources: list[DataSource]
    description: str | None = None


@dataclass
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDataItem] | None = None


def has_value(model: object) -> bool:
    return any(value is not None for value in model.__dict__.values())


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/cell-counting/REC/2024/09/cell-counting.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest=self.MANIFEST,
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=add_custom_information_document(
                    DeviceSystemDocument(
                        model_number=data.metadata.model_number,
                        product_manufacturer=data.metadata.product_manufacturer,
                        brand_name=data.metadata.brand_name,
                        asset_management_identifier=data.metadata.asset_management_identifier,
                        device_identifier=data.metadata.device_identifier,
                        description=data.metadata.description,
                        equipment_serial_number=data.metadata.equipment_serial_number,
                    ),
                    data.metadata.device_system_custom_info or {},
                ),
                data_system_document=add_custom_information_document(
                    DataSystemDocument(
                        data_system_instance_identifier=data.metadata.data_system_instance_id,
                        file_name=data.metadata.file_name,
                        unc_path=data.metadata.unc_path,
                        software_name=data.metadata.software_name,
                        software_version=data.metadata.software_version,
                        asm_converter_name=self.converter_name,
                        asm_converter_version=ASM_CONVERTER_VERSION,
                        asm_file_identifier=data.metadata.asm_file_identifier,
                    ),
                    data.metadata.data_system_custom_info or {},
                ),
                cell_counting_document=[
                    self._get_technique_document(
                        measurement_group, data.metadata, data.calculated_data
                    )
                    for measurement_group in data.measurement_groups
                ],
            ),
        )

    def _get_technique_document(
        self,
        measurement_group: MeasurementGroup,
        metadata: Metadata,
        calculated_data: list[CalculatedDataItem] | None = None,
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=add_custom_information_document(
                MeasurementAggregateDocument(
                    measurement_document=[
                        self._get_measurement_document(measurement, metadata)
                        for measurement in measurement_group.measurements
                    ],
                    calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                        calculated_data
                    ),
                ),
                measurement_group.custom_info or {},
            ),
        )

    def _get_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocumentItem:
        device_control_doc = DeviceControlDocumentItem(
            device_type=metadata.device_type,
            detection_type=metadata.detection_type,
            sample_volume_setting=(
                SampleVolumeSetting(value=measurement.sample_volume_setting)
                if measurement.sample_volume_setting is not None
                else None
            ),
        )
        device_control_doc = add_custom_information_document(
            device_control_doc, measurement.device_control_custom_info or {}
        )
        measurement_document = MeasurementDocumentItem(
            measurement_time=self.get_date_time(measurement.timestamp),
            measurement_identifier=measurement.measurement_identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[device_control_doc]
            ),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
            image_aggregate_document=ImageAggregateDocument(
                image_document=[
                    add_custom_information_document(
                        ImageDocumentItem(
                            experimental_data_identifier=measurement.experimental_data_identifier
                        ),
                        measurement.image_processing_custom_info or {},
                    )
                ],
            )
            if measurement.experimental_data_identifier
            or measurement.image_processing_custom_info
            else None,
        )
        return add_custom_information_document(
            measurement_document, measurement.custom_info or {}
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        # TODO(ASM gaps): we believe these values should be introduced to ASM.
        custom_document = {
            "group identifier": measurement.group_identifier,
            "sample draw time": (
                self.get_date_time(measurement.sample_draw_time)
                if measurement.sample_draw_time
                else None
            ),
            "dilution volume": quantity_or_none(
                TQuantityValueMicroliter, measurement.dilution_volume
            ),
        }
        custom_document.update(measurement.sample_custom_info or {})
        return add_custom_information_document(
            SampleDocument(
                sample_identifier=measurement.sample_identifier,
                batch_identifier=measurement.batch_identifier,
                written_name=measurement.written_name,
            ),
            custom_document,
        )

    def _get_processed_data_aggregate_document(
        self, measurement: Measurement
    ) -> ProcessedDataAggregateDocument1:
        # TODO(ASM gaps): we believe average values and stddev should be added to the processed data document.
        # TODO(ASM gaps): we believe "total object count" and "aggregate rate" should be introduced to ASM.
        custom_document = {
            "average compactness": quantity_or_none(
                TQuantityValueUnitless, measurement.average_compactness
            ),
            "average area": quantity_or_none(
                TQuantityValueUnitless, measurement.average_area
            ),
            "average perimeter": quantity_or_none(
                TQuantityValueMicrometer, measurement.average_perimeter
            ),
            "average segment area": quantity_or_none(
                TQuantityValueUnitless, measurement.average_segment_area
            ),
            "total object count": quantity_or_none(
                TQuantityValueCell, measurement.total_object_count
            ),
            "standard deviation": quantity_or_none(
                TQuantityValueCell, measurement.standard_deviation
            ),
            "aggregate rate": quantity_or_none(
                TQuantityValuePercent, measurement.aggregate_rate
            ),
            "cell aggregation percentage": quantity_or_none(
                TQuantityValuePercent, measurement.cell_aggregation_percentage
            ),
            "aggregate size": quantity_or_none(
                TQuantityValueMicrometer, measurement.aggregate_size
            ),
            "aggregate count": quantity_or_none(
                TQuantityValueCell, measurement.aggregate_count
            ),
            "debris index": quantity_or_none(
                TQuantityValueUnitless, measurement.debris_index
            ),
        }
        data_processing_document = add_custom_information_document(
            DataProcessingDocument(
                cell_type_processing_method=measurement.cell_type_processing_method,
                minimum_cell_diameter_setting=(
                    MinimumCellDiameterSetting(
                        value=measurement.minimum_cell_diameter_setting,
                    )
                    if measurement.minimum_cell_diameter_setting is not None
                    else None
                ),
                maximum_cell_diameter_setting=(
                    MaximumCellDiameterSetting(
                        value=measurement.maximum_cell_diameter_setting,
                    )
                    if measurement.maximum_cell_diameter_setting is not None
                    else None
                ),
                cell_density_dilution_factor=(
                    CellDensityDilutionFactor(
                        value=measurement.cell_density_dilution_factor,
                    )
                    if measurement.cell_density_dilution_factor is not None
                    else None
                ),
            ),
            measurement.data_processing_custom_info or {},
        )
        processed_data_document = ProcessedDataDocumentItem(
            processed_data_identifier=measurement.processed_data_identifier,
            data_processing_document=(
                data_processing_document
                if has_value(data_processing_document)
                else None
            ),
            viability__cell_counter_=ViabilityCellCounter(
                value=measurement.viability,
            ),
            viable_cell_density__cell_counter_=ViableCellDensityCellCounter(
                value=measurement.viable_cell_density,
            ),
            dead_cell_density__cell_counter_=(
                DeadCellDensityCellCounter(value=measurement.dead_cell_density)
                if measurement.dead_cell_density is not None
                else None
            ),
            total_cell_count=(
                TotalCellCount(value=measurement.total_cell_count)
                if measurement.total_cell_count is not None
                else None
            ),
            total_cell_density__cell_counter_=(
                TotalCellDensityCellCounter(value=measurement.total_cell_density)
                if measurement.total_cell_density is not None
                else None
            ),
            average_total_cell_diameter=(
                AverageTotalCellDiameter(value=measurement.average_total_cell_diameter)
                if measurement.average_total_cell_diameter is not None
                else None
            ),
            average_live_cell_diameter__cell_counter_=(
                AverageLiveCellDiameterCellCounter(
                    value=measurement.average_live_cell_diameter,
                )
                if measurement.average_live_cell_diameter is not None
                else None
            ),
            average_dead_cell_diameter__cell_counter_=(
                AverageDeadCellDiameterCellCounter(
                    value=measurement.average_dead_cell_diameter,
                )
                if measurement.average_dead_cell_diameter is not None
                else None
            ),
            viable_cell_count=(
                ViableCellCount(value=measurement.viable_cell_count)
                if measurement.viable_cell_count is not None
                else None
            ),
            dead_cell_count=(
                DeadCellCount(value=measurement.dead_cell_count)
                if measurement.dead_cell_count is not None
                else None
            ),
            average_total_cell_circularity=(
                AverageTotalCellCircularity(
                    value=measurement.average_total_cell_circularity,
                )
                if measurement.average_total_cell_circularity is not None
                else None
            ),
            average_viable_cell_circularity=(
                AverageViableCellCircularity(
                    value=measurement.average_viable_cell_circularity,
                )
                if measurement.average_viable_cell_circularity is not None
                else None
            ),
        )
        return ProcessedDataAggregateDocument1(
            processed_data_document=[
                add_custom_information_document(
                    processed_data_document,
                    custom_document | (measurement.processed_data_custom_info or {}),
                )
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
