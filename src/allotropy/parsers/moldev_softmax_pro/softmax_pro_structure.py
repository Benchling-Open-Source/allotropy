from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Optional, Union

import pandas as pd

from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import (
    assert_not_none,
    num_to_chars,
    try_float,
    try_float_or_none,
    try_int,
    try_int_or_none,
)

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"
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


@dataclass(frozen=True)
class Block:
    block_type: str
    raw_lines: list[str]

    @staticmethod
    def create(reader: CsvReader) -> Block:
        block_cls_by_type: dict[str, type[Block]] = {
            "Group": GroupBlock,
            "Note": NoteBlock,
            "Plate": PlateBlock,
        }

        for key, cls in block_cls_by_type.items():
            if reader.match(f"^{key}"):
                return cls.create(reader)

        error = f"Expected block '{reader.get()}' to start with one of {sorted(block_cls_by_type.keys())}."
        raise AllotropeConversionError(error)


@dataclass(frozen=True)
class GroupBlock(Block):
    block_type: str
    name: str
    group_data: list[str]

    @staticmethod
    def create(reader: CsvReader) -> GroupBlock:
        return GroupBlock(
            block_type="Group",
            raw_lines=reader.lines,
            name=(reader.pop() or "").removeprefix("Group: "),
            group_data=list(reader.pop_until("Group Column")),
        )


# TODO do we need to do anything with these?
@dataclass(frozen=True)
class NoteBlock(Block):
    @staticmethod
    def create(reader: CsvReader) -> NoteBlock:
        return NoteBlock(block_type="Note", raw_lines=reader.lines)


@dataclass(frozen=True)
class PlateHeader:
    name: str
    export_version: str
    export_format: str
    read_type: str
    data_type: str
    kinetic_points: int
    num_wavelengths: int
    wavelengths: list[float]
    num_columns: int
    num_wells: int
    concept: str
    read_mode: str
    unit: str
    scan_position: Optional[str]
    reads_per_well: float
    pmt_gain: Optional[str]
    num_rows: int
    excitation_wavelengths: Optional[list[int]]
    cutoff_filters: Optional[list[int]]


@dataclass
class DataElement:
    temperature: Optional[float]
    wavelength: float
    position: str
    value: float


@dataclass(frozen=True)
class PlateWavelengthData:
    wavelength: float
    data: pd.Series[float]

    @staticmethod
    def create(wavelength: float, df_data: pd.DataFrame) -> PlateWavelengthData:
        rows, _ = df_data.shape
        df_data.index = pd.Index([num_to_chars(i) for i in range(rows)])

        data = df_data.stack()
        if isinstance(data, pd.DataFrame):
            error = "Unable to read plate wavelength data as pandas series."
            raise AllotropeConversionError(error)

        data.index = data.index.map("".join)
        return PlateWavelengthData(wavelength, data)


@dataclass(frozen=True)
class PlateKineticData:
    temperature: Optional[float]
    wavelength_data: list[PlateWavelengthData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
        columns: pd.Series[str],
    ) -> PlateKineticData:
        data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t"),
            msg="unable to find data from plate block.",
        )
        data.columns = pd.Index(columns)

        temperature = try_float_or_none(str(data.iloc[0, 1]))
        if temperature is not None and math.isnan(temperature):
            temperature = None

        return PlateKineticData(
            temperature=temperature,
            wavelength_data=list(
                PlateKineticData._iter_wavelength_data(
                    header, data.iloc[:, 2:].astype(float)
                )
            ),
        )

    @staticmethod
    def _iter_wavelength_data(
        header: PlateHeader, w_data: pd.DataFrame
    ) -> Iterator[PlateWavelengthData]:
        for idx in range(header.num_wavelengths):
            wavelength = header.wavelengths[idx]
            start = idx * (header.num_columns + 1)
            end = start + header.num_columns
            yield PlateWavelengthData.create(wavelength, w_data.iloc[:, start:end])


@dataclass(frozen=True)
class PlateRawData:
    kinetic_data: list[PlateKineticData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> Optional[PlateRawData]:
        if header.data_type == DataType.REDUCED.value:
            return None

        columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find data columns for plate block raw data.",
        )

        return PlateRawData(
            kinetic_data=[
                PlateKineticData.create(reader, header, columns)
                for _ in range(header.kinetic_points)
            ]
        )


