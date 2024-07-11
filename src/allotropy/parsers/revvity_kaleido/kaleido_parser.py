from abc import ABC, abstractmethod

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ContainerType,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    ImageDocumentItem,
    ImageFeatureAggregateDocument,
    ImageFeatureDocumentItem,
    LuminescencePointDetectionDeviceControlAggregateDocument,
    LuminescencePointDetectionDeviceControlDocumentItem,
    LuminescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    OpticalImagingAggregateDocument,
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
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.revvity_kaleido.kaleido_builder import create_data
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    Channel,
    Data,
    ExperimentType,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser

MeasurementItem = (
    OpticalImagingMeasurementDocumentItems
    | UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    | FluorescencePointDetectionMeasurementDocumentItems
    | LuminescencePointDetectionMeasurementDocumentItems
)


class MeasurementParser(ABC):
    @abstractmethod
    def parse(self, data: Data, well_position: str) -> list[MeasurementItem]:
        pass

    @abstractmethod
    def get_experiment_type(self) -> ExperimentType:
        pass

    def get_sample_document(self, data: Data, well_position: str) -> SampleDocument:
        platemap_value = data.get_platemap_well_value(well_position)
        sample_identifier = (
            f"{data.results.barcode}_{well_position}"
            if platemap_value == "-"
            else platemap_value
        )
        return SampleDocument(
            sample_identifier=sample_identifier,
            location_identifier=str(well_position),
            well_plate_identifier=data.results.barcode,
            sample_role_type=data.get_sample_role_type(well_position),
        )


class FluorescenceMeasurementParser(MeasurementParser):
    def get_experiment_type(self) -> ExperimentType:
        return ExperimentType.FLUORESCENCE

    def get_device_control_document(
        self, data: Data
    ) -> FluorescencePointDetectionDeviceControlDocumentItem:
        return FluorescencePointDetectionDeviceControlDocumentItem(
            device_type="fluorescence detector",
            detection_type="fluorescence",
            number_of_averages=quantity_or_none(
                TQuantityValueNumber, data.measurements.number_of_averages
            ),
            detector_distance_setting__plate_reader_=quantity_or_none(
                TQuantityValueMillimeter, data.measurements.detector_distance
            ),
            scan_position_setting__plate_reader_=data.measurements.scan_position,
            detector_wavelength_setting=quantity_or_none(
                TQuantityValueNanometer, data.measurements.emission_wavelength
            ),
            excitation_wavelength_setting=quantity_or_none(
                TQuantityValueNanometer, data.measurements.excitation_wavelength
            ),
        )

    def parse(self, data: Data, well_position: str) -> list[MeasurementItem]:
        return [
            FluorescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=random_uuid_str(),
                fluorescence=TQuantityValueRelativeFluorescenceUnit(
                    value=data.get_well_float_value(well_position)
                ),
                sample_document=self.get_sample_document(data, well_position),
                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[self.get_device_control_document(data)]
                ),
            )
        ]


class AbsorbanceMeasurementParser(MeasurementParser):
    def get_experiment_type(self) -> ExperimentType:
        return ExperimentType.ABSORBANCE

    def get_device_control_document(
        self, data: Data
    ) -> UltravioletAbsorbancePointDetectionDeviceControlDocumentItem:
        return UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
            device_type="absorbance detector",
            detection_type=data.background_info.experiment_type,
            number_of_averages=TQuantityValueNumber(
                value=assert_not_none(
                    data.measurements.number_of_averages,
                    msg="Unable to find number of averages",
                ),
            ),
            detector_distance_setting__plate_reader_=quantity_or_none(
                TQuantityValueMillimeter, data.measurements.detector_distance
            ),
            detector_wavelength_setting=quantity_or_none(
                TQuantityValueNanometer, data.measurements.excitation_wavelength
            ),
        )

    def parse(self, data: Data, well_position: str) -> list[MeasurementItem]:
        return [
            UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                measurement_identifier=random_uuid_str(),
                absorbance=TQuantityValueMilliAbsorbanceUnit(
                    value=data.get_well_float_value(well_position)
                ),
                sample_document=self.get_sample_document(data, well_position),
                device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[self.get_device_control_document(data)]
                ),
            )
        ]


class LuminescenceMeasurementParser(MeasurementParser):
    def get_experiment_type(self) -> ExperimentType:
        return ExperimentType.LUMINESCENCE

    def get_device_control_document(
        self, data: Data
    ) -> LuminescencePointDetectionDeviceControlDocumentItem:
        return LuminescencePointDetectionDeviceControlDocumentItem(
            device_type="luminescence detector",
            detection_type=data.background_info.experiment_type,
            detector_distance_setting__plate_reader_=quantity_or_none(
                TQuantityValueMillimeter, data.measurements.detector_distance
            ),
        )

    def parse(self, data: Data, well_position: str) -> list[MeasurementItem]:
        return [
            LuminescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=random_uuid_str(),
                luminescence=TQuantityValueRelativeLightUnit(
                    value=data.get_well_float_value(well_position)
                ),
                sample_document=self.get_sample_document(data, well_position),
                device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[self.get_device_control_document(data)]
                ),
            )
        ]


