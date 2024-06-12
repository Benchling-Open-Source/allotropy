from collections.abc import Sequence
from typing import Any

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
    LuminescencePointDetectionDeviceControlAggregateDocument,
    LuminescencePointDetectionDeviceControlDocumentItem,
    LuminescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    SampleDocument,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimeter,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueRelativeLightUnit,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import PlateData
from allotropy.parsers.agilent_gen5.constants import (
    DEFAULT_SOFTWARE_NAME,
    DEVICE_TYPE,
    MULTIPLATE_FILE_ERROR,
    ReadMode,
)
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser

MeasurementDocumentItems = (
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    | FluorescencePointDetectionMeasurementDocumentItems
    | LuminescencePointDetectionMeasurementDocumentItems
)

MeasurementDocumentAttributeClasses = (
    TQuantityValueDegreeCelsius
    | TQuantityValueMillimeter
    | TQuantityValueNanometer
    | TQuantityValueNumber
)


def get_instance_or_none(
    cls: type[MeasurementDocumentAttributeClasses], value: Any
) -> Any:
    return cls(value=value) if value is not None else None


class AgilentGen5Parser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Agilent Gen5"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def _create_model(self, plate_data: PlateData, file_name: str) -> Model:
        header_data = plate_data.header_data
        results = plate_data.results

        calculated_data_document = [
            CalculatedDataDocumentItem(
                calculated_data_identifier=calculated_datum.identifier,
                data_source_aggregate_document=DataSourceAggregateDocument(
                    data_source_document=[
                        DataSourceDocumentItem(
                            data_source_identifier=data_source.identifier,
                            data_source_feature=data_source.feature.value.lower(),
                        )
                        for data_source in calculated_datum.data_sources
                    ]
                ),
                calculated_data_name=calculated_datum.name,
                calculated_result=TQuantityValueUnitless(value=calculated_datum.result),
            )
            for calculated_datum in results.calculated_data
        ]

        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier="NA",
                    model_number=header_data.model_number,
                    equipment_serial_number=header_data.equipment_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    software_name=DEFAULT_SOFTWARE_NAME,
                    software_version=plate_data.header_data.software_version,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                plate_reader_document=[
                    self._get_plate_reader_document_item(plate_data, well_position)
                    for well_position in results.wells
                ],
                calculated_data_aggregate_document=(
                    CalculatedDataAggregateDocument(
                        calculated_data_document=calculated_data_document
                    )
                    if calculated_data_document
                    else None
                ),
            ),
        )

    def _get_plate_reader_document_item(
        self, plate_data: PlateData, well_position: str
    ) -> PlateReaderDocumentItem:
        header_data = plate_data.header_data
        plate_well_count = len(plate_data.results.wells)
        read_mode = plate_data.read_data.read_mode

        measurement_document: Sequence[MeasurementDocumentItems]

        if read_mode == ReadMode.ABSORBANCE:
            measurement_document = self._get_absorbance_measurement_document(
                plate_data, well_position
            )
        elif read_mode == ReadMode.FLUORESCENCE:
            measurement_document = self._get_fluorescence_measurement_document(
                plate_data, well_position
            )
        elif read_mode == ReadMode.LUMINESCENCE:
            measurement_document = self._get_luminescence_measurement_document(
                plate_data, well_position
            )

        return PlateReaderDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(header_data.datetime),
                analytical_method_identifier=header_data.protocol_file_path,
                experimental_data_identifier=header_data.experiment_file_path,
                plate_well_count=TQuantityValueNumber(value=plate_well_count),
                container_type=ContainerType.well_plate,
                measurement_document=list(measurement_document),
            )
        )

    def _get_sample_document(
        self, plate_data: PlateData, well_position: str
    ) -> SampleDocument:
        well_plate_identifier = plate_data.header_data.well_plate_identifier
        sample_identifier = plate_data.layout_data.sample_identifiers.get(
            well_position, f"{well_plate_identifier} {well_position}"
        )

        return SampleDocument(
            sample_identifier=sample_identifier,
            location_identifier=well_position,
            well_plate_identifier=well_plate_identifier,
        )

    def _get_wavelength_from_label(self, label: str) -> float:
        return float(label.split(":")[-1].split(" ")[0])

    def _get_absorbance_measurement_document(
        self, plate_data: PlateData, well_position: str
    ) -> list[UltravioletAbsorbancePointDetectionMeasurementDocumentItems]:
        read_data = plate_data.read_data

        measurements = plate_data.results.measurements[well_position]
        sample_document = self._get_sample_document(plate_data, well_position)

        return [
            UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                measurement_identifier=measurement.identifier,
                sample_document=sample_document,
                device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                            device_type=DEVICE_TYPE,
                            detection_type=read_data.read_mode.value,
                            detector_wavelength_setting=TQuantityValueNanometer(
                                value=self._get_wavelength_from_label(measurement.label)
                            ),
                            number_of_averages=(
                                TQuantityValueNumber(value=read_data.number_of_averages)
                                if read_data.number_of_averages
                                else None
                            ),
                            detector_carriage_speed_setting=read_data.detector_carriage_speed,
                        )
                    ]
                ),
                absorbance=TQuantityValueMilliAbsorbanceUnit(value=measurement.value),
                compartment_temperature=get_instance_or_none(
                    TQuantityValueDegreeCelsius, plate_data.compartment_temperature
                ),
            )
            for measurement in measurements
        ]

    def _get_fluorescence_measurement_document(
        self, plate_data: PlateData, well_position: str
    ) -> list[FluorescencePointDetectionMeasurementDocumentItems]:
        read_data = plate_data.read_data
        measurements = plate_data.results.measurements[well_position]
        sample_document = self._get_sample_document(plate_data, well_position)

        measurement_document = []

        for measurement in measurements:
            filter_data = read_data.filter_sets[measurement.label]
            document = FluorescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=measurement.identifier,
                sample_document=sample_document,
                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        FluorescencePointDetectionDeviceControlDocumentItem(
                            device_type=DEVICE_TYPE,
                            detection_type=read_data.read_mode.value,
                            detector_wavelength_setting=get_instance_or_none(
                                TQuantityValueNanometer,
                                filter_data.detector_wavelength_setting,
                            ),
                            detector_bandwidth_setting=get_instance_or_none(
                                TQuantityValueNanometer,
                                filter_data.detector_bandwidth_setting,
                            ),
                            excitation_wavelength_setting=get_instance_or_none(
                                TQuantityValueNanometer,
                                filter_data.excitation_wavelength_setting,
                            ),
                            excitation_bandwidth_setting=get_instance_or_none(
                                TQuantityValueNanometer,
                                filter_data.excitation_bandwidth_setting,
                            ),
                            wavelength_filter_cutoff_setting=get_instance_or_none(
                                TQuantityValueNanometer,
                                filter_data.wavelength_filter_cutoff_setting,
                            ),
                            detector_distance_setting__plate_reader_=get_instance_or_none(
                                TQuantityValueMillimeter, read_data.detector_distance
                            ),
                            scan_position_setting__plate_reader_=filter_data.scan_position_setting,
                            detector_gain_setting=filter_data.gain,
                            number_of_averages=get_instance_or_none(
                                TQuantityValueNumber, read_data.number_of_averages
                            ),
                            detector_carriage_speed_setting=read_data.detector_carriage_speed,
                        )
                    ]
                ),
                fluorescence=TQuantityValueRelativeFluorescenceUnit(
                    value=measurement.value
                ),
                compartment_temperature=get_instance_or_none(
                    TQuantityValueDegreeCelsius, plate_data.compartment_temperature
                ),
            )
            measurement_document.append(document)

        return measurement_document

    def _get_luminescence_measurement_document(
        self, plate_data: PlateData, well_position: str
    ) -> list[LuminescencePointDetectionMeasurementDocumentItems]:
        _ = (plate_data, well_position)
        read_data = plate_data.read_data
        measurements = plate_data.results.measurements[well_position]
        sample_document = self._get_sample_document(plate_data, well_position)

        measurement_document = []
        for measurement in measurements:
            filter_data = read_data.filter_sets[measurement.label]
            measurement_document.append(
                LuminescencePointDetectionMeasurementDocumentItems(
                    measurement_identifier=measurement.identifier,
                    sample_document=sample_document,
                    device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                        device_control_document=[
                            LuminescencePointDetectionDeviceControlDocumentItem(
                                device_type=DEVICE_TYPE,
                                detection_type=read_data.read_mode.value,
                                detector_wavelength_setting=get_instance_or_none(
                                    TQuantityValueNanometer,
                                    filter_data.detector_wavelength_setting,
                                ),
                                detector_bandwidth_setting=get_instance_or_none(
                                    TQuantityValueNanometer,
                                    filter_data.detector_bandwidth_setting,
                                ),
                                detector_distance_setting__plate_reader_=get_instance_or_none(
                                    TQuantityValueMillimeter,
                                    read_data.detector_distance,
                                ),
                                scan_position_setting__plate_reader_=filter_data.scan_position_setting,
                                detector_gain_setting=filter_data.gain,
                                detector_carriage_speed_setting=read_data.detector_carriage_speed,
                            )
                        ]
                    ),
                    luminescence=TQuantityValueRelativeLightUnit(
                        value=measurement.value
                    ),
                )
            )
        return measurement_document

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        lines = read_to_lines(named_file_contents)
        section_lines_reader = SectionLinesReader(lines)
        plates = list(section_lines_reader.iter_sections("^Software Version"))

        if not plates:
            msg = "No plate data found in file."
            raise AllotropeConversionError(msg)

        if len(plates) > 1:
            raise AllotropeConversionError(MULTIPLATE_FILE_ERROR)

        plate_data = PlateData.create(plates[0], named_file_contents.original_file_name)

        return self._create_model(plate_data, named_file_contents.original_file_name)
