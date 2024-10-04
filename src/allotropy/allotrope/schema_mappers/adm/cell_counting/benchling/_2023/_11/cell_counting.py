from dataclasses import dataclass

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    CellCountingAggregateDocument,
    CellCountingDetectorDeviceControlAggregateDocument,
    CellCountingDetectorMeasurementDocumentItem,
    CellCountingDocumentItem,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlDocumentItemModel,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueMicroliter,
    TQuantityValueMicrometer,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
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
    viable_cell_density: JsonFloat

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

    # Optional measurements
    viable_cell_count: float | None = None
    total_cell_count: float | None = None
    total_cell_density: JsonFloat | None = None
    dead_cell_count: float | None = None
    dead_cell_density: JsonFloat | None = None

    average_total_cell_diameter: JsonFloat | None = None
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

    errors: list[Error] | None = None

    # customer information document fields
    debris_index: float | None = None
    cell_aggregation_percentage: JsonFloat | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    analyst: str | None = None


@dataclass
class Metadata:
    device_type: str
    detection_type: str | None = None
    model_number: str | None = None
    software_name: str | None = None
    file_name: str | None = None
    unc_path: str | None = None
    equipment_serial_number: str | None = None
    software_version: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None
    asset_management_identifier: str | None = None
    device_identifier: str | None = None
    description: str | None = None


@dataclass
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


def has_value(model: object) -> bool:
    return any(value is not None for value in model.__dict__.values())


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest=self.MANIFEST,
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    product_manufacturer=data.metadata.product_manufacturer,
                    brand_name=data.metadata.brand_name,
                    asset_management_identifier=data.metadata.asset_management_identifier,
                    device_identifier=data.metadata.device_identifier,
                    description=data.metadata.description,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                cell_counting_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
            ),
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    self._get_measurement_document(measurement, metadata)
                    for measurement in measurement_group.measurements
                ]
            ),
        )

    def _get_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> CellCountingDetectorMeasurementDocumentItem:
        return CellCountingDetectorMeasurementDocumentItem(
            measurement_time=self.get_date_time(measurement.timestamp),
            measurement_identifier=measurement.measurement_identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=CellCountingDetectorDeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItemModel(
                        device_type=metadata.device_type,
                        detection_type=metadata.detection_type,
                        sample_volume_setting=quantity_or_none(
                            TQuantityValueMicroliter, measurement.sample_volume_setting
                        ),
                    )
                ]
            ),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        # TODO(ASM gaps): we believe these values should be introduced to ASM.
        custom_document = {
            "group identifier": measurement.group_identifier,
            "sample draw time": self.get_date_time(measurement.sample_draw_time)
            if measurement.sample_draw_time
            else None,
        }
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
    ) -> ProcessedDataAggregateDocument:
        # TODO: average values and stddev should be calculated data
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
            "debris index": quantity_or_none(
                TQuantityValueUnitless, measurement.debris_index
            ),
        }
        data_processing_document = DataProcessingDocument(
            cell_type_processing_method=measurement.cell_type_processing_method,
            minimum_cell_diameter_setting=quantity_or_none(
                TQuantityValueMicrometer,
                measurement.minimum_cell_diameter_setting,
            ),
            maximum_cell_diameter_setting=quantity_or_none(
                TQuantityValueMicrometer,
                measurement.maximum_cell_diameter_setting,
            ),
            cell_density_dilution_factor=quantity_or_none(
                TQuantityValueUnitless,
                measurement.cell_density_dilution_factor,
            ),
        )
        processed_data_document = ProcessedDataDocumentItem(
            processed_data_identifier=measurement.processed_data_identifier,
            data_processing_document=data_processing_document
            if has_value(data_processing_document)
            else None,
            viability__cell_counter_=TQuantityValuePercent(value=measurement.viability),
            viable_cell_density__cell_counter_=TQuantityValueMillionCellsPerMilliliter(
                value=measurement.viable_cell_density
            ),
            dead_cell_density__cell_counter_=quantity_or_none(
                TQuantityValueMillionCellsPerMilliliter,
                measurement.dead_cell_density,
            ),
            total_cell_count=quantity_or_none(
                TQuantityValueCell, measurement.total_cell_count
            ),
            total_cell_density__cell_counter_=quantity_or_none(
                TQuantityValueMillionCellsPerMilliliter,
                measurement.total_cell_density,
            ),
            average_total_cell_diameter=quantity_or_none(
                TQuantityValueMicrometer,
                measurement.average_total_cell_diameter,
            ),
            average_live_cell_diameter__cell_counter_=quantity_or_none(
                TQuantityValueMicrometer,
                measurement.average_live_cell_diameter,
            ),
            average_dead_cell_diameter__cell_counter_=quantity_or_none(
                TQuantityValueMicrometer,
                measurement.average_dead_cell_diameter,
            ),
            viable_cell_count=quantity_or_none(
                TQuantityValueCell, measurement.viable_cell_count
            ),
            dead_cell_count=quantity_or_none(
                TQuantityValueCell, measurement.dead_cell_count
            ),
            average_total_cell_circularity=quantity_or_none(
                TQuantityValueUnitless,
                measurement.average_total_cell_circularity,
            ),
            average_viable_cell_circularity=quantity_or_none(
                TQuantityValueUnitless,
                measurement.average_viable_cell_circularity,
            ),
        )
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                add_custom_information_document(
                    processed_data_document, custom_document
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
