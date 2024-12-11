from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    ContainerType,
    CustomInformationAggregateDocument,
    CustomInformationDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    ImageDocumentItem,
    ImageFeatureAggregateDocument,
    ImageFeatureDocumentItem,
    LuminescencePointDetectionDeviceControlAggregateDocument,
    LuminescencePointDetectionDeviceControlDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    OpticalImagingAggregateDocument,
    OpticalImagingDeviceControlAggregateDocument,
    OpticalImagingDeviceControlDocumentItem,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    ScanPositionSettingPlateReader,
    TransmittedLightSetting,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
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
    TDatacube,
    TQuantityValue,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, get_data_cube
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.utils.values import (
    assert_not_none,
    quantity_or_none,
    quantity_or_none_from_unit,
)


class MeasurementType(Enum):
    OPTICAL_IMAGING = "OPTICAL_IMAGING"
    ULTRAVIOLET_ABSORBANCE = "ULTRAVIOLET_ABSORBANCE"
    FLUORESCENCE = "FLUORESCENCE"
    LUMINESCENCE = "LUMINESCENCE"


@dataclass(frozen=True)
class DataSource:
    identifier: str
    feature: str


@dataclass(frozen=True)
class ImageFeature:
    identifier: str
    feature: str
    result: float | InvalidJsonFloat
    data_sources: list[DataSource] | None = None


@dataclass(frozen=True)
class ProcessedData:
    features: list[ImageFeature]
    identifier: str | None = None
    data_processing_document: dict[str, Any] | None = None


@dataclass(frozen=True)
class CalculatedDataItem:
    identifier: str
    name: str
    value: JsonFloat
    unit: str
    data_sources: list[DataSource]
    description: str | None = None


@dataclass(frozen=True)
class ImageSource:
    identifier: str


