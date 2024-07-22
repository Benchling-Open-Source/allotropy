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
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    ImageFeatureAggregateDocument,
    ImageFeatureDocumentItem,
    LuminescencePointDetectionDeviceControlAggregateDocument,
    LuminescencePointDetectionDeviceControlDocumentItem,
    LuminescencePointDetectionMeasurementDocumentItems,
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
    ScanPositionSettingPlateReader,
    TransmittedLightSetting,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimeter,
    TQuantityValueMilliSecond,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueRelativeLightUnit,
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


class MeasurementType(Enum):
    OPTICAL_IMAGING = "OPTICAL_IMAGING"
    ULTRAVIOLET_ABSORBANCE = "ULTRAVIOLET_ABSORBANCE"
    FLUORESCENCE = "FLUORESCENCE"
    LUMINESCENCE = "LUMINESCENCE"


MeasurementDocumentItems = (
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    | FluorescencePointDetectionMeasurementDocumentItems
    | LuminescencePointDetectionMeasurementDocumentItems
    | OpticalImagingMeasurementDocumentItems
)


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
    type_: MeasurementType
    identifier: str
    sample_identifier: str
    location_identifier: str
    analyst: str | None = None
    measurement_time: str | None = None
    well_plate_identifier: str | None = None

    # Measurements
    absorbance: JsonFloat | None = None
    fluorescence: JsonFloat | None = None
    luminescence: JsonFloat | None = None

    # Processed data
    calculated_data: list[CalculatedDataItem] | None = None
    processed_data: ProcessedData | None = None

    # Settings
    detector_wavelength_setting: JsonFloat | None = None
    detector_bandwidth_setting: JsonFloat | None = None
    excitation_wavelength_setting: JsonFloat | None = None
    excitation_bandwidth_setting: JsonFloat | None = None
    wavelength_filter_cutoff_setting: float | None = None
    detector_distance_setting: float | None = None
    scan_position_setting: ScanPositionSettingPlateReader | None = None
    detector_gain_setting: str | None = None
    detector_carriage_speed: str | None = None
    compartment_temperature: float | None = None
    number_of_averages: float | None = None

    # Optical imaging
    exposure_duration_setting: float | None = None
    illumination_setting: float | None = None
    magnification_setting: float | None = None
    transmitted_light_setting: TransmittedLightSetting | None = None
    auto_focus_setting: bool | None = None
    image_count_setting: float | None = None
    fluorescent_tag_setting: str | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float
    analytical_method_identifier: str | None = None
    experimental_data_identifier: str | None = None
    _measurement_time: str | None = None
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
    software_name: str
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
    MANIFEST = "http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest"

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

    def map_model(self, data: Data) -> Model:
        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    product_manufacturer=data.metadata.product_manufacturer,
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=data.metadata.data_system_instance_id,
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                plate_reader_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data
                ),
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> PlateReaderDocumentItem:
        return PlateReaderDocumentItem(
            analyst=metadata.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                analytical_method_identifier=measurement_group.analytical_method_identifier,
                experimental_data_identifier=measurement_group.experimental_data_identifier,
                container_type=ContainerType.well_plate,
                plate_well_count=TQuantityValueNumber(
                    value=measurement_group.plate_well_count
                ),
                measurement_time=self.get_date_time(
                    assert_not_none(
                        measurement_group.measurement_time or metadata.measurement_time,
                        msg="Failed to parse valid timestamp",
                    )
                ),
                measurement_document=[
                    self._get_measurement_document(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
                processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                    measurement_group.processed_data
                ),
            ),
        )

    def _get_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocumentItems:
        # TODO(switch-statement): use switch statement once Benchling can use 3.10 syntax
        if measurement.type_ == MeasurementType.OPTICAL_IMAGING:
            return self._get_optical_imaging_measurement_document(measurement, metadata)
        elif measurement.type_ == MeasurementType.ULTRAVIOLET_ABSORBANCE:
            return self._get_ultraviolet_absorbance_measurement_document(
                measurement, metadata
            )
        elif measurement.type_ == MeasurementType.LUMINESCENCE:
            return self._get_luminescence_measurement_document(measurement, metadata)
        elif measurement.type_ == MeasurementType.FLUORESCENCE:
            return self._get_fluorescence_measurement_document(measurement, metadata)
        else:
            msg = f"Invalid measurement type: {measurement.type}"
            raise AllotropeConversionError(msg)

    def _get_optical_imaging_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> OpticalImagingMeasurementDocumentItems:
        return OpticalImagingMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=OpticalImagingDeviceControlAggregateDocument(
                device_control_document=[
                    OpticalImagingDeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detection_type=metadata.detection_type,
                        detector_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.detector_wavelength_setting,
                        ),
                        exposure_duration_setting=quantity_or_none(
                            TQuantityValueMilliSecond,
                            measurement.exposure_duration_setting,
                        ),
                        illumination_setting=quantity_or_none(
                            TQuantityValueUnitless, measurement.illumination_setting
                        ),
                        detector_gain_setting=measurement.detector_gain_setting,
                        magnification_setting=quantity_or_none(
                            TQuantityValueUnitless,
                            measurement.magnification_setting,
                        ),
                        transmitted_light_setting=measurement.transmitted_light_setting,
                        auto_focus_setting=measurement.auto_focus_setting,
                        fluorescent_tag_setting=measurement.fluorescent_tag_setting,
                        image_count_setting=quantity_or_none(
                            TQuantityValueUnitless,
                            measurement.image_count_setting,
                        ),
                        excitation_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.excitation_wavelength_setting,
                        ),
                    )
                ]
            ),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
        )

    def _get_ultraviolet_absorbance_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> UltravioletAbsorbancePointDetectionMeasurementDocumentItems:
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detection_type=metadata.detection_type,
                        detector_wavelength_setting=TQuantityValueNanometer(
                            value=assert_not_none(  # type: ignore[arg-type]
                                measurement.detector_wavelength_setting,
                                msg="Missing wavelength setting value in ultraviolet absorbance measurement",
                            )
                        ),
                        number_of_averages=quantity_or_none(
                            TQuantityValueNumber, measurement.number_of_averages
                        ),
                        detector_carriage_speed_setting=measurement.detector_carriage_speed,
                    )
                ]
            ),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=assert_not_none(  # type: ignore[arg-type]
                    value=measurement.absorbance,
                    msg="Missing absorbance value in ultraviolet absorbance measurement",
                )
            ),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius, measurement.compartment_temperature
            ),
        )

    def _get_luminescence_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> LuminescencePointDetectionMeasurementDocumentItems:
        return LuminescencePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    LuminescencePointDetectionDeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detection_type=metadata.detection_type,
                        detector_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.detector_wavelength_setting,
                        ),
                        detector_bandwidth_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.detector_bandwidth_setting,
                        ),
                        detector_distance_setting__plate_reader_=quantity_or_none(
                            TQuantityValueMillimeter,
                            measurement.detector_distance_setting,
                        ),
                        scan_position_setting__plate_reader_=measurement.scan_position_setting,
                        detector_gain_setting=measurement.detector_gain_setting,
                        detector_carriage_speed_setting=measurement.detector_carriage_speed,
                    )
                ]
            ),
            luminescence=TQuantityValueRelativeLightUnit(
                value=assert_not_none(  # type: ignore[arg-type]
                    measurement.luminescence,
                    msg="Missing luminescence value in luminescence measurement",
                )
            ),
        )

    def _get_fluorescence_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> FluorescencePointDetectionMeasurementDocumentItems:
        return FluorescencePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    FluorescencePointDetectionDeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detection_type=metadata.detection_type,
                        detector_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.detector_wavelength_setting,
                        ),
                        detector_bandwidth_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.detector_bandwidth_setting,
                        ),
                        excitation_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.excitation_wavelength_setting,
                        ),
                        excitation_bandwidth_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.excitation_bandwidth_setting,
                        ),
                        wavelength_filter_cutoff_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.wavelength_filter_cutoff_setting,
                        ),
                        detector_distance_setting__plate_reader_=quantity_or_none(
                            TQuantityValueMillimeter,
                            measurement.detector_distance_setting,
                        ),
                        scan_position_setting__plate_reader_=measurement.scan_position_setting,
                        detector_gain_setting=measurement.detector_gain_setting,
                        number_of_averages=quantity_or_none(
                            TQuantityValueNumber, measurement.number_of_averages
                        ),
                        detector_carriage_speed_setting=measurement.detector_carriage_speed,
                    )
                ]
            ),
            fluorescence=TQuantityValueRelativeFluorescenceUnit(
                value=assert_not_none(  # type: ignore[arg-type]
                    measurement.fluorescence,
                    msg="Missing fluorescence value in fluorescence measurement",
                )
            ),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius, measurement.compartment_temperature
            ),
            sample_document=self._get_sample_document(measurement),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            location_identifier=measurement.location_identifier,
            well_plate_identifier=measurement.well_plate_identifier,
        )

    def _get_processed_data_aggregate_document(
        self, data: ProcessedData | None
    ) -> ProcessedDataAggregateDocument | None:
        if not data:
            return None

        # NOTE: this / ProcessedData operating only on "image features" is almost certainly not comprehensive,
        # and should be expanded as needed.
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    processed_data_identifier=data.identifier,
                    image_feature_aggregate_document=ImageFeatureAggregateDocument(
                        image_feature_document=[
                            ImageFeatureDocumentItem(
                                image_feature_identifier=image_feature.identifier,
                                image_feature_name=image_feature.feature,
                                image_feature_result=TQuantityValueUnitless(
                                    value=image_feature.result
                                ),
                            )
                            for image_feature in data.features
                        ]
                    ),
                )
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
