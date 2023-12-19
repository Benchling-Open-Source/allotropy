from collections.abc import Iterator
from typing import Optional
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
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
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
    ReadType,
    WellData,
)
from allotropy.parsers.utils.values import (
    assert_not_none,
)
from allotropy.parsers.vendor_parser import VendorParser


class SoftmaxproParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents.contents, encoding=None)
        reader = CsvReader(lines)
        data = Data.create(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, file_name: str, data: Data) -> Model:
        plate_block = data.get_plate_block()
        return Model(
            field_asm_manifest="http://purl.allotrope.org/json-schemas/adm/plate-reader/BENCHLING/2023/09/plate-reader.schema",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier="null",
                    model_number="null",
                ),
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    software_name="SoftMax Pro",
                    software_version=None,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                plate_reader_document=[
                    self._get_plate_reader_document_item(plate_block, position)
                    for position in plate_block.iter_wells()
                ],
                calculated_data_aggregate_document=None,
            ),
        )

    def _get_plate_reader_document_item(
        self, plate_block: PlateBlock, position: str
    ) -> PlateReaderDocumentItem:
        if plate_block.plate_block_type == "Absorbance":
            return PlateReaderDocumentItem(
                measurement_aggregate_document=MeasurementAggregateDocument(
                    measurement_time="null",
                    plate_well_count=TQuantityValueNumber(plate_block.header.num_wells),
                    container_type=ContainerType.well_plate,
                    measurement_document=list(
                        self._iter_absorbance_measurement_document(
                            plate_block, position
                        ),
                    ),
                )
            )
        elif plate_block.plate_block_type == "Luminescence":
            return PlateReaderDocumentItem(
                measurement_aggregate_document=MeasurementAggregateDocument(
                    measurement_time="null",
                    plate_well_count=TQuantityValueNumber(plate_block.header.num_wells),
                    container_type=ContainerType.well_plate,
                    measurement_document=list(
                        self._iter_luminescence_measurement_document(
                            plate_block, position
                        ),
                    ),
                )
            )
        elif plate_block.plate_block_type == "Fluorescence":
            return PlateReaderDocumentItem(
                measurement_aggregate_document=MeasurementAggregateDocument(
                    measurement_time="null",
                    plate_well_count=TQuantityValueNumber(plate_block.header.num_wells),
                    container_type=ContainerType.well_plate,
                    measurement_document=list(
                        self._iter_fluorescence_measurement_document(
                            plate_block, position
                        )
                    ),
                )
            )
        else:
            error = "Unable to find valid plate block type."
            raise AllotropeConversionError(error)

    def _iter_fluorescence_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> Iterator[FluorescencePointDetectionMeasurementDocumentItems]:
        if plate_block.header.scan_position == "TRUE":
            scan_position = (
                ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_
            )
        elif plate_block.header.scan_position == "FALSE":
            scan_position = (
                ScanPositionSettingPlateReader.top_scan_position__plate_reader_
            )
        else:
            error = "Unable to find valid scan position."
            raise AllotropeConversionError(error)

        reads_per_well = assert_not_none(
            plate_block.header.reads_per_well,
            msg="Unable to find plate block reads per well.",
        )

        excitation_wavelengths = assert_not_none(
            plate_block.header.excitation_wavelengths,
            msg="Unable to find plate block excitation wavelength.",
        )

        cutoff_filters = assert_not_none(
            plate_block.header.cutoff_filters,
            msg="Unable to find plate block cutoff filters.",
        )

        for idx, data_element in enumerate(
            plate_block.block_data.iter_wavelengths(position)
        ):
            wavelength = assert_not_none(
                data_element.wavelength,
                msg=f"Unable to find wavelength for position {data_element.position}.",
            )
            yield FluorescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=str(uuid.uuid4()),
                fluorescence=TRelativeFluorescenceUnit(value=data_element.value),
                compartment_temperature=None
                if data_element.temperature is None
                else TQuantityValueDegreeCelsius(data_element.temperature),
                sample_document=SampleDocument(
                    location_identifier=data_element.position,
                    well_plate_identifier=plate_block.header.name,
                    sample_identifier=f"{plate_block.header.name} {data_element.position}",
                    sample_role_type=None,
                    well_location_identifier=None,
                    vial_location_identifier=None,
                    mass_concentration=None,
                ),
                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        FluorescencePointDetectionDeviceControlDocumentItem(
                            device_type="plate reader",
                            detection_type=plate_block.header.read_mode,
                            scan_position_setting__plate_reader_=scan_position,
                            detector_wavelength_setting=TQuantityValueNanometer(
                                wavelength
                            ),
                            excitation_wavelength_setting=TQuantityValueNanometer(
                                excitation_wavelengths[idx]
                            ),
                            wavelength_filter_cutoff_setting=TQuantityValueNanometer(
                                cutoff_filters[idx]
                            ),
                            number_of_averages=TQuantityValueNumber(reads_per_well),
                            detector_gain_setting=plate_block.header.pmt_gain,
                        )
                    ]
                ),
            )

    def _iter_luminescence_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> Iterator[LuminescencePointDetectionMeasurementDocumentItems]:
        reads_per_well = assert_not_none(
            plate_block.header.reads_per_well,
            msg="Unable to find plate block reads per well.",
        )

        for data_element in plate_block.block_data.iter_wavelengths(position):
            wavelength = assert_not_none(
                data_element.wavelength,
                msg=f"Unable to find wavelength for position {data_element.position}.",
            )
            yield LuminescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=str(uuid.uuid4()),
                luminescence=TRelativeLightUnit(value=data_element.value),
                compartment_temperature=None
                if data_element.temperature is None
                else TQuantityValueDegreeCelsius(data_element.temperature),
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
                                wavelength
                            ),
                            number_of_averages=TQuantityValueNumber(reads_per_well),
                            detector_gain_setting=plate_block.header.pmt_gain,
                        )
                    ]
                ),
            )

    def _iter_absorbance_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> Iterator[UltravioletAbsorbancePointDetectionMeasurementDocumentItems]:
        for data_element in plate_block.block_data.iter_wavelengths(position):
            wavelength = assert_not_none(
                data_element.wavelength,
                msg=f"Unable to find wavelength for position {data_element.position}.",
            )
            yield UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                measurement_identifier=str(uuid.uuid4()),
                absorbance=TQuantityValueMilliAbsorbanceUnit(value=data_element.value),
                compartment_temperature=None
                if data_element.temperature is None
                else TQuantityValueDegreeCelsius(data_element.temperature),
                sample_document=SampleDocument(
                    location_identifier=data_element.position,
                    well_plate_identifier=plate_block.header.name,
                    sample_identifier=f"{plate_block.header.name} {data_element.position}",
                    sample_role_type=None,
                    well_location_identifier=None,
                    vial_location_identifier=None,
                    mass_concentration=None,
                ),
                device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                            device_type="plate reader",
                            detection_type=plate_block.header.read_mode,
                            detector_wavelength_setting=TQuantityValueNanometer(
                                wavelength
                            ),
                        )
                    ]
                ),
            )

    def get_data_cube_dimensions(
        self, plate_block: PlateBlock
    ) -> list[tuple[str, str, Optional[str]]]:
        dimensions: list[tuple[str, str, Optional[str]]] = []

        if plate_block.header.read_type == ReadType.KINETIC.value:
            dimensions = [("double", "elapsed time", "s")]
        elif plate_block.header.read_type == ReadType.WELL_SCAN.value:
            dimensions = [("int", "x", None)]
        elif plate_block.header.read_type in {
            ReadType.SPECTRUM.value,
            ReadType.ENDPOINT.value,
        }:
            dimensions = [("int", "wavelength", "nm")]
        else:
            error = f"Cannot make data cube for read type {plate_block.header.read_type}; only {sorted(ReadType._member_names_)} are supported."
            raise AllotropeConversionError(error)

        if plate_block.has_wavelength_dimension:
            dimensions.append(("int", "wavelength", "nm"))

        return dimensions

    def generate_data_cube(
        self, plate_block: PlateBlock, well_data: WellData
    ) -> TDatacube:
        dimension_data = [well_data.dimensions] + (
            [well_data.wavelengths] if plate_block.has_wavelength_dimension else []
        )
        return TDatacube(
            cube_structure=TDatacubeStructure(
                [
                    TDatacubeComponent(FieldComponentDatatype(data_type), concept, unit)
                    for data_type, concept, unit in self.get_data_cube_dimensions(
                        plate_block
                    )
                ],
                [
                    TDatacubeComponent(
                        FieldComponentDatatype("double"),
                        plate_block.header.concept,
                        plate_block.header.unit,
                    )
                ],
            ),
            data=TDatacubeData(
                dimension_data,  # type: ignore[arg-type]
                [well_data.values],
            ),
        )
