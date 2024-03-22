from abc import ABC, abstractmethod
from typing import Union

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ContainerType,
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
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimeter,
    TQuantityValueMilliSecond,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValuePercent,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueRelativeLightUnit,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.revvity_kaleido.kaleido_builder import create_data
from allotropy.parsers.revvity_kaleido.kaleido_common_structure import WellPosition
from allotropy.parsers.revvity_kaleido.kaleido_structure_v2 import DataV2
from allotropy.parsers.revvity_kaleido.kaleido_structure_v3 import DataV3
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none
from allotropy.parsers.vendor_parser import VendorParser

VData = Union[DataV2, DataV3]
MeasurementItem = Union[
    OpticalImagingMeasurementDocumentItems,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
    FluorescencePointDetectionMeasurementDocumentItems,
    LuminescencePointDetectionMeasurementDocumentItems,
]


class MeasurementParser(ABC):
    @abstractmethod
    def parse(self, data: VData, well_position: WellPosition) -> MeasurementItem:
        pass

    def get_sample_document(
        self, data: VData, well_position: WellPosition
    ) -> SampleDocument:
        well_plate_identifier = data.get_well_plate_identifier()
        platemap_value = data.get_platemap_well_value(well_position)
        sample_identifier = (
            f"{well_plate_identifier}_{well_position}"
            if platemap_value == "-"
            else platemap_value
        )
        return SampleDocument(
            sample_identifier=sample_identifier,
            location_identifier=str(well_position),
            well_plate_identifier=well_plate_identifier,
            sample_role_type=data.get_sample_role_type(well_position),
        )


class FluorescenceMeasurementParser(MeasurementParser):
    def get_device_control_document(
        self, data: VData
    ) -> FluorescencePointDetectionDeviceControlDocumentItem:
        number_of_averages = data.get_number_of_averages()
        detector_distance = data.get_detector_distance()
        detector_wavelength = data.get_emission_wavelength()
        excitation_wavelength = data.get_excitation_wavelength()
        return FluorescencePointDetectionDeviceControlDocumentItem(
            device_type="fluorescence detector",
            detection_type="fluorescence",
            number_of_averages=(
                None
                if number_of_averages is None
                else TQuantityValueNumber(value=number_of_averages)
            ),
            detector_distance_setting__plate_reader_=(
                None
                if detector_distance is None
                else TQuantityValueMillimeter(value=detector_distance)
            ),
            scan_position_setting__plate_reader_=data.get_scan_position(),
            detector_wavelength_setting=(
                None
                if detector_wavelength is None
                else TQuantityValueNanometer(value=detector_wavelength)
            ),
            excitation_wavelength_setting=(
                None
                if excitation_wavelength is None
                else TQuantityValueNanometer(value=excitation_wavelength)
            ),
        )

    def parse(self, data: VData, well_position: WellPosition) -> MeasurementItem:
        return FluorescencePointDetectionMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            fluorescence=TQuantityValueRelativeFluorescenceUnit(
                value=data.get_well_value(well_position)
            ),
            sample_document=self.get_sample_document(data, well_position),
            device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[self.get_device_control_document(data)]
            ),
        )


class AbsorbanceMeasurementParser(MeasurementParser):
    def get_device_control_document(
        self, data: VData
    ) -> UltravioletAbsorbancePointDetectionDeviceControlDocumentItem:
        detector_distance = data.get_detector_distance()
        detector_wavelength = data.get_excitation_wavelength()
        return UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
            device_type="absorbance detector",
            detection_type=data.get_experiment_type(),
            number_of_averages=TQuantityValueNumber(
                value=assert_not_none(
                    data.get_number_of_averages(),
                    msg="Unable to find number of averages",
                ),
            ),
            detector_distance_setting__plate_reader_=(
                None
                if detector_distance is None
                else TQuantityValueMillimeter(value=detector_distance)
            ),
            detector_wavelength_setting=(
                None
                if detector_wavelength is None
                else TQuantityValueNanometer(value=detector_wavelength)
            ),
        )

    def parse(self, data: VData, well_position: WellPosition) -> MeasurementItem:
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=data.get_well_value(well_position)
            ),
            sample_document=self.get_sample_document(data, well_position),
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[self.get_device_control_document(data)]
            ),
        )


class LuminescenceMeasurementParser(MeasurementParser):
    def get_device_control_document(
        self, data: VData
    ) -> LuminescencePointDetectionDeviceControlDocumentItem:
        detector_distance = data.get_detector_distance()
        return LuminescencePointDetectionDeviceControlDocumentItem(
            device_type="luminescence detector",
            detection_type=data.get_experiment_type(),
            detector_distance_setting__plate_reader_=(
                None
                if detector_distance is None
                else TQuantityValueMillimeter(value=detector_distance)
            ),
        )

    def parse(self, data: VData, well_position: WellPosition) -> MeasurementItem:
        return LuminescencePointDetectionMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            luminescence=TQuantityValueRelativeLightUnit(
                value=data.get_well_value(well_position)
            ),
            sample_document=self.get_sample_document(data, well_position),
            device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[self.get_device_control_document(data)]
            ),
        )