@dataclass(frozen=True)
class PlateReducedData:
    data: pd.Series[float]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> Optional[PlateReducedData]:
        if not reader.current_line_exists():
            return None

        raw_data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t", header=0),
            msg="Unable to find reduced data for plate block.",
        )
        df_data = raw_data.iloc[:, 2 : header.num_columns + 2].astype(float)
        rows, _ = df_data.shape
        df_data.index = pd.Index([num_to_chars(i) for i in range(rows)])

        data = df_data.stack()
        if isinstance(data, pd.DataFrame):
            error = "Unable to read plate reduced data as pandas series."
            raise AllotropeConversionError(error)

        data.index = data.index.map("".join)
        return PlateReducedData(data)


@dataclass(frozen=True)
class PlateData:
    raw_data: Optional[PlateRawData]
    reduced_data: Optional[PlateReducedData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> PlateData:
        return PlateData(
            raw_data=PlateRawData.create(reader, header),
            reduced_data=PlateReducedData.create(reader, header),
        )

    def iter_wavelengths(self, position: str) -> Iterator[DataElement]:
        raw_data = assert_not_none(
            self.raw_data,
            msg="Unable to find plate block raw data.",
        )

        for kinetic_data in raw_data.kinetic_data:
            for wavelength_data in kinetic_data.wavelength_data:
                yield DataElement(
                    temperature=kinetic_data.temperature,
                    wavelength=wavelength_data.wavelength,
                    position=position,
                    value=wavelength_data.data[position],
                )


@dataclass(frozen=True)
class TimeKineticData:
    temperature: Optional[float]
    data: pd.Series[float]

    @staticmethod
    def create(row: pd.Series[float]) -> TimeKineticData:
        temperature = try_float_or_none(str(row.iloc[1]))
        if temperature is not None and math.isnan(temperature):
            temperature = None
        return TimeKineticData(
            temperature=temperature,
            data=row.iloc[2:].astype(float),
        )


@dataclass(frozen=True)
class TimeWavelengthData:
    wavelength: float
    kinetic_data: list[TimeKineticData]

    @staticmethod
    def create(
        reader: CsvReader,
        wavelength: float,
        columns: pd.Series[str],
    ) -> TimeWavelengthData:
        data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t"),
            msg="unable to find raw data from time block.",
        )
        data.columns = pd.Index(columns)
        return TimeWavelengthData(
            wavelength=wavelength,
            kinetic_data=[TimeKineticData.create(row) for _, row in data.iterrows()],
        )


@dataclass(frozen=True)
class TimeRawData:
    wavelength_data: list[TimeWavelengthData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> Optional[TimeRawData]:
        if header.data_type == DataType.REDUCED.value:
            return None

        columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find data columns for time block raw data.",
        )

        return TimeRawData(
            wavelength_data=[
                TimeWavelengthData.create(reader, header.wavelengths[idx], columns)
                for idx in range(header.num_wavelengths)
            ]
        )


@dataclass(frozen=True)
class TimeReducedData:
    columns: list[str]
    data: list[str]

    @staticmethod
    def create(reader: CsvReader) -> Optional[TimeReducedData]:
        if not reader.current_line_exists():
            return None

        _, _, *columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find columns for time block reduced data.",
        )
        _, _, *data = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find reduced data from time block.",
        )
        return TimeReducedData(columns, data)

    def iter_data(self) -> Iterator[tuple[str, float]]:
        for pos, value in zip(self.columns, self.data):
            yield pos, try_float(value, "time block reduced data element")


