from typing import Union
import uuid

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ContainerType,
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
    ScanPositionSettingPlateReader,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TRelativeFluorescenceUnit,
    TRelativeLightUnit,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.exceptions import (
    AllotropeConversionError,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import (
    Data,
    PlateBlock,
)
from allotropy.parsers.utils.values import (
    assert_not_none,
)
from allotropy.parsers.vendor_parser import VendorParser

EPOCH = "1970-01-01T00:00:00-00:00"
NULL = "null"


class SoftmaxproParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents.contents, encoding=None)
        reader = CsvReader(lines)
        data = Data.create(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, file_name: str, data: Data) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/json-schemas/adm/plate-reader/BENCHLING/2023/09/plate-reader.schema",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=NULL,
                    model_number=NULL,
                ),
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    software_name="SoftMax Pro",
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                plate_reader_document=[
                    self._get_plate_reader_document_item(plate_block, position)
                    for plate_block in data.get_plate_block()
                    for position in plate_block.iter_wells()
                ],
            ),
        )

    def _get_plate_reader_document_item(
        self, plate_block: PlateBlock, position: str
    ) -> PlateReaderDocumentItem:
        plate_block_type = plate_block.plate_block_type

        measurement_document: list[
            Union[
                UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
                FluorescencePointDetectionMeasurementDocumentItems,
                LuminescencePointDetectionMeasurementDocumentItems,
            ]
        ]

        if plate_block_type == "Absorbance":
            measurement_document = self._get_absorbance_measurement_document(
                plate_block,
                position,
            )
        elif plate_block_type == "Luminescence":
            measurement_document = self._get_luminescence_measurement_document(
                plate_block,
                position,
            )
        elif plate_block_type == "Fluorescence":
            measurement_document = self._get_fluorescence_measurement_document(
                plate_block,
                position,
            )
        else:
            error = f"{plate_block_type} is not a valid plate block type."
            raise AllotropeConversionError(error)

        return PlateReaderDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=EPOCH,
                plate_well_count=TQuantityValueNumber(plate_block.header.num_wells),
                container_type=ContainerType.well_plate,
                measurement_document=measurement_document,
            )
        )

    def _get_fluorescence_plate_block_scan_position(
        self, plate_block: PlateBlock
    ) -> ScanPositionSettingPlateReader:
        if plate_block.header.scan_position == "TRUE":
            return ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_
        elif plate_block.header.scan_position == "FALSE":
            return ScanPositionSettingPlateReader.top_scan_position__plate_reader_
        else:
            error = "Unable to find valid scan position."
            raise AllotropeConversionError(error)

    def _get_fluorescence_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> list[
        Union[
            UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
            FluorescencePointDetectionMeasurementDocumentItems,
            LuminescencePointDetectionMeasurementDocumentItems,
        ]
    ]:
        return [
            FluorescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=str(uuid.uuid4()),
                fluorescence=TRelativeFluorescenceUnit(value=data_element.value),
                compartment_temperature=(
                    None
                    if data_element.temperature is None
                    else TQuantityValueDegreeCelsius(data_element.temperature)
                ),
                sample_document=SampleDocument(
                    location_identifier=data_element.position,
                    well_plate_identifier=plate_block.header.name,
                    sample_identifier=f"{plate_block.header.name} {data_element.position}",
                ),
                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        FluorescencePointDetectionDeviceControlDocumentItem(
                            device_type="plate reader",
                            detection_type=plate_block.header.read_mode,
                            scan_position_setting__plate_reader_=self._get_fluorescence_plate_block_scan_position(
                                plate_block
                            ),
                            detector_wavelength_setting=TQuantityValueNanometer(
                                data_element.wavelength
                            ),
                            excitation_wavelength_setting=(
                                None
                                if plate_block.header.excitation_wavelengths is None
                                else TQuantityValueNanometer(
                                    plate_block.header.excitation_wavelengths[idx]
                                )
                            ),
                            wavelength_filter_cutoff_setting=(
                                None
                                if plate_block.header.cutoff_filters is None
                                else TQuantityValueNanometer(
                                    plate_block.header.cutoff_filters[idx]
                                )
                            ),
                            number_of_averages=TQuantityValueNumber(
                                plate_block.header.reads_per_well,
                            ),
                            detector_gain_setting=plate_block.header.pmt_gain,
                        )
                    ]
                ),
            )
            for idx, data_element in enumerate(
                plate_block.block_data.iter_wavelengths(position)
            )
        ]

    def _get_luminescence_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> list[
        Union[
            UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
            FluorescencePointDetectionMeasurementDocumentItems,
            LuminescencePointDetectionMeasurementDocumentItems,
        ]
    ]:
        reads_per_well = assert_not_none(
            plate_block.header.reads_per_well,
            msg="Unable to find plate block reads per well.",
        )

        return [
            LuminescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=str(uuid.uuid4()),
                luminescence=TRelativeLightUnit(value=data_element.value),
                compartment_temperature=(
                    None
                    if data_element.temperature is None
                    else TQuantityValueDegreeCelsius(data_element.temperature)
                ),
                sample_document=SampleDocument(
                    location_identifier=data_element.position,
                    well_plate_identifier=plate_block.header.name,
                    sample_identifier=f"{plate_block.header.name} {data_element.position}",
                ),
                device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        LuminescencePointDetectionDeviceControlDocumentItem(
                            device_type="plate reader",
                            detection_type=plate_block.header.read_mode,
                            detector_wavelength_setting=TQuantityValueNanometer(
                                data_element.wavelength
                            ),
                            number_of_averages=TQuantityValueNumber(reads_per_well),
                            detector_gain_setting=plate_block.header.pmt_gain,
                        )
                    ]
                ),
            )
            for data_element in plate_block.block_data.iter_wavelengths(position)
        ]

    def _get_absorbance_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> list[
        Union[
            UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
            FluorescencePointDetectionMeasurementDocumentItems,
            LuminescencePointDetectionMeasurementDocumentItems,
        ]
    ]:
        return [
            UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                measurement_identifier=str(uuid.uuid4()),
                absorbance=TQuantityValueMilliAbsorbanceUnit(value=data_element.value),
                compartment_temperature=(
                    None
                    if data_element.temperature is None
                    else TQuantityValueDegreeCelsius(data_element.temperature)
                ),
                sample_document=SampleDocument(
                    location_identifier=data_element.position,
                    well_plate_identifier=plate_block.header.name,
                    sample_identifier=f"{plate_block.header.name} {data_element.position}",
                ),
                device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                            device_type="plate reader",
                            detection_type=plate_block.header.read_mode,
                            detector_wavelength_setting=TQuantityValueNanometer(
                                data_element.wavelength
                            ),
                        )
                    ]
                ),
            )
            for data_element in plate_block.block_data.iter_wavelengths(position)
        ]
