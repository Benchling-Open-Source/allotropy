from __future__ import annotations

from abc import ABC
from collections import defaultdict
from enum import Enum
from typing import Any, ClassVar, Optional

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.shared.components.plate_reader import (
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)
from allotropy.parsers.utils.values import assert_not_none, PrimitiveValue, try_int

START_LETTER_CODE = ord("A")
EXPORT_VERSION = "1.3"


class ReadType(Enum):
    ENDPOINT = "Endpoint"
    KINETIC = "Kinetic"
    SPECTRUM = "Spectrum"
    WELL_SCAN = "Well Scan"


class ExportFormat(Enum):
    TIME_FORMAT = "TimeFormat"
    PLATE_FORMAT = "PlateFormat"


class DataType(Enum):
    RAW = "Raw"
    REDUCED = "Reduced"


class Block:
    BLOCK_TYPE: ClassVar[str]

    def __init__(self, raw_lines: list[str]):
        self.raw_lines = raw_lines


class GroupBlock(Block):
    GROUP_PREFIX = "Group: "
    GROUP_COLUMN_PREFIX = "Group Column"
    BLOCK_TYPE = "Group"
    name: str
    group_data: list[str]

    def __init__(self, raw_lines: list[str]):
        super().__init__(raw_lines)
        self.name = raw_lines[0][len(self.GROUP_PREFIX) :]
        for i, line in enumerate(raw_lines):
            if line.startswith(self.GROUP_COLUMN_PREFIX):
                self.group_data = raw_lines[1 : i - 1]
        # TODO handle group data


# TODO do we need to do anything with these?
class NoteBlock(Block):
    BLOCK_TYPE = "Note"


def split_wavelengths(
    values: Optional[str], delimiter: str = " "
) -> Optional[list[int]]:
    if values is None:
        return None
    return [int(value) for value in values.split(delimiter)]


def get_well_coordinates(row_number: int, column_number: str) -> str:
    row_letters = ""
    while row_number > 0:
        row_number, remainder = divmod(row_number - 1, 26)
        row_letters = chr(START_LETTER_CODE + remainder) + row_letters
    return row_letters + str(column_number)


class WellData:
    values: list[Optional[float]]
    dimensions: list[Optional[PrimitiveValue]]
    wavelengths: list[Optional[int]]
    temperature: Optional[str]
    processed_data: list[float]

    def __init__(self) -> None:
        self.values = []
        self.dimensions = []
        self.wavelengths = []
        self.temperature = None
        self.processed_data = []

    def add_value(
        self,
        value: float,
        dimension: Optional[PrimitiveValue],
        temperature: Optional[str],
        wavelength: Optional[int],
    ) -> None:
        self.values.append(value)
        self.dimensions.append(dimension)
        self.wavelengths.append(wavelength)
        if temperature is not None:
            if self.temperature is not None and temperature != self.temperature:
                error = "Expected all measurements to have the same temperature"
                raise AllotropeConversionError(error)
            self.temperature = temperature

    @property
    def is_empty(self) -> bool:
        return not self.dimensions or not self.values


