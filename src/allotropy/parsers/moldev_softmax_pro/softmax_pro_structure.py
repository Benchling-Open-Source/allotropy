from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import Any, ClassVar, Optional
import uuid

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentFluorescence,
    DeviceControlDocumentItem as DeviceControlDocumentItemFluorescence,
    MeasurementAggregateDocument as MeasurementAggregateDocumentFluorescence,
    MeasurementDocumentItem as MeasurementDocumentItemFluorescence,
    Model as ModelFluorescence,
)
from allotropy.allotrope.models.luminescence_benchling_2023_09_luminescence import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentLuminescence,
    DeviceControlDocumentItem as DeviceControlDocumentItemLuminescence,
    MeasurementAggregateDocument as MeasurementAggregateDocumentLuminescence,
    MeasurementDocumentItem as MeasurementDocumentItemLuminescence,
    Model as ModelLuminescence,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueNanometer,
    TQuantityValueNumber,
)
from allotropy.allotrope.models.ultraviolet_absorbance_benchling_2023_09_ultraviolet_absorbance import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentAbsorbance,
    DeviceControlDocumentItem as DeviceControlDocumentItemAbsorbance,
    MeasurementAggregateDocument as MeasurementAggregateDocumentAbsorbance,
    MeasurementDocumentItem as MeasurementDocumentItemAbsorbance,
    Model as ModelAbsorbance,
)
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.moldev_softmax_pro.plate_block import (
    Block,
    GroupBlock,
    NoteBlock,
    PlateBlock,
    split_wavelengths,
    WellData,
)
from allotropy.parsers.utils.values import (
    assert_not_none,
    natural_sort_key,
    try_int,
    value_or_none,
)

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"


class FluorescenceOrLuminescencePlateBlock(PlateBlock):
    EXCITATION_WAVELENGTHS_IDX: ClassVar[int]

    def parse_read_mode_header(self, header: list[Optional[str]]) -> None:
        [
            excitation_wavelengths_str,
            self.cutoff,
            cutoff_filters_str,
            self.sweep_wave,
            self.sweep_wavelength,
            self.reads_per_well,
            self.pmt_gain,
            self.start_integration_time,
            self.end_integration_time,
            self.first_row,
            num_rows,
        ] = header[
            self.EXCITATION_WAVELENGTHS_IDX : self.EXCITATION_WAVELENGTHS_IDX + 11
        ]
        self.excitation_wavelengths = split_wavelengths(excitation_wavelengths_str)
        self.cutoff_filters = split_wavelengths(cutoff_filters_str)
        self.num_rows = assert_not_none(try_int(num_rows), "num_rows")


class FluorescencePlateBlock(FluorescenceOrLuminescencePlateBlock):
    READ_MODE = "Fluorescence"
    CONCEPT = "fluorescence"
    UNIT = "RFU"
    DATA_TYPE_IDX = 7
    EXCITATION_WAVELENGTHS_IDX = 20

    # TODO: the reason we can't factor out DeviceControlDocumentItemFluorescence and the enclosing classes is because the
    # Fluorescence ASM model has these extra fields. We may be able to fix this by templating the PlateBlock
    # class on these classes, or some clever shared/models refactoring.
    def generate_device_control_doc(self) -> DeviceControlDocumentItemFluorescence:
        device_control_doc = DeviceControlDocumentItemFluorescence(
            detector_gain_setting=self.pmt_gain
        )

        if self.is_single_wavelength:
            device_control_doc.detector_wavelength_setting = TQuantityValueNanometer(
                self.wavelengths[0]
            )
        if self.excitation_wavelengths and len(self.excitation_wavelengths) == 1:
            device_control_doc.excitation_wavelength_setting = TQuantityValueNanometer(
                self.excitation_wavelengths[0]
            )
        if self.cutoff_filters and len(self.cutoff_filters) == 1:
            device_control_doc.wavelength_filter_cutoff_setting = (
                TQuantityValueNanometer(self.cutoff_filters[0])
            )

        return device_control_doc

    def generate_measurement_doc(
        self, well: str, well_data: WellData
    ) -> MeasurementDocumentItemFluorescence:
        measurement = MeasurementDocumentItemFluorescence(
            DeviceControlAggregateDocumentFluorescence(
                [self.generate_device_control_doc()]
            ),
            self.generate_sample_document(well),
        )

        if well_data.temperature is not None:
            measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                float(well_data.temperature)
            )

        if not well_data.is_empty:
            measurement.data_cube = self.generate_data_cube(well_data)

        if well_data.processed_data:
            measurement.processed_data_aggregate_document = (
                self.generate_processed_data_aggreate_document(well_data)
            )

        return measurement

    def to_allotrope(self) -> Any:
        wells = sorted(self.well_data.keys(), key=natural_sort_key)

        allotrope_file = ModelFluorescence(
            measurement_aggregate_document=MeasurementAggregateDocumentFluorescence(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(self.num_wells),
                measurement_document=[
                    self.generate_measurement_doc(well, self.well_data[well])
                    for well in wells
                ],
            )
        )

        return allotrope_file


