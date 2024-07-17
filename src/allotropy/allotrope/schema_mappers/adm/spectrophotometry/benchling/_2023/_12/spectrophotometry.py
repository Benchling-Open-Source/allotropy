from collections.abc import Callable
from dataclasses import dataclass

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SpectrophotometryAggregateDocument,
    SpectrophotometryDocumentItem,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNanometer,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
    TDateTimeValue,
    TQuantityValue,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.units import get_quantity_class
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none


@dataclass(frozen=True)
class ProcessedDataFeature:
    result: float | InvalidJsonFloat
    unit: str
    feature: str | None = None
    identifier: str | None = None


@dataclass(frozen=True)
class ProcessedData:
    features: list[ProcessedDataFeature]
    identifier: str | None = None


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
    analyst: str | None = None
    measurement_time: str | None = None
    well_plate_identifier: str | None = None

    # Measurements
    absorbance: JsonFloat | None = None

    # Processed data
    calculated_data: list[CalculatedDataItem] | None = None
    processed_data: ProcessedData | None = None

    # Settings
    detector_wavelength_setting: JsonFloat | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float | None = None
    _measurement_time: str | None = None
    experiment_type: str | None = None
    analyst: str | None = None
    processed_data: ProcessedData | None = None

    @property
    def measurement_time(self) -> str | None:
        if self._measurement_time is not None:
            return self._measurement_time
        if (
            self.measurements
            and len({m.measurement_time for m in self.measurements}) == 1
            and self.measurements[0].measurement_time
        ):
            return self.measurements[0].measurement_time
        return None


@dataclass(frozen=True)
class Metadata:
    device_identifier: str
    device_type: str
    model_number: str
    software_name: str | None = None
    detection_type: str | None = None
    unc_path: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None

    file_name: str | None = None
    data_system_instance_id: str | None = None

    analyst: str | None = None
    measurement_time: str | None = None


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
    MANIFEST = "http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest"

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

    def map_model(self, data: Data) -> Model:
        return Model(
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                spectrophotometry_document=[
                    SpectrophotometryDocumentItem(
                        analyst=measurement_group.analyst,
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            measurement_time=self.get_date_time(
                                assert_not_none(measurement_group.measurement_time)
                            ),
                            experiment_type=measurement_group.experiment_type,
                            measurement_document=[
                                self._get_measurement_document_item(
                                    measurement, data.metadata
                                )
                                for measurement in measurement_group.measurements
                            ],
                        ),
                    )
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data
                ),
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_measurement_document_item(
        self, measurement: Measurement, metadata: Metadata
    ) -> UltravioletAbsorbancePointDetectionMeasurementDocumentItems:
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=assert_not_none(  # type: ignore[arg-type]
                                measurement.detector_wavelength_setting
                            ),
                        ),
                    )
                ]
            ),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=assert_not_none(measurement.absorbance)  # type: ignore[arg-type]
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            well_plate_identifier=measurement.well_plate_identifier,
            location_identifier=measurement.location_identifier,
        )

    def _get_processed_data_aggregate_document(
        self, data: ProcessedData | None
    ) -> ProcessedDataAggregateDocument | None:
        if not data:
            return None

        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    # NOTE: mypy is mad because mass_concentration asserts a subset of TQuantityValue
                    mass_concentration=quantity_or_none(
                        get_quantity_class(feature.unit), feature.result  # type: ignore[arg-type]
                    ),
                    processed_data_identifier=data.identifier,
                )
                for feature in data.features
            ]
        )

    def _get_calculated_data_aggregate_document(
        self, data: Data
    ) -> CalculatedDataAggregateDocument | None:
        if not (calculated_data_document := data.get_calculated_data_items()):
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
                for calculated_data_item in calculated_data_document
            ]
        )