class PlateBlock(Block, ABC):
    BLOCK_TYPE = "Plate"
    CONCEPT: ClassVar[str]
    MANIFEST: ClassVar[str]
    READ_MODE: ClassVar[str]
    UNIT: ClassVar[str]
    DATA_TYPE_IDX: ClassVar[int]
    data_header: list[Optional[str]]
    data_type: Optional[str]
    export_format: Optional[str]
    name: Optional[str]
    kinetic_points: int
    num_columns: int
    num_rows: int
    num_wavelengths: Optional[int]
    num_wells: int
    pmt_gain: Optional[str]
    read_type: Optional[str]
    wavelengths: list[int]
    well_data: defaultdict[str, WellData]

    def __init__(
        self,
        header: list[Optional[str]],
        split_lines: list[list[Optional[str]]],
        raw_lines: list[str],
    ):
        super().__init__(raw_lines)
        self.parse_header(header)
        self.well_data = defaultdict(WellData)
        self.data_header = split_lines[1]
        data_lines = split_lines[2:]
        if self.export_format == ExportFormat.TIME_FORMAT.value:
            self._parse_time_format_data(data_lines)
        elif self.export_format == ExportFormat.PLATE_FORMAT.value:
            self._parse_plate_format_data(data_lines)
        else:
            error = f"unrecognized export format {self.export_format}"
            raise AllotropeConversionError(error)

    def _parse_reduced_plate_rows(
        self, reduced_data_rows: list[list[Optional[str]]]
    ) -> None:
        for i, row in enumerate(reduced_data_rows):
            for j, value in enumerate(row[2 : self.num_columns + 2]):
                if value is None:
                    continue
                col_number = assert_not_none(self.data_header[j + 2], "column number")
                well = get_well_coordinates(i + 1, col_number)
                self.well_data[well].processed_data.append(float(value))

    def _parse_reduced_columns(self, reduced_data_row: list[Optional[str]]) -> None:
        for i, value in enumerate(reduced_data_row[2:]):
            if value is None:
                continue
            well = assert_not_none(self.data_header[i + 2], "well")
            self.well_data[well].processed_data.append(float(value))

    def _add_data_point(
        self,
        well: str,
        value: str,
        data_key: Optional[str],
        temperature: Optional[str],
        wavelength: Optional[int],
    ) -> None:
        dimension = (
            wavelength if self.read_type == ReadType.ENDPOINT.value else data_key
        )
        self.well_data[well].add_value(
            value=float(value),
            dimension=dimension,
            temperature=temperature,
            wavelength=wavelength,
        )

    def _parse_time_format_data(self, data_lines: list[list[Optional[str]]]) -> None:
        if self.data_type == DataType.RAW.value:
            num_row_blocks = (
                self.num_wavelengths if self.num_wavelengths is not None else 1
            )
            for wavelength_index in range(num_row_blocks):
                start_index = wavelength_index * (self.kinetic_points + 1)
                wavelength_rows = data_lines[
                    start_index : start_index + self.kinetic_points
                ]
                for row in wavelength_rows:
                    for i, value in enumerate(row[2 : self.num_wells + 2]):
                        if value is None:
                            continue
                        well = assert_not_none(self.data_header[i + 2], "well")
                        self._add_data_point(
                            well,
                            value,
                            data_key=row[0],
                            temperature=row[1],
                            wavelength=self.get_wavelength(wavelength_index),
                        )
            if len(data_lines) > (self.kinetic_points + 1) * num_row_blocks:
                reduced_row = data_lines[-1][: self.num_wells + 2]
                self._parse_reduced_columns(reduced_row)
        elif self.data_type == DataType.REDUCED.value:
            reduced_row = data_lines[-1][: self.num_wells + 2]
            self._parse_reduced_columns(reduced_row)
        else:
            error = f"unrecognized data type {self.data_type}"
            raise AllotropeConversionError(error)

    def _parse_plate_format_data(self, data_lines: list[list[Optional[str]]]) -> None:
        end_raw_data_index = 0
        if self.data_type == DataType.RAW.value:
            for read_index in range(self.kinetic_points):
                start_index = read_index * (self.num_rows + 1)
                read_rows = data_lines[start_index : start_index + self.num_rows]
                data_key = read_rows[0][0]
                temperature = read_rows[0][1]
                for i, row in enumerate(read_rows):
                    wavelength_index = 0
                    num_row_blocks = (
                        self.num_wavelengths if self.num_wavelengths is not None else 1
                    )
                    for wavelength_index in range(num_row_blocks):
                        col_start_index = 2 + (
                            wavelength_index * (self.num_columns + 1)
                        )
                        for j, value in enumerate(
                            row[col_start_index : col_start_index + self.num_columns]
                        ):
                            if value is None:
                                continue
                            col_number = assert_not_none(
                                self.data_header[j + 2], "column number"
                            )
                            well = get_well_coordinates(i + 1, col_number)
                            self._add_data_point(
                                well,
                                value,
                                data_key=data_key,
                                temperature=temperature,
                                wavelength=self.get_wavelength(wavelength_index),
                            )
            end_raw_data_index = ((self.num_rows + 1) * self.kinetic_points) + 1
            reduced_data_rows = data_lines[end_raw_data_index:]
            if len(reduced_data_rows) == self.num_rows:
                self._parse_reduced_plate_rows(reduced_data_rows)
        elif self.data_type == DataType.REDUCED.value:
            reduced_data_rows = data_lines[end_raw_data_index:]
            self._parse_reduced_plate_rows(reduced_data_rows)
        else:
            error = f"unrecognized data type {self.data_type}"
            raise AllotropeConversionError(error)

    def parse_read_mode_header(self, header: list[Optional[str]]) -> None:
        raise NotImplementedError

    def parse_header(self, header: list[Optional[str]]) -> None:
        [
            _,  # Plate:
            self.name,
            self.export_version,
            self.export_format,
            self.read_type,
            _,  # Read mode
        ] = header[:6]
        if self.export_version != EXPORT_VERSION:
            error = f"Invalid export version {self.export_version}"
            raise AllotropeConversionError(error)

        [
            self.data_type,
            _,  # Pre-read, always FALSE
            kinetic_points,
            read_time_or_scan_pattern,
            read_interval_or_scan_density,
            self.start_wavelength,
            self.end_wavelength,
            self.wavelength_step,
            num_wavelengths,
            wavelengths_str,
            self.first_column,
            num_columns,
            num_wells,
        ] = header[self.DATA_TYPE_IDX : self.DATA_TYPE_IDX + 13]
        self.kinetic_points = assert_not_none(try_int(kinetic_points), "kinetic_points")
        self.num_columns = assert_not_none(try_int(num_columns), "num_columns")
        self.num_wells = assert_not_none(try_int(num_wells), "num_wells")
        self.num_wavelengths = try_int(num_wavelengths)
        self.wavelengths = split_wavelengths(wavelengths_str) or []
        self.parse_read_mode_header(header)

        if self.read_type == ReadType.KINETIC.value:
            self.read_time = read_time_or_scan_pattern
            self.read_interval = read_interval_or_scan_density
        elif self.read_type == ReadType.WELL_SCAN.value:
            self.scan_pattern = read_time_or_scan_pattern
            self.scan_density = read_interval_or_scan_density

    @property
    def is_single_wavelength(self) -> bool:
        return (
            self.read_type in {ReadType.SPECTRUM.value, ReadType.ENDPOINT.value}
            and len(self.wavelengths) == 1
        )

    @property
    def has_wavelength_dimension(self) -> bool:
        return (
            self.read_type not in {ReadType.SPECTRUM.value, ReadType.ENDPOINT.value}
            and len(self.wavelengths) > 1
        )

    def get_wavelength(self, wavelength_index: int) -> Optional[int]:
        if self.read_type == ReadType.SPECTRUM.value:
            return None
        else:
            return self.wavelengths[wavelength_index] if self.wavelengths else None

    def get_data_cube_dimensions(self) -> list[tuple[str, str, Optional[str]]]:
        dimensions: list[tuple[str, str, Optional[str]]] = []
        if self.read_type == ReadType.KINETIC.value:
            dimensions = [("double", "elapsed time", "s")]
        elif self.read_type == ReadType.WELL_SCAN.value:
            dimensions = [("int", "x", None)]
        elif self.read_type in {ReadType.SPECTRUM.value, ReadType.ENDPOINT.value}:
            dimensions = [("int", "wavelength", "nm")]
        else:
            error = f"cannot make data cube for {self.read_type}"
            raise AllotropeConversionError(error)
        if self.has_wavelength_dimension:
            dimensions.append(("int", "wavelength", "nm"))
        return dimensions

    def generate_sample_document(self, well: str) -> SampleDocument:
        return SampleDocument(well_location_identifier=well, plate_barcode=self.name)

    def generate_data_cube(self, well_data: WellData) -> TDatacube:
        dimension_data = [well_data.dimensions] + (
            [well_data.wavelengths] if self.has_wavelength_dimension else []
        )
        return TDatacube(
            cube_structure=TDatacubeStructure(
                [
                    TDatacubeComponent(FieldComponentDatatype(data_type), concept, unit)
                    for data_type, concept, unit in self.get_data_cube_dimensions()
                ],
                [
                    TDatacubeComponent(
                        FieldComponentDatatype("double"), self.CONCEPT, self.UNIT
                    )
                ],
            ),
            data=TDatacubeData(
                dimension_data,  # type: ignore[arg-type]
                [well_data.values],
            ),
        )

    def generate_processed_data_aggreate_document(
        self, well_data: WellData
    ) -> ProcessedDataAggregateDocument:
        return ProcessedDataAggregateDocument(
            [
                ProcessedDataDocumentItem(
                    val, data_processing_description="processed data"
                )
                for val in well_data.processed_data
            ]
        )

    def to_allotrope(self) -> Any:
        raise NotImplementedError
