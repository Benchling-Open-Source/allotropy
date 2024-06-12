from collections.abc import Sequence
from typing import Any, Union

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ContainerType,
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
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliSecond,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader
from allotropy.parsers.agilent_gen5_image.agilent_gen5_image_structure import (
    ImageFeature,
    PlateData,
    ReadData,
)
from allotropy.parsers.agilent_gen5_image.constants import (
    DEFAULT_SOFTWARE_NAME,
    DETECTION_TYPE,
    DEVICE_TYPE,
    MULTIPLATE_FILE_ERROR,
    NO_PLATE_DATA_ERROR,
)
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

MeasurementDocumentAttributeClasses = Union[
    TQuantityValueMilliSecond,
    TQuantityValueNanometer,
    TQuantityValueUnitless,
]


def get_instance_or_none(
    cls: type[MeasurementDocumentAttributeClasses], value: Any
) -> Any:
    return cls(value=value) if value is not None else None


class AgilentGen5ImageParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Agilent Gen5 Image"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def _create_model(self, plate_data: PlateData, file_name: str) -> Model:
        header_data = plate_data.header_data

        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier="N/A",
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
                    for well_position in plate_data.results.image_features.keys()
                ],
            ),
        )

    def _get_plate_reader_document_item(
        self, plate_data: PlateData, well_position: str
    ) -> PlateReaderDocumentItem:
        header_data = plate_data.header_data
        plate_well_count = len(plate_data.results.image_features)

        image_features = plate_data.results.image_features[well_position]
        processed_data_aggregate_document = ProcessedDataAggregateDocument(
            processed_data_document=self._get_processed_data_document(image_features)
        )

        sample_document = self._get_sample_document(plate_data, well_position)
        measurement_document = list(
            self._get_measurement_document(plate_data.read_data, sample_document)
        )

        # Image features (included in the processed data document) are included at the measurement
        # level only when there is only one device control document (and thus one measurement document)
        # otherwise they are included at the measurement aggregate document level.
        if len(measurement_document) == 1:
            first_doc = measurement_document[0]
            first_doc.processed_data_aggregate_document = (
                processed_data_aggregate_document
            )

        return PlateReaderDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(header_data.datetime),
                analytical_method_identifier=header_data.protocol_file_path,
                experimental_data_identifier=header_data.experiment_file_path,
                plate_well_count=TQuantityValueNumber(value=plate_well_count),
                container_type=ContainerType.well_plate,
                measurement_document=list(measurement_document),
                processed_data_aggregate_document=(
                    processed_data_aggregate_document
                    if len(measurement_document) > 1
                    else None
                ),
            )
        )

    def _get_processed_data_document(
        self,
        image_features: list[ImageFeature],
    ) -> list[ProcessedDataDocumentItem]:
        return [
            ProcessedDataDocumentItem(
                processed_data_identifier=random_uuid_str(),
                image_feature_aggregate_document=ImageFeatureAggregateDocument(
                    image_feature_document=[
                        ImageFeatureDocumentItem(
                            image_feature_identifier=image_feature.identifier,
                            image_feature_name=image_feature.name,
                            image_feature_result=TQuantityValueUnitless(
                                value=image_feature.result
                            ),
                        )
                        for image_feature in image_features
                    ]
                ),
            )
        ]

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

    def _get_measurement_document(
        self, read_data: ReadData, sample_document: SampleDocument
    ) -> Sequence[OpticalImagingMeasurementDocumentItems]:
        measurement_document = []
        for read_section in read_data.read_sections:
            measurement_document.extend(
                [
                    OpticalImagingMeasurementDocumentItems(
                        measurement_identifier=random_uuid_str(),
                        sample_document=sample_document,
                        device_control_aggregate_document=OpticalImagingDeviceControlAggregateDocument(
                            device_control_document=[
                                OpticalImagingDeviceControlDocumentItem(
                                    device_type=DEVICE_TYPE,
                                    detection_type=DETECTION_TYPE,
                                    # This setting won't get reported at the moment since Gen5 only reports it
                                    # in micrometers and we don't do conversions on the adapters at the moment
                                    # detector_distance_setting__plate_reader_=get_instance_or_none(
                                    #     TQuantityValueMillimeter,
                                    #     instrument_settings.detector_distance,
                                    # ),
                                    detector_gain_setting=instrument_settings.detector_gain,
                                    magnification_setting=get_instance_or_none(
                                        TQuantityValueUnitless,
                                        read_section.magnification_setting,
                                    ),
                                    illumination_setting=get_instance_or_none(
                                        TQuantityValueUnitless,
                                        instrument_settings.illumination,
                                    ),
                                    transmitted_light_setting=instrument_settings.transmitted_light,
                                    auto_focus_setting=instrument_settings.auto_focus,
                                    image_count_setting=get_instance_or_none(
                                        TQuantityValueUnitless,
                                        read_section.image_count_setting,
                                    ),
                                    fluorescent_tag_setting=instrument_settings.fluorescent_tag,
                                    exposure_duration_setting=get_instance_or_none(
                                        TQuantityValueMilliSecond,
                                        instrument_settings.exposure_duration,
                                    ),
                                    excitation_wavelength_setting=get_instance_or_none(
                                        TQuantityValueNanometer,
                                        instrument_settings.excitation_wavelength,
                                    ),
                                    detector_wavelength_setting=get_instance_or_none(
                                        TQuantityValueNanometer,
                                        instrument_settings.detector_wavelength,
                                    ),
                                )
                            ]
                        ),
                    )
                    for instrument_settings in read_section.instrument_settings_list
                ]
            )

        return measurement_document

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        lines = read_to_lines(named_file_contents)
        section_lines_reader = SectionLinesReader(lines)
        plates = list(section_lines_reader.iter_sections("^Software Version"))

        if not plates:
            raise AllotropeConversionError(NO_PLATE_DATA_ERROR)

        if len(plates) > 1:
            raise AllotropeConversionError(MULTIPLATE_FILE_ERROR)

        plate_data = PlateData.create(plates[0], named_file_contents.original_file_name)

        return self._create_model(plate_data, named_file_contents.original_file_name)