class LuminescencePlateBlock(FluorescenceOrLuminescencePlateBlock):
    READ_MODE = "Luminescence"
    CONCEPT = "luminescence"
    UNIT = "RLU"
    DATA_TYPE_IDX = 6
    EXCITATION_WAVELENGTHS_IDX = 19

    def generate_device_control_doc(self) -> DeviceControlDocumentItemLuminescence:
        device_control_doc = DeviceControlDocumentItemLuminescence(
            detector_gain_setting=self.pmt_gain
        )

        if self.is_single_wavelength:
            device_control_doc.detector_wavelength_setting = TQuantityValueNanometer(
                self.wavelengths[0]
            )

        return device_control_doc

    def generate_measurement_doc(
        self, well: str, well_data: WellData
    ) -> MeasurementDocumentItemLuminescence:
        measurement = MeasurementDocumentItemLuminescence(
            DeviceControlAggregateDocumentLuminescence(
                [self.generate_device_control_doc()]
            ),
            self.generate_sample_document(well),
        )

        if well_data.temperature is not None:
            measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                float(well_data.temperature)
            )

        if not well_data.is_empty:
            measurement.data_cube = self.generate_data_cube(well_data)

        if well_data.processed_data:
            measurement.processed_data_aggregate_document = (
                self.generate_processed_data_aggreate_document(well_data)
            )

        return measurement

    def to_allotrope(self) -> Any:
        wells = sorted(self.well_data.keys(), key=natural_sort_key)

        allotrope_file = ModelLuminescence(
            measurement_aggregate_document=MeasurementAggregateDocumentLuminescence(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(self.num_wells),
                measurement_document=[
                    self.generate_measurement_doc(well, self.well_data[well])
                    for well in wells
                ],
            )
        )

        return allotrope_file


class AbsorbancePlateBlock(PlateBlock):
    READ_MODE = "Absorbance"
    CONCEPT = "absorbance"
    UNIT = "mAU"
    DATA_TYPE_IDX = 6

    def parse_read_mode_header(self, header: list[Optional[str]]) -> None:
        [self.first_row, num_rows] = header[19:21]
        self.pmt_gain = None
        self.num_rows = assert_not_none(try_int(num_rows), "num_rows")

    def generate_device_control_doc(self) -> DeviceControlDocumentItemAbsorbance:
        device_control_doc = DeviceControlDocumentItemAbsorbance(
            detector_gain_setting=self.pmt_gain
        )

        if self.is_single_wavelength:
            device_control_doc.detector_wavelength_setting = TQuantityValueNanometer(
                self.wavelengths[0]
            )

        return device_control_doc

    def generate_measurement_doc(
        self, well: str, well_data: WellData
    ) -> MeasurementDocumentItemAbsorbance:
        measurement = MeasurementDocumentItemAbsorbance(
            DeviceControlAggregateDocumentAbsorbance(
                [self.generate_device_control_doc()]
            ),
            self.generate_sample_document(well),
        )

        if well_data.temperature is not None:
            measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                float(well_data.temperature)
            )

        if not well_data.is_empty:
            measurement.data_cube = self.generate_data_cube(well_data)

        if well_data.processed_data:
            measurement.processed_data_aggregate_document = (
                self.generate_processed_data_aggreate_document(well_data)
            )

        return measurement

    def to_allotrope(self) -> Any:
        wells = sorted(self.well_data.keys(), key=natural_sort_key)

        allotrope_file = ModelAbsorbance(
            measurement_aggregate_document=MeasurementAggregateDocumentAbsorbance(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(self.num_wells),
                measurement_document=[
                    self.generate_measurement_doc(well, self.well_data[well])
                    for well in wells
                ],
            )
        )

        return allotrope_file


def create_plate_block(raw_lines: list[str]) -> PlateBlock:
    split_lines = [
        [value_or_none(value) for value in raw_line.split("\t")]
        for raw_line in raw_lines
    ]
    header = split_lines[0]
    read_mode = header[5]

    plate_block_cls = {
        "Absorbance": AbsorbancePlateBlock,
        "Fluorescence": FluorescencePlateBlock,
        "Luminescence": LuminescencePlateBlock,
    }

    if cls := plate_block_cls.get(read_mode or ""):
        return cls(header, split_lines, raw_lines)

    error = f"unrecognized read mode {read_mode}"
    raise AllotropeConversionError(error)


def create_block(lines: list[str]) -> Block:
    all_blocks: list[type[Block]] = [GroupBlock, NoteBlock, PlateBlock]
    block_cls_by_type = {cls.BLOCK_TYPE: cls for cls in all_blocks}

    for key, block_cls in block_cls_by_type.items():
        if lines[0].startswith(key):
            if block_cls == PlateBlock:
                return create_plate_block(lines)
            return block_cls(lines)

    error = f"unrecognized block {lines[0]}"
    raise AllotropeConversionError(error)


@dataclass
class BlockList:
    blocks: list[Block]

    @staticmethod
    def create(lines_reader: LinesReader) -> BlockList:
        return BlockList(
            blocks=[
                create_block(block) for block in BlockList._iter_blocks(lines_reader)
            ]
        )

    @staticmethod
    def _get_n_blocks(lines_reader: LinesReader) -> int:
        if search_result := re.search(BLOCKS_LINE_REGEX, lines_reader.pop() or ""):
            return int(search_result.group(1))
        error = "unrecognized start line"
        raise AllotropeConversionError(error)

    @staticmethod
    def _iter_blocks(lines_reader: LinesReader) -> Iterator[list[str]]:
        n_blocks = BlockList._get_n_blocks(lines_reader)
        for _ in range(n_blocks):
            yield list(lines_reader.pop_until(END_LINE_REGEX))
            lines_reader.pop()  # drop end line
            lines_reader.drop_empty()


@dataclass
class Data:
    block_list: BlockList

    def get_plate_block(self) -> PlateBlock:
        plate_blocks = [
            block for block in self.block_list.blocks if isinstance(block, PlateBlock)
        ]

        if len(plate_blocks) != 1:
            block_types = [block.BLOCK_TYPE for block in self.block_list.blocks]
            block_counts = {bt: block_types.count(bt) for bt in set(block_types)}
            error = f"expected exactly 1 plate block, got {block_counts}"
            raise AllotropeConversionError(error)

        return plate_blocks[0]

    @staticmethod
    def create(lines_reader: LinesReader) -> Data:
        return Data(block_list=BlockList.create(lines_reader))