class ImagingMeasurementParser(MeasurementParser):
    def get_device_control_document(
        self, data: VData
    ) -> OpticalImagingDeviceControlDocumentItem:
        detector_distance = data.get_focus_height()
        detector_wavelength = data.get_emission_wavelength()
        excitation_wavelength = data.get_excitation_wavelength()
        exposure_duration = data.get_exposure_duration()
        illumination = data.get_illumination()
        return OpticalImagingDeviceControlDocumentItem(
            device_type="imaging detector",
            detection_type=data.get_experiment_type(),
            detector_distance_setting__plate_reader_=(
                None
                if detector_distance is None
                else TQuantityValueMillimeter(value=detector_distance)
            ),
            detector_wavelength_setting=(
                None
                if detector_wavelength is None
                else TQuantityValueNanometer(value=detector_wavelength)
            ),
            excitation_wavelength_setting=(
                None
                if excitation_wavelength is None
                else TQuantityValueNanometer(value=excitation_wavelength)
            ),
            magnification_setting=TQuantityValueUnitless(value=4),
            exposure_duration_setting=(
                None
                if exposure_duration is None
                else TQuantityValueMilliSecond(value=exposure_duration)
            ),
            illumination_setting=(
                None
                if illumination is None
                else TQuantityValuePercent(value=illumination)
            ),
            transmitted_light_setting=data.get_transmitted_light(),
            fluorescent_tag_setting=data.get_fluorescent_tag(),
        )

    def parse(self, data: VData, well_position: WellPosition) -> MeasurementItem:
        return OpticalImagingMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            sample_document=self.get_sample_document(data, well_position),
            device_control_aggregate_document=OpticalImagingDeviceControlAggregateDocument(
                device_control_document=[self.get_device_control_document(data)],
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(  # CONSULT this should be in here?
                processed_data_document=[
                    ProcessedDataDocumentItem(
                        image_feature_aggregate_document=ImageFeatureAggregateDocument(
                            image_feature_document=[
                                ImageFeatureDocumentItem(
                                    image_feature_identifier=random_uuid_str(),
                                    image_feature_name=data.get_image_feature_name(),
                                    image_feature_result=TQuantityValueUnitless(
                                        value=data.get_image_feature_result(
                                            well_position  # CONSULT from which matrix
                                        )
                                    ),
                                    # data_source_aggregate_document=DataSourceAggregateDocument()  # CONSULT
                                ),
                            ]
                        )
                    )
                ]
            ),
        )


class KaleidoParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = create_data(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, file_name: str, data: VData) -> Model:
        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                plate_reader_document=self._get_plate_reader_document(data),
                device_system_document=self._get_device_system_document(data),
                data_system_document=self._get_data_system_document(
                    file_name, data.version
                ),
            ),
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
        )

    def _get_device_system_document(self, data: VData) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            device_identifier="EnSight",
            model_number="EnSight",
            product_manufacturer="Revvity",
            equipment_serial_number=data.get_equipment_serial_number(),
        )

    def _get_data_system_document(
        self, file_name: str, version: str
    ) -> DataSystemDocument:
        return DataSystemDocument(
            file_name=file_name,
            software_name="Kaleido",
            software_version=version,
            ASM_converter_name=ASM_CONVERTER_NAME,
            ASM_converter_version=ASM_CONVERTER_VERSION,
        )

    def _get_plate_reader_document(self, data: VData) -> list[PlateReaderDocumentItem]:
        measurement_parser = self._get_measurement_document_parser(
            data.get_experiment_type()
        )
        return [
            PlateReaderDocumentItem(
                measurement_aggregate_document=self._get_measurement_aggregate_document(
                    data, measurement_parser, well_position
                )
            )
            for well_position in data.iter_wells()
        ]

    def _get_measurement_aggregate_document(
        self,
        data: VData,
        measurement_parser: MeasurementParser,
        well_position: WellPosition,
    ) -> MeasurementAggregateDocument:
        return MeasurementAggregateDocument(
            container_type=ContainerType.well_plate,
            measurement_time=self._get_date_time(data.get_measurement_time()),
            plate_well_count=TQuantityValueNumber(value=data.get_plate_well_count()),
            experiment_type=data.get_experiment_type(),
            analytical_method_identifier=data.get_analytical_method_id(),
            experimental_data_identifier=data.get_experimentl_data_id(),
            measurement_document=[measurement_parser.parse(data, well_position)],
        )

    def _get_measurement_document_parser(
        self, experiment_type: str
    ) -> MeasurementParser:
        experiment_type_lower = experiment_type.lower()
        if "fluorescence" in experiment_type_lower or "alpha" in experiment_type_lower:
            return FluorescenceMeasurementParser()
        elif "abs" in experiment_type_lower:
            return AbsorbanceMeasurementParser()
        elif "luminescence" in experiment_type_lower:
            return LuminescenceMeasurementParser()
        elif "img" in experiment_type_lower:
            return ImagingMeasurementParser()
        else:
            error = f"Unable to find valid experiment type in '{experiment_type}'"
            raise AllotropeConversionError(error)