@dataclass(frozen=True)
class TimeData:
    raw_data: Optional[TimeRawData]
    reduced_data: Optional[TimeReducedData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> TimeData:
        return TimeData(
            raw_data=TimeRawData.create(reader, header),
            reduced_data=TimeReducedData.create(reader),
        )

    def iter_wavelengths(self, position: str) -> Iterator[DataElement]:
        raw_data = assert_not_none(
            self.raw_data,
            msg="Unable to find plate block raw data.",
        )

        for wavelength_data in raw_data.wavelength_data:
            for kinetic_data in wavelength_data.kinetic_data:
                yield DataElement(
                    temperature=kinetic_data.temperature,
                    wavelength=wavelength_data.wavelength,
                    position=position,
                    value=kinetic_data.data[position],
                )


@dataclass(frozen=True)
class PlateBlock(Block):
    block_type: str
    header: PlateHeader
    block_data: Union[PlateData, TimeData]
    plate_block_type: str = "Abstract"

    @staticmethod
    def create(reader: CsvReader) -> PlateBlock:
        header_series = PlateBlock.read_header(reader)
        cls = PlateBlock.get_plate_block_cls(header_series)
        header = cls.parse_header(header_series)

        if header.export_format == ExportFormat.TIME_FORMAT.value:
            return cls(
                block_type="Plate",
                raw_lines=reader.lines,
                header=header,
                block_data=TimeData.create(reader, header),
            )
        elif header.export_format == ExportFormat.PLATE_FORMAT.value:
            return cls(
                block_type="Plate",
                raw_lines=reader.lines,
                header=header,
                block_data=PlateData.create(reader, header),
            )
        else:
            error = f"unrecognized export format {header.export_format}"
            raise AllotropeConversionError(error)

    @staticmethod
    def read_header(reader: CsvReader) -> pd.Series[str]:
        raw_header_series = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="Unable to find plate block header.",
        )
        return raw_header_series.replace("", None).str.strip()

    @staticmethod
    def get_plate_block_cls(header_series: pd.Series[str]) -> type[PlateBlock]:
        plate_block_cls: dict[str, type[PlateBlock]] = {
            "Absorbance": AbsorbancePlateBlock,
            "Fluorescence": FluorescencePlateBlock,
            "Luminescence": LuminescencePlateBlock,
        }
        read_mode = header_series[5]
        cls = plate_block_cls.get(read_mode or "")
        if cls is None:
            msg = msg_for_error_on_unrecognized_value(
                "read mode", read_mode, plate_block_cls.keys()
            )
            raise AllotropeConversionError(msg)
        return cls

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        raise NotImplementedError

    def iter_wells(self) -> Iterator[str]:
        for row in range(self.header.num_rows):
            for col in range(1, self.header.num_columns + 1):
                yield f"{num_to_chars(row)}{col}"


@dataclass(frozen=True)
class FluorescencePlateBlock(PlateBlock):
    plate_block_type: str = "Fluorescence"

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            _,  # Read mode
            scan_position,
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            _,  # read_time_or_scan_pattern
            _,  # read_interval_or_scan_density
            _,  # start_wavelength
            _,  # end_wavelength
            _,  # wavelength_step
            num_wavelengths_raw,
            wavelengths_str,
            _,  # first_column
            num_columns_raw,
            num_wells_raw,
            excitation_wavelengths_str,
            _,  # cutoff
            cutoff_filters_str,
            _,  # sweep_wave
            _,  # sweep_wavelength
            reads_per_well,
            pmt_gain,
            _,  # start_integration_time
            _,  # end_integration_time
            _,  # first_row
            num_rows,
        ] = header[:31]

        if export_version != EXPORT_VERSION:
            error = f"Unsupported export version {export_version}; only {EXPORT_VERSION} is supported."
            raise AllotropeConversionError(error)

        if read_type != ReadType.ENDPOINT.value:
            error = "Only Endpoint measurements can be processed at this time."
            raise AllotropeConversionError(error)

        num_wavelengths = try_int_or_none(num_wavelengths_raw) or 1

        assert_not_none(
            wavelengths_str,
            msg="Unable to find wavelengths list.",
        )

        wavelengths = [
            try_float(wavelength, "wavelength")
            for wavelength in wavelengths_str.split()
        ]

        if len(wavelengths) != num_wavelengths:
            error = "Unable to find expected number of wavelength values."
            raise AllotropeConversionError(error)

        assert_not_none(
            excitation_wavelengths_str,
            msg="Unable to find excitation wavelengths.",
        )

        excitation_wavelengths = [
            try_int(excitation_wavelength, "excitation wavelengths")
            for excitation_wavelength in excitation_wavelengths_str.split()
        ]

        if len(excitation_wavelengths) != num_wavelengths:
            error = "Unable to find expected number of excitation values."
            raise AllotropeConversionError(error)

        cutoff_filters = (
            [
                try_int(cutoff_filters, "cutoff filters")
                for cutoff_filters in cutoff_filters_str.split()
            ]
            if cutoff_filters_str is not None
            else None
        )

        if cutoff_filters is not None and len(cutoff_filters) != num_wavelengths:
            error = "Unable to find expected number of cutoff filter values."
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=num_wavelengths,
            wavelengths=wavelengths,
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="fluorescence",
            read_mode="Fluorescence",
            unit="RFU",
            scan_position=scan_position,
            reads_per_well=try_float(reads_per_well, "reads_per_well"),
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=excitation_wavelengths,
            cutoff_filters=cutoff_filters,
        )