@dataclass(frozen=True)
class Measurement:
    # Measurement metadata
    type_: MeasurementType
    device_type: str
    identifier: str
    sample_identifier: str
    location_identifier: str

    # Optional metadata
    batch_identifier: str | None = None
    well_plate_identifier: str | None = None
    detection_type: str | None = None
    sample_role_type: SampleRoleType | None = None
    firmware_version: str | None = None

    # Measurements
    absorbance: JsonFloat | None = None
    fluorescence: JsonFloat | None = None
    luminescence: JsonFloat | None = None

    # Processed data
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
    electronic_absorbance_reference_wavelength_setting: float | None = None
    electronic_absorbance_reference_absorbance: float | None = None

    # Optical imaging
    exposure_duration_setting: float | None = None
    illumination_setting: float | None = None
    illumination_setting_unit: str | None = None
    magnification_setting: float | None = None
    transmitted_light_setting: TransmittedLightSetting | None = None
    auto_focus_setting: bool | None = None
    image_count_setting: float | None = None
    fluorescent_tag_setting: str | None = None

    # Custom information
    led_filter: str | None = None
    path_length: float | None = None
    device_control_custom_info: dict[str, Any] | None = None

    custom_data_cubes: list[DataCube] | None = None
    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float
    measurement_time: str
    analyst: str | None = None
    analytical_method_identifier: str | None = None
    experimental_data_identifier: str | None = None
    experiment_type: str | None = None

    # Processed data
    processed_data: ProcessedData | None = None
    images: list[ImageSource] | None = None

    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Metadata:
    device_identifier: str
    model_number: str
    software_name: str | None = None
    unc_path: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None

    file_name: str | None = None
    data_system_instance_id: str | None = None

    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDataItem] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            plate_reader_aggregate_document=add_custom_information_document(
                PlateReaderAggregateDocument(
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
                        self._get_technique_document(measurement_group)
                        for measurement_group in data.measurement_groups
                    ],
                    calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                        data.calculated_data
                    ),
                ),
                data.metadata.custom_info,
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup
    ) -> PlateReaderDocumentItem:
        return PlateReaderDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=add_custom_information_document(
                MeasurementAggregateDocument(
                    analytical_method_identifier=measurement_group.analytical_method_identifier,
                    experimental_data_identifier=measurement_group.experimental_data_identifier,
                    experiment_type=measurement_group.experiment_type,
                    container_type=ContainerType.well_plate,
                    plate_well_count=TQuantityValueNumber(
                        value=measurement_group.plate_well_count
                    ),
                    measurement_time=self.get_date_time(
                        measurement_group.measurement_time
                    ),
                    measurement_document=[
                        self._get_measurement_document(measurement)
                        for measurement in measurement_group.measurements
                    ],
                    processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                        measurement_group.processed_data
                    ),
                    image_aggregate_document=self._get_image_source_aggregate_document(
                        measurement_group.images
                    ),
                ),
                measurement_group.custom_info,
            ),
        )

    def _get_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        # TODO(switch-statement): use switch statement once Benchling can use 3.10 syntax
        doc: MeasurementDocument
        if measurement.type_ == MeasurementType.OPTICAL_IMAGING:
            doc = self._get_optical_imaging_measurement_document(measurement)
        elif measurement.type_ == MeasurementType.ULTRAVIOLET_ABSORBANCE:
            doc = self._get_ultraviolet_absorbance_measurement_document(measurement)
        elif measurement.type_ == MeasurementType.LUMINESCENCE:
            doc = self._get_luminescence_measurement_document(measurement)
        elif measurement.type_ == MeasurementType.FLUORESCENCE:
            doc = self._get_fluorescence_measurement_document(measurement)
        else:
            msg = f"Unexpected measurement type: {measurement.type}"
            raise AllotropyParserError(msg)
        return add_custom_information_document(doc, measurement.custom_info)

    def _get_optical_imaging_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        device_control_document = OpticalImagingDeviceControlDocumentItem(
            device_type=measurement.device_type,
            firmware_version=measurement.firmware_version,
            detection_type=measurement.detection_type,
            detector_wavelength_setting=quantity_or_none(
                TQuantityValueNanometer,
                measurement.detector_wavelength_setting,
            ),
            exposure_duration_setting=quantity_or_none(
                TQuantityValueMilliSecond,
                measurement.exposure_duration_setting,
            ),
            # TODO(nstender): figure out how to limit possible classes from get_quantity_class for typing.
            illumination_setting=quantity_or_none_from_unit(  # type: ignore[arg-type]
                measurement.illumination_setting_unit,
                measurement.illumination_setting,
            ),
            detector_distance_setting__plate_reader_=quantity_or_none(
                TQuantityValueMillimeter,
                measurement.detector_distance_setting,
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
        # TODO(ASM gaps): we think this should be added to ASM
        custom_info = {
            "LED filter": measurement.led_filter,
        }

        return MeasurementDocument(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=OpticalImagingDeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        device_control_document,
                        (measurement.device_control_custom_info or {}) | custom_info,
                    )
                ]
            ),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
            custom_information_aggregate_document=CustomInformationAggregateDocument(
                custom_information_document=[
                    CustomInformationDocumentItem(
                        datum_label=data_cube.label,
                        data_cube=assert_not_none(
                            get_data_cube(data_cube, TDatacube),
                            f"Unable to create data cube with label: {data_cube.label}",
                        ),
                    )
                    for data_cube in measurement.custom_data_cubes
                    if data_cube
                ]
            )
            if measurement.custom_data_cubes
            else None,
        )

    def _get_ultraviolet_absorbance_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        device_control_document = (
            UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                device_type=measurement.device_type,
                firmware_version=measurement.firmware_version,
                detection_type=measurement.detection_type,
                detector_wavelength_setting=quantity_or_none(
                    TQuantityValueNanometer,
                    measurement.detector_wavelength_setting,
                ),
                number_of_averages=quantity_or_none(
                    TQuantityValueNumber, measurement.number_of_averages
                ),
                detector_carriage_speed_setting=measurement.detector_carriage_speed,
                detector_gain_setting=measurement.detector_gain_setting,
                detector_distance_setting__plate_reader_=quantity_or_none(
                    TQuantityValueMillimeter,
                    measurement.detector_distance_setting,
                ),
                electronic_absorbance_reference_wavelength_setting=quantity_or_none(
                    TQuantityValueNanometer,
                    measurement.electronic_absorbance_reference_wavelength_setting,
                ),
            )
        )
        # TODO(ASM gaps): we think this should be added to ASM
        measurement_custom_info = {
            "electronic absorbance reference absorbance": measurement.electronic_absorbance_reference_absorbance
        }
        measurement_doc = MeasurementDocument(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        device_control_document,
                        measurement.device_control_custom_info or {},
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
        return add_custom_information_document(measurement_doc, measurement_custom_info)

    def _get_luminescence_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        device_control_document = LuminescencePointDetectionDeviceControlDocumentItem(
            device_type=measurement.device_type,
            firmware_version=measurement.firmware_version,
            detection_type=measurement.detection_type,
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

        return MeasurementDocument(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        device_control_document,
                        measurement.device_control_custom_info or {},
                    )
                ]
            ),
            luminescence=TQuantityValueRelativeLightUnit(
                value=assert_not_none(  # type: ignore[arg-type]
                    measurement.luminescence,
                    msg="Missing luminescence value in luminescence measurement",
                )
            ),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius, measurement.compartment_temperature
            ),
        )

    def _get_fluorescence_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        device_control_document = FluorescencePointDetectionDeviceControlDocumentItem(
            device_type=measurement.device_type,
            firmware_version=measurement.firmware_version,
            detection_type=measurement.detection_type,
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

        return MeasurementDocument(
            measurement_identifier=measurement.identifier,
            device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        device_control_document,
                        measurement.device_control_custom_info or {},
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
        # TODO(ASM gaps): we think this should be added to ASM
        custom_info = {
            "path length": measurement.path_length,
        }
        sample_doc = SampleDocument(
            sample_identifier=measurement.sample_identifier,
            location_identifier=measurement.location_identifier,
            well_plate_identifier=measurement.well_plate_identifier,
            batch_identifier=measurement.batch_identifier,
            sample_role_type=measurement.sample_role_type.value
            if measurement.sample_role_type
            else None,
        )
        return add_custom_information_document(sample_doc, custom_info)

    def _get_processed_data_aggregate_document(
        self, data: ProcessedData | None
    ) -> ProcessedDataAggregateDocument | None:
        if not (data and data.features):
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
                                data_source_aggregate_document=self._get_data_source_aggregate_document(
                                    image_feature.data_sources
                                ),
                            )
                            for image_feature in data.features
                        ]
                    ),
                    data_processing_document={
                        key: value
                        for key, value in data.data_processing_document.items()
                        if value is not None
                    }
                    if data.data_processing_document
                    else None,
                )
            ]
        )

    def _get_image_source_aggregate_document(
        self, images: list[ImageSource] | None
    ) -> OpticalImagingAggregateDocument | None:
        if not images:
            return None

        return OpticalImagingAggregateDocument(
            image_document=[
                ImageDocumentItem(experimental_data_identifier=image.identifier)
                for image in images
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
                    calculation_description=calculated_data_item.description,
                    calculated_result=TQuantityValue(
                        value=calculated_data_item.value,
                        unit=calculated_data_item.unit,
                    ),
                    data_source_aggregate_document=self._get_data_source_aggregate_document(
                        calculated_data_item.data_sources
                    ),
                )
                for calculated_data_item in calculated_data_items
            ]
        )

    def _get_data_source_aggregate_document(
        self, data_sources: list[DataSource] | None
    ) -> DataSourceAggregateDocument | None:
        if not data_sources:
            return None

        return DataSourceAggregateDocument(
            data_source_document=[
                DataSourceDocumentItem(
                    data_source_identifier=item.identifier,
                    data_source_feature=item.feature,
                )
                for item in data_sources
            ]
        )
