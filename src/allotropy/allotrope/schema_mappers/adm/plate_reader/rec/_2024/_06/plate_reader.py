from dataclasses import dataclass
from enum import Enum
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    TQuantityValueModel,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimeter,
    TQuantityValueNanogramPerMicroliter,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValuePicogramPerMilliliter,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueRelativeLightUnit,
    TQuantityValueSecondTime,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDatacube
from allotropy.allotrope.models.shared.definitions.units import Unitless
from allotropy.allotrope.schema_mappers.data_cube import DataCube, get_data_cube
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import (
    assert_not_none,
    quantity_or_none,
)


# TODO: these two enum classes should come from the schema
class ScanPositionSettingPlateReader(Enum):
    bottom_scan_position__plate_reader_ = "bottom scan position (plate reader)"
    scan_position_configuration__plate_reader_ = (
        "scan position configuration (plate reader)"
    )
    top_scan_position__plate_reader_ = "top scan position (plate reader)"


class ContainerType(Enum):
    reactor = "reactor"
    controlled_lab_reactor = "controlled lab reactor"
    tube = "tube"
    well_plate = "well plate"
    differential_scanning_calorimetry_pan = "differential scanning calorimetry pan"
    qPCR_reaction_block = "qPCR reaction block"  # noqa: N815
    vial_rack = "vial rack"
    pan = "pan"
    reservoir = "reservoir"
    array_card_block = "array card block"
    capillary = "capillary"
    disintegration_apparatus_basket = "disintegration apparatus basket"
    jar = "jar"
    container = "container"
    tray = "tray"
    basket = "basket"
    cell_holder = "cell holder"


class MeasurementType(Enum):
    ULTRAVIOLET_ABSORBANCE = "ULTRAVIOLET_ABSORBANCE"
    FLUORESCENCE = "FLUORESCENCE"
    LUMINESCENCE = "LUMINESCENCE"
    ULTRAVIOLET_ABSORBANCE_CUBE_DETECTOR = "ULTRAVIOLET_ABSORBANCE_CUBE_DETECTOR"
    FLUORESCENCE_CUBE_DETECTOR = "FLUORESCENCE_CUBE_DETECTOR"
    LUMINESCENCE_CUBE_DETECTOR = "LUMINESCENCE_CUBE_DETECTOR"


@dataclass(frozen=True)
class ErrorDocument:
    error: str
    error_feature: str


@dataclass(frozen=True)
class ProcessedDataDocument:
    identifier: str | None = None
    concentration_factor: float | None = None


