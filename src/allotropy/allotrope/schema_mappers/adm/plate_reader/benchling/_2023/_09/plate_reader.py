from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    ContainerType,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
    ImageFeatureAggregateDocument,
    ImageFeatureDocumentItem,
    MeasurementAggregateDocument,
    Model,
    OpticalImagingDeviceControlAggregateDocument,
    OpticalImagingDeviceControlDocumentItem,
    OpticalImagingMeasurementDocumentItems,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilliSecond,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
    TDateTimeValue,
    TQuantityValue,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none


@dataclass(frozen=True)
class ImageFeature:
    identifier: str
    feature: str
    result: float | InvalidJsonFloat


@dataclass(frozen=True)
class ProcessedData:
    identifier: str
    features: list[ImageFeature]


@dataclass(frozen=True)
class DataSourceItem:
    identifier: str
    feature: str


@dataclass(frozen=True)
class CalculatedDataItem:
    identifier: str
    name: str
    value: float
    unit: str
    data_source_document: list[DataSourceItem]


class MeasurementType(Enum):
    OPTICAL_IMAGING = "OPTICAL_IMAGING"
    ULTRAVIOLET_ABSORBANCE = "ULTRAVIOLET_ABSORBANCE"


@dataclass(frozen=True)
class Measurement:
    type_: MeasurementType
    identifier: str
    sample_identifier: str
    location_identifier: str
    analyst: str | None = None
    measurement_time: str | None = None
    well_plate_identifier: str | None = None
    exposure_duration_setting: float | None = None
    illumination_setting: float | None = None
    processed_data: ProcessedData | None = None
    wavelength: float | None = None
    absorbance: JsonFloat | None = None
    calculated_data: list[CalculatedDataItem] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float
    analytical_method_identifier: str | None = None
    _measurement_time: str | None = None
    _analyst: str | None = None

    @property
    def measurement_time(self) -> str:
        if self._measurement_time is not None:
            return self._measurement_time
        if (
            self.measurements
            and len({m.measurement_time for m in self.measurements}) == 1
            and self.measurements[0].measurement_time
        ):
            return self.measurements[0].measurement_time
        msg = "Missing valid measurement group time"
        raise AllotropeConversionError(msg)

    @property
    def analyst(self) -> str | None:
        if self._analyst is not None:
            return self._analyst
        if self.measurements and len({m.analyst for m in self.measurements}) == 1:
            return self.measurements[0].analyst
        return None


@dataclass(frozen=True)
class Metadata:
    device_identifier: str
    device_type: str
    model_number: str
    software_name: str
    detection_type: str | None = None
    unc_path: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]

    def get_calculated_data_items(self) -> list[CalculatedDataItem]:
        return [
            calculated_data_item
            for measurement_group in self.measurement_groups
            for measurement in measurement_group.measurements
            for calculated_data_item in (measurement.calculated_data or [])
        ]


class Mapper:
    MANIFEST = "http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest"

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

    def map_model(self, data: Data, file_name: str) -> Model:
        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    product_manufacturer=data.metadata.product_manufacturer,
                ),
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                plate_reader_document=[
                    PlateReaderDocumentItem(
                        analyst=measurement_group.analyst,
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            analytical_method_identifier=measurement_group.analytical_method_identifier,
                            container_type=ContainerType.well_plate,
                            plate_well_count=TQuantityValueNumber(
                                value=measurement_group.plate_well_count
                            ),
                            measurement_time=self.get_date_time(
                                measurement_group.measurement_time
                            ),
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
    ) -> OpticalImagingMeasurementDocumentItems | UltravioletAbsorbancePointDetectionMeasurementDocumentItems:
        if measurement.type_ == MeasurementType.OPTICAL_IMAGING:
            return self._get_optical_imaging_measurement_document(measurement, metadata)
        elif measurement.type_ == MeasurementType.ULTRAVIOLET_ABSORBANCE:
            return self._get_ultraviolet_absorbance_measurement_document(
                measurement, metadata
            )
        msg = f"Invalid measurement type: {measurement.type}"
        raise AllotropeConversionError(msg)

    def _get_optical_imaging_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> OpticalImagingMeasurementDocumentItems:
        return OpticalImagingMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                location_identifier=measurement.location_identifier,
                well_plate_identifier=measurement.well_plate_identifier,
            ),
            device_control_aggregate_document=OpticalImagingDeviceControlAggregateDocument(
                device_control_document=[
                    OpticalImagingDeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detection_type=metadata.detection_type,
                        exposure_duration_setting=quantity_or_none(
                            TQuantityValueMilliSecond,
                            measurement.exposure_duration_setting,
                        ),
                        illumination_setting=quantity_or_none(
                            TQuantityValueUnitless, measurement.illumination_setting
                        ),
                    )
                ]
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(
                        processed_data_identifier=measurement.processed_data.identifier,
                        image_feature_aggregate_document=ImageFeatureAggregateDocument(
                            image_feature_document=[
                                ImageFeatureDocumentItem(
                                    image_feature_identifier=image_feature.identifier,
                                    image_feature_name=image_feature.feature,
                                    image_feature_result=TQuantityValueUnitless(
                                        value=image_feature.result
                                    ),
                                )
                                for image_feature in measurement.processed_data.features
                            ]
                        ),
                    )
                ]
            )
            if measurement.processed_data
            else None,
        )

    def _get_ultraviolet_absorbance_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> UltravioletAbsorbancePointDetectionMeasurementDocumentItems:
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detector_wavelength_setting=assert_not_none(
                            quantity_or_none(
                                TQuantityValueNanometer, measurement.wavelength
                            ),
                            msg="Missing wavelength setting value in ultraviolet absorbance measurement",
                        ),
                    )
                ]
            ),
            absorbance=assert_not_none(
                quantity_or_none(
                    TQuantityValueMilliAbsorbanceUnit, measurement.absorbance
                ),
                msg="Missing absorbance value in ultraviolet absorbance measurement",
            ),
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                location_identifier=measurement.location_identifier,
                well_plate_identifier=measurement.well_plate_identifier,
            ),
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
                            for item in calculated_data_item.data_source_document
                        ]
                    ),
                )
                for calculated_data_item in calculated_data_document
            ]
        )