@dataclass(frozen=True)
class LuminescencePlateBlock(PlateBlock):
    plate_block_type: str = "Luminescence"

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            _,  # Read mode
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            _,  # read_time_or_scan_pattern
            _,  # read_interval_or_scan_density
            _,  # start_wavelength
            _,  # end_wavelength
            _,  # wavelength_step
            num_wavelengths_raw,
            wavelengths_str,
            _,  # first_column
            num_columns_raw,
            num_wells_raw,
            _,  # excitation_wavelengths_str
            _,  # cutoff
            _,  # cutoff_filters_str,
            _,  # sweep_wave
            _,  # sweep_wavelength
            reads_per_well,
            pmt_gain,
            _,  # start_integration_time
            _,  # end_integration_time
            _,  # first_row
            num_rows,
        ] = header[:30]

        if export_version != EXPORT_VERSION:
            error = f"Invalid export version {export_version}"
            raise AllotropeConversionError(error)

        if read_type != ReadType.ENDPOINT.value:
            error = "Only Endpoint measurements can be processed at this time."
            raise AllotropeConversionError(error)

        num_wavelengths = try_int_or_none(num_wavelengths_raw) or 1

        assert_not_none(
            wavelengths_str,
            msg="Unable to find wavelengths list.",
        )

        wavelengths = [
            try_float(wavelength, "wavelength")
            for wavelength in wavelengths_str.split()
        ]

        if len(wavelengths) != num_wavelengths:
            error = "Unable to find expected number of wavelength values."
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=num_wavelengths,
            wavelengths=wavelengths,
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="luminescence",
            read_mode="Luminescence",
            unit="RLU",
            scan_position=None,
            reads_per_well=try_int(reads_per_well, "reads_per_well"),
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=None,
            cutoff_filters=None,
        )


@dataclass(frozen=True)
class AbsorbancePlateBlock(PlateBlock):
    plate_block_type: str = "Absorbance"

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            _,  # Read mode
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            _,  # read_time_or_scan_pattern
            _,  # read_interval_or_scan_density
            _,  # start_wavelength
            _,  # end_wavelength
            _,  # wavelength_step
            num_wavelengths_raw,
            wavelengths_str,
            _,  # first_column
            num_columns_raw,
            num_wells_raw,
            _,
            num_rows_raw,
        ] = header[:21]

        if export_version != EXPORT_VERSION:
            error = f"Invalid export version {export_version}"
            raise AllotropeConversionError(error)

        if read_type != ReadType.ENDPOINT.value:
            error = "Only Endpoint measurements can be processed at this time."
            raise AllotropeConversionError(error)

        num_wavelengths = try_int_or_none(num_wavelengths_raw) or 1

        assert_not_none(
            wavelengths_str,
            msg="Unable to find wavelengths list.",
        )

        wavelengths = [
            try_float(wavelength, "wavelength")
            for wavelength in wavelengths_str.split()
        ]

        if len(wavelengths) != num_wavelengths:
            error = "Unable to find expected number of wavelength values."
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=num_wavelengths,
            wavelengths=wavelengths,
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="absorbance",
            read_mode="Absorbance",
            unit="mAU",
            scan_position=None,
            reads_per_well=0,
            pmt_gain=None,
            num_rows=try_int(num_rows_raw, "num_rows"),
            excitation_wavelengths=None,
            cutoff_filters=None,
        )


@dataclass(frozen=True)
class BlockList:
    blocks: list[Block]

    @staticmethod
    def create(reader: CsvReader) -> BlockList:
        return BlockList(
            blocks=[Block.create(block) for block in BlockList._iter_blocks(reader)]
        )

    @staticmethod
    def _get_n_blocks(reader: CsvReader) -> int:
        start_line = reader.pop() or ""
        if search_result := re.search(BLOCKS_LINE_REGEX, start_line):
            return int(search_result.group(1))
        msg = msg_for_error_on_unrecognized_value("start line", start_line)
        raise AllotropeConversionError(msg)

    @staticmethod
    def _iter_blocks(reader: CsvReader) -> Iterator[CsvReader]:
        n_blocks = BlockList._get_n_blocks(reader)
        for _ in range(n_blocks):
            yield CsvReader(list(reader.pop_until(END_LINE_REGEX)))
            reader.pop()  # drop end line
            reader.drop_empty()


@dataclass(frozen=True)
class Data:
    block_list: BlockList

    def get_plate_block(self) -> list[PlateBlock]:
        return [
            block for block in self.block_list.blocks if isinstance(block, PlateBlock)
        ]

    @staticmethod
    def create(reader: CsvReader) -> Data:
        return Data(block_list=BlockList.create(reader))