@dataclass(frozen=True)
class Measurement:
    # Measurement metadata
    type_: MeasurementType
    device_type: str
    identifier: str
    sample_identifier: str
    location_identifier: str
    firmware_version: str | None = None
    batch_identifier: str | None = None

    # Optional metadata
    well_plate_identifier: str | None = None
    well_location_identifier: str | None = None
    detection_type: str | None = None
    sample_role_type: SampleRoleType | None = None
    mass_concentration: float | None = None

    # Measurements
    absorbance: float | None = None
    fluorescence: float | None = None
    luminescence: float | None = None

    # Settings
    detector_wavelength_setting: float | None = None
    detector_bandwidth_setting: float | None = None
    excitation_wavelength_setting: float | None = None
    excitation_bandwidth_setting: float | None = None
    wavelength_filter_cutoff_setting: float | None = None
    detector_distance_setting: float | None = None
    scan_position_setting: ScanPositionSettingPlateReader | None = None
    detector_gain_setting: str | None = None
    detector_carriage_speed: str | None = None
    compartment_temperature: float | None = None
    number_of_averages: float | None = None
    measurement_custom_info: dict[str, Any] | None = None
    sample_custom_info: dict[str, Any] | None = None
    device_control_custom_info: dict[str, Any] | None = None
    electronic_absorbance_reference_wavelength_setting: float | None = None
    wavelength_identifier: str | None = None

    # Kinetic settings
    total_measurement_time_setting: float | None = None
    read_interval_setting: float | None = None
    number_of_scans_setting: float | None = None

    # Kinetic measurements
    profile_data_cube: DataCube | None = None

    # error documents
    error_document: list[ErrorDocument] | None = None

    # processing data
    processed_data_document: ProcessedDataDocument | None = None

    calc_docs_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float
    measurement_time: str
    analyst: str | None = None
    analytical_method_identifier: str | None = None
    experimental_data_identifier: str | None = None
    experiment_type: str | None = None
    maximum_wavelength_signal: float | None = None
    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Metadata:
    asm_file_identifier: str
    device_identifier: str
    model_number: str
    data_system_instance_id: str
    software_name: str | None = None
    unc_path: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None
    file_name: str | None = None
    custom_info_doc: dict[str, Any] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDocument] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/plate-reader/REC/2024/06/plate-reader.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    product_manufacturer=data.metadata.product_manufacturer,
                ),
                data_system_document=add_custom_information_document(
                    DataSystemDocument(
                        ASM_file_identifier=data.metadata.asm_file_identifier,
                        data_system_instance_identifier=data.metadata.data_system_instance_id,
                        file_name=data.metadata.file_name,
                        UNC_path=data.metadata.unc_path,
                        software_name=data.metadata.software_name,
                        software_version=data.metadata.software_version,
                        ASM_converter_name=self.converter_name,
                        ASM_converter_version=ASM_CONVERTER_VERSION,
                    ),
                    data.metadata.custom_info_doc,
                ),
                plate_reader_document=[
                    self._get_technique_document(measurement_group)
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data.calculated_data
                ),
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup
    ) -> PlateReaderDocumentItem:
        plate_reader_doc = PlateReaderDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                analytical_method_identifier=measurement_group.analytical_method_identifier,
                experimental_data_identifier=measurement_group.experimental_data_identifier,
                experiment_type=measurement_group.experiment_type,
                container_type=ContainerType.well_plate.value,
                plate_well_count=TQuantityValueNumber(
                    value=measurement_group.plate_well_count
                ),
                measurement_time=self.get_date_time(measurement_group.measurement_time),
                measurement_document=[
                    self._get_measurement_document(measurement)
                    for measurement in measurement_group.measurements
                ],
            ),
        )
        custom_info_doc = {
            "maximum wavelength signal": quantity_or_none(
                TQuantityValueNanometer, measurement_group.maximum_wavelength_signal
            )
        }
        custom_info_doc.update(measurement_group.custom_info or {})
        return add_custom_information_document(plate_reader_doc, custom_info_doc)

    def _get_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        # TODO(switch-statement): use switch statement once Benchling can use 3.10 syntax
        if measurement.type_ == MeasurementType.ULTRAVIOLET_ABSORBANCE:
            return self._get_ultraviolet_absorbance_measurement_document(measurement)
        elif measurement.type_ == MeasurementType.LUMINESCENCE:
            return self._get_luminescence_measurement_document(measurement)
        elif measurement.type_ == MeasurementType.FLUORESCENCE:
            return self._get_fluorescence_measurement_document(measurement)
        elif measurement.type_ in [
            MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_DETECTOR,
            MeasurementType.LUMINESCENCE_CUBE_DETECTOR,
            MeasurementType.FLUORESCENCE_CUBE_DETECTOR,
        ]:
            return self._get_profile_data_cube_measurement_document(measurement)
        else:
            msg = f"Unexpected measurement type: {measurement.type_}"
            raise AllotropyParserError(msg)

    def _get_ultraviolet_absorbance_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        device_control_document = DeviceControlDocumentItem(
            electronic_absorbance_reference_wavelength_setting=quantity_or_none(
                TQuantityValueNanometer,
                measurement.electronic_absorbance_reference_wavelength_setting,
            ),
            device_type=measurement.device_type,
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
            firmware_version=measurement.firmware_version,
        )
        measurement_doc = MeasurementDocument(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        device_control_document, measurement.device_control_custom_info
                    )
                ]
            ),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=assert_not_none(
                    value=measurement.absorbance,
                    msg="Missing absorbance value in ultraviolet absorbance measurement",
                )
            ),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius, measurement.compartment_temperature
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.error_document
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(
                        processed_data_identifier=measurement.processed_data_document.identifier,
                        data_processing_document={
                            "concentration factor": quantity_or_none(
                                TQuantityValueNanogramPerMicroliter,
                                measurement.processed_data_document.concentration_factor,
                            )
                        },
                    )
                ]
            )
            if measurement.processed_data_document
            else None,
        )
        return add_custom_information_document(
            measurement_doc, measurement.measurement_custom_info
        )

    def _get_luminescence_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        device_control_document = DeviceControlDocumentItem(
            device_type=measurement.device_type,
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
            scan_position_setting__plate_reader_=(
                measurement.scan_position_setting.value
                if measurement.scan_position_setting
                else None
            ),
            number_of_averages=quantity_or_none(
                TQuantityValueNumber, measurement.number_of_averages
            ),
            detector_gain_setting=measurement.detector_gain_setting,
            detector_carriage_speed_setting=measurement.detector_carriage_speed,
        )
        doc = MeasurementDocument(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        device_control_document,
                        measurement.device_control_custom_info,
                    ),
                ]
            ),
            luminescence=TQuantityValueRelativeLightUnit(
                value=assert_not_none(
                    measurement.luminescence,
                    msg="Missing luminescence value in luminescence measurement",
                )
            ),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius, measurement.compartment_temperature
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.error_document
            ),
        )
        return add_custom_information_document(doc, measurement.measurement_custom_info)

    def _get_fluorescence_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        device_control_document = DeviceControlDocumentItem(
            device_type=measurement.device_type,
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
            scan_position_setting__plate_reader_=(
                measurement.scan_position_setting.value
                if measurement.scan_position_setting
                else None
            ),
            detector_gain_setting=measurement.detector_gain_setting,
            number_of_averages=quantity_or_none(
                TQuantityValueNumber, measurement.number_of_averages
            ),
            detector_carriage_speed_setting=measurement.detector_carriage_speed,
        )
        measurement_doc = MeasurementDocument(
            measurement_identifier=measurement.identifier,
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        device_control_document, measurement.device_control_custom_info
                    )
                ]
            ),
            fluorescence=TQuantityValueRelativeFluorescenceUnit(
                value=assert_not_none(
                    measurement.fluorescence,
                    msg="Missing fluorescence value in fluorescence measurement",
                )
            ),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius, measurement.compartment_temperature
            ),
            sample_document=self._get_sample_document(measurement),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.error_document
            ),
        )
        return add_custom_information_document(
            measurement_doc, measurement.measurement_custom_info
        )

    def _get_profile_data_cube_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        if not measurement.profile_data_cube:
            msg = "Profile data cube is required for cube detector measurements"
            raise AllotropyParserError(msg)

        profile_data_cube = get_data_cube(measurement.profile_data_cube, TDatacube)

        return MeasurementDocument(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=measurement.device_type,
                        detection_type=measurement.detection_type,
                        detector_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.detector_wavelength_setting,
                        ),
                        excitation_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.excitation_wavelength_setting,
                        ),
                        wavelength_filter_cutoff_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            measurement.wavelength_filter_cutoff_setting,
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
                        total_measurement_time_setting=quantity_or_none(
                            TQuantityValueSecondTime,
                            measurement.total_measurement_time_setting,
                        ),
                        read_interval_setting=quantity_or_none(
                            TQuantityValueSecondTime,
                            measurement.read_interval_setting,
                        ),
                        number_of_scans_setting=quantity_or_none(
                            TQuantityValueNumber,
                            measurement.number_of_scans_setting,
                        ),
                    )
                ]
            ),
            compartment_temperature=quantity_or_none(
                TQuantityValueDegreeCelsius, measurement.compartment_temperature
            ),
            absorption_profile_data_cube=(
                profile_data_cube
                if measurement.type_
                == MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_DETECTOR
                else None
            ),
            luminescence_profile_data_cube=(
                profile_data_cube
                if measurement.type_ == MeasurementType.LUMINESCENCE_CUBE_DETECTOR
                else None
            ),
            fluorescence_emission_profile_data_cube=(
                profile_data_cube
                if measurement.type_ == MeasurementType.FLUORESCENCE_CUBE_DETECTOR
                else None
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        sample_doc = SampleDocument(
            sample_identifier=measurement.sample_identifier,
            location_identifier=measurement.location_identifier,
            well_plate_identifier=measurement.well_plate_identifier,
            well_location_identifier=measurement.well_location_identifier,
            sample_role_type=(
                measurement.sample_role_type.value
                if measurement.sample_role_type
                else None
            ),
            mass_concentration=quantity_or_none(
                TQuantityValuePicogramPerMilliliter,
                measurement.mass_concentration,
            ),
            batch_identifier=measurement.batch_identifier,
        )
        return add_custom_information_document(
            sample_doc, measurement.sample_custom_info
        )

    def _get_calculated_data_aggregate_document(
        self, calculated_data_items: list[CalculatedDocument] | None
    ) -> CalculatedDataAggregateDocument | None:
        if not calculated_data_items:
            return None

        return CalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calculated_data_item.uuid,
                    calculated_data_name=calculated_data_item.name,
                    calculation_description=calculated_data_item.description,
                    calculated_result=TQuantityValueModel(
                        value=calculated_data_item.value,
                        unit=calculated_data_item.unit or Unitless.unit,
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

    def _get_error_aggregate_document(
        self, error_documents: list[ErrorDocument] | None
    ) -> ErrorAggregateDocument | None:
        return (
            ErrorAggregateDocument(
                error_document=[
                    ErrorDocumentItem(
                        error=error.error,
                        error_feature=error.error_feature,
                    )
                    for error in error_documents
                ]
            )
            if error_documents
            else None
        )