class ImagingMeasurementParser(MeasurementParser):
    def get_experiment_type(self) -> ExperimentType:
        return ExperimentType.OPTICAL_IMAGING

    def get_device_control_document(
        self, data: Data, channel: Channel
    ) -> OpticalImagingDeviceControlDocumentItem:
        return OpticalImagingDeviceControlDocumentItem(
            device_type="imaging detector",
            detection_type="optical-imaging",
            detector_distance_setting__plate_reader_=quantity_or_none(
                TQuantityValueMillimeter, data.measurements.focus_height
            ),
            excitation_wavelength_setting=quantity_or_none(
                TQuantityValueNanometer, channel.excitation_wavelength
            ),
            magnification_setting=TQuantityValueUnitless(value=4),
            exposure_duration_setting=quantity_or_none(
                TQuantityValueMilliSecond, channel.exposure_duration
            ),
            illumination_setting=quantity_or_none(
                TQuantityValuePercent, channel.illumination
            ),
            transmitted_light_setting=channel.transmitted_light,
            fluorescent_tag_setting=channel.fluorescent_tag,
        )

    def parse(self, data: Data, well_position: str) -> list[MeasurementItem]:
        return [
            OpticalImagingMeasurementDocumentItems(
                measurement_identifier=random_uuid_str(),
                sample_document=self.get_sample_document(data, well_position),
                device_control_aggregate_document=OpticalImagingDeviceControlAggregateDocument(
                    device_control_document=[
                        self.get_device_control_document(data, channel)
                    ],
                ),
            )
            for channel in data.measurements.channels
        ]


class KaleidoParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Revvity Kaleido"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = create_data(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, file_name: str, data: Data) -> Model:
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

    def _get_device_system_document(self, data: Data) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            device_identifier="EnSight",
            model_number="EnSight",
            product_manufacturer="Revvity",
            equipment_serial_number=data.measurement_info.instrument_serial_number,
        )

    def _get_data_system_document(
        self, file_name: str, version: str
    ) -> DataSystemDocument:
        return DataSystemDocument(
            file_name=file_name,
            software_name="Kaleido",
            software_version=version,
            ASM_converter_name=self.get_asm_converter_name(),
            ASM_converter_version=ASM_CONVERTER_VERSION,
        )

    def _get_plate_reader_document(self, data: Data) -> list[PlateReaderDocumentItem]:
        measurement_parser = self._get_measurement_document_parser(
            data.background_info.experiment_type
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
        data: Data,
        measurement_parser: MeasurementParser,
        well_position: str,
    ) -> MeasurementAggregateDocument:
        return MeasurementAggregateDocument(
            container_type=ContainerType.well_plate,
            measurement_time=self._get_date_time(
                data.measurement_info.measurement_time
            ),
            plate_well_count=TQuantityValueNumber(
                value=data.results.get_plate_well_count()
            ),
            experiment_type=data.background_info.experiment_type,
            analytical_method_identifier=data.measurement_info.protocol_signature,
            experimental_data_identifier=data.measurement_info.measurement_signature,
            measurement_document=measurement_parser.parse(data, well_position),
            image_aggregate_document=self.get_image_aggregate_document(
                data, well_position, measurement_parser
            ),
            processed_data_aggregate_document=self.get_processed_data_aggregate_document(
                data, well_position, measurement_parser
            ),
        )

    def get_image_aggregate_document(
        self,
        data: Data,
        well_position: str,
        measurement_parser: MeasurementParser,
    ) -> OpticalImagingAggregateDocument | None:
        if measurement_parser.get_experiment_type() != ExperimentType.OPTICAL_IMAGING:
            return None

        return OpticalImagingAggregateDocument(
            image_document=[
                ImageDocumentItem(
                    experimental_data_identifier=data.get_well_str_value(well_position),
                )
            ]
        )

    def get_processed_data_aggregate_document(
        self,
        data: Data,
        well_position: str,
        measurement_parser: MeasurementParser,
    ) -> ProcessedDataAggregateDocument | None:
        if (
            measurement_parser.get_experiment_type() != ExperimentType.OPTICAL_IMAGING
            or not data.analysis_results
        ):
            return None

        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    image_feature_aggregate_document=ImageFeatureAggregateDocument(
                        image_feature_document=[
                            ImageFeatureDocumentItem(
                                image_feature_identifier=random_uuid_str(),
                                image_feature_name=analysis_result.analysis_parameter,
                                image_feature_result=TQuantityValueUnitless(
                                    value=analysis_result.get_image_feature_result(
                                        well_position
                                    )
                                ),
                                data_source_aggregate_document=DataSourceAggregateDocument(
                                    data_source_document=[
                                        DataSourceDocumentItem(
                                            data_source_identifier=data.get_well_str_value(
                                                well_position
                                            ),
                                            data_source_feature="image feature",  # wait for actual value
                                        )
                                    ]
                                ),
                            )
                            for analysis_result in data.analysis_results
                        ]
                    )
                )
            ]
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
