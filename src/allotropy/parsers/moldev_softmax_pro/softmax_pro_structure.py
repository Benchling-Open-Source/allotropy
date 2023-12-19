from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
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
    PrimitiveValue,
    str_or_none,
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


@dataclass
class WellData:
    values: list[Optional[float]]
    dimensions: list[Optional[PrimitiveValue]]
    wavelengths: list[Optional[int]]
    temperature: Optional[float]
    processed_data: list[float]

    @staticmethod
    def create() -> WellData:
        return WellData(
            values=[],
            dimensions=[],
            wavelengths=[],
            temperature=None,
            processed_data=[],
        )

    def add_value(
        self,
        value: float,
        dimension: Optional[PrimitiveValue],
        temperature: Optional[float],
        wavelength: Optional[int],
    ) -> None:
        self.values.append(value)
        self.dimensions.append(dimension)
        self.wavelengths.append(wavelength)
        if temperature is not None:
            if self.temperature is not None and temperature != self.temperature:
                error = f"Expected all measurements to have the same temperature, but two have differing values of {self.temperature} and {temperature}."
                raise AllotropeConversionError(error)
            self.temperature = temperature

    @property
    def is_empty(self) -> bool:
        return not self.dimensions or not self.values


@dataclass(frozen=True)
class PlateHeader:
    name: str
    export_version: str
    export_format: str
    read_type: str
    data_type: str
    kinetic_points: int
    num_wavelengths: int
    wavelengths: list[int]
    num_columns: int
    num_wells: int
    concept: str
    read_mode: str
    unit: str
    scan_position: Optional[str]
    reads_per_well: Optional[int]
    pmt_gain: Optional[str]
    num_rows: int
    excitation_wavelengths: Optional[list[int]]
    cutoff_filters: Optional[list[int]]


@dataclass
class DataElement:
    temperature: Optional[float]
    wavelength: Optional[int]
    position: str
    value: float


@dataclass(frozen=True)
class PlateWavelengthData:
    wavelength: Optional[int]
    data: pd.Series[float]

    @staticmethod
    def create(wavelength: Optional[int], df_data: pd.DataFrame) -> PlateWavelengthData:
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
    data_key: Optional[str]
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

        raw_data_key = data.iloc[0, 0]
        raw_temperature = data.iloc[0, 1]

        return PlateKineticData(
            data_key=str_or_none(raw_data_key),
            temperature=try_float_or_none(str(raw_temperature)),
            wavelength_data=list(
                PlateKineticData._iter_wavelength_data(header, data.iloc[:, 2:])
            ),
        )

    @staticmethod
    def _iter_wavelength_data(
        header: PlateHeader, w_data: pd.DataFrame
    ) -> Iterator[PlateWavelengthData]:
        for idx in range(header.num_wavelengths):
            wavelength = (
                header.wavelengths[idx]
                if header.read_type != ReadType.SPECTRUM.value
                else None
            )
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
        df_data = raw_data.iloc[:, 2 : header.num_columns + 2]
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
    data_key: str
    temperature: float
    data: pd.Series[float]

    @staticmethod
    def create(row: pd.Series[float]) -> TimeKineticData:
        return TimeKineticData(
            data_key=str(int(row.iloc[0])),
            temperature=row.iloc[1],
            data=row.iloc[2:],
        )


@dataclass(frozen=True)
class TimeWavelengthData:
    wavelength: Optional[int]
    kinetic_data: list[TimeKineticData]

    @staticmethod
    def create(wavelength: Optional[int], data: pd.DataFrame) -> TimeWavelengthData:
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
        data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t"),
            msg="unable to find raw data from time block.",
        )
        data.columns = pd.Index(columns)
        return TimeRawData(
            wavelength_data=list(TimeRawData._iter_wavelength_data(header, data)),
        )

    @staticmethod
    def _iter_wavelength_data(
        header: PlateHeader, data: pd.DataFrame
    ) -> Iterator[TimeWavelengthData]:
        for idx in range(header.num_wavelengths):
            wavelength = (
                header.wavelengths[idx]
                if header.read_type != ReadType.SPECTRUM.value
                else None
            )
            start = idx * (header.kinetic_points + 1)
            end = start + header.kinetic_points
            yield TimeWavelengthData.create(wavelength, data.iloc[start:end, :])


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
    well_data: defaultdict[str, WellData]
    block_data: Union[PlateData, TimeData]
    plate_block_type: str = "Abstract"

    @staticmethod
    def create(reader: CsvReader) -> PlateBlock:
        header_series = PlateBlock.read_header(reader)
        cls = PlateBlock.get_plate_block_cls(header_series)
        header = cls.parse_header(header_series)
        well_data: defaultdict[str, WellData] = defaultdict(WellData.create)

        if header.export_format == ExportFormat.TIME_FORMAT.value:
            time_data = TimeData.create(reader, header)
            PlateBlock._parse_time_format_data(
                header,
                well_data,
                time_data,
            )
            return cls(
                block_type="Plate",
                raw_lines=reader.lines,
                header=header,
                well_data=well_data,
                block_data=time_data,
            )
        elif header.export_format == ExportFormat.PLATE_FORMAT.value:
            plate_data = PlateData.create(reader, header)
            PlateBlock._parse_plate_format_data(
                header,
                well_data,
                plate_data,
            )
            return cls(
                block_type="Plate",
                raw_lines=reader.lines,
                header=header,
                well_data=well_data,
                block_data=plate_data,
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

    @staticmethod
    def _add_data_point(
        header: PlateHeader,
        well_data: defaultdict[str, WellData],
        well: str,
        value: float,
        data_key: Optional[str],
        temperature: Optional[float],
        wavelength: Optional[int],
    ) -> None:
        dimension = (
            wavelength if header.read_type == ReadType.ENDPOINT.value else data_key
        )
        well_data[well].add_value(
            value=value,
            dimension=dimension,
            temperature=temperature,
            wavelength=wavelength,
        )

    @staticmethod
    def _parse_time_format_data(
        header: PlateHeader,
        well_data: defaultdict[str, WellData],
        time_data: TimeData,
    ) -> None:
        if header.data_type == DataType.RAW.value:
            raw_data = assert_not_none(
                time_data.raw_data,
                msg="Unable to find plate block raw data.",
            )
            for wavelength_data in raw_data.wavelength_data:
                for kinetic_data in wavelength_data.kinetic_data:
                    for pos, val in kinetic_data.data.items():
                        PlateBlock._add_data_point(
                            header,
                            well_data,
                            str(pos),
                            val,
                            data_key=kinetic_data.data_key,
                            temperature=kinetic_data.temperature,
                            wavelength=wavelength_data.wavelength,
                        )
            if time_data.reduced_data:
                for pos, val in time_data.reduced_data.iter_data():
                    well_data[pos].processed_data.append(val)
        elif header.data_type == DataType.REDUCED.value:
            reduced_data = assert_not_none(
                time_data.reduced_data,
                msg="Unable to find plate block reduced data.",
            )
            for pos, val in reduced_data.iter_data():
                well_data[pos].processed_data.append(val)
        else:
            msg = msg_for_error_on_unrecognized_value(
                "data type", header.data_type, DataType._member_names_
            )
            raise AllotropeConversionError(msg)

    @staticmethod
    def _parse_plate_format_data(
        header: PlateHeader,
        well_data: defaultdict[str, WellData],
        plate_data: PlateData,
    ) -> None:
        if header.data_type == DataType.RAW.value:
            raw_data = assert_not_none(
                plate_data.raw_data,
                msg="Unable to find plate block raw data.",
            )
            for kinetic_data in raw_data.kinetic_data:
                for wavelength_data in kinetic_data.wavelength_data:
                    for pos, value in wavelength_data.data.items():
                        PlateBlock._add_data_point(
                            header,
                            well_data,
                            str(pos),
                            value,
                            data_key=kinetic_data.data_key,
                            temperature=kinetic_data.temperature,
                            wavelength=wavelength_data.wavelength,
                        )
            if plate_data.reduced_data:
                for pos, value in plate_data.reduced_data.data.items():
                    well_data[str(pos)].processed_data.append(value)
        elif header.data_type == DataType.REDUCED.value:
            reduced_data = assert_not_none(
                plate_data.reduced_data,
                msg="Unable to find plate block reduced data.",
            )
            for pos, value in reduced_data.data.items():
                well_data[str(pos)].processed_data.append(value)
        else:
            msg = msg_for_error_on_unrecognized_value(
                "data type", header.data_type, DataType._member_names_
            )
            raise AllotropeConversionError(msg)

    @staticmethod
    def split_wavelengths(values: Optional[str]) -> Optional[list[int]]:
        return None if values is None else [int(v) for v in values.split()]

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        raise NotImplementedError

    def iter_wells(self) -> Iterator[str]:
        for row in range(self.header.num_rows):
            for col in range(1, self.header.num_columns + 1):
                yield f"{num_to_chars(row)}{col}"

    @property
    def is_single_wavelength(self) -> bool:
        return (
            self.header.read_type in {ReadType.SPECTRUM.value, ReadType.ENDPOINT.value}
            and len(self.header.wavelengths) == 1
        )

    @property
    def has_wavelength_dimension(self) -> bool:
        return (
            self.header.read_type
            not in {ReadType.SPECTRUM.value, ReadType.ENDPOINT.value}
            and len(self.header.wavelengths) > 1
        )


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

        if read_type != ReadType.ENDPOINT:
            error = f"Only Endpoint measurements can be processed at this time."
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=try_int_or_none(num_wavelengths_raw) or 1,
            wavelengths=PlateBlock.split_wavelengths(wavelengths_str) or [],
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="fluorescence",
            read_mode="Fluorescence",
            unit="RFU",
            scan_position=scan_position,
            reads_per_well=try_int(reads_per_well, "reads_per_well"),
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=PlateBlock.split_wavelengths(
                excitation_wavelengths_str
            ),
            cutoff_filters=PlateBlock.split_wavelengths(cutoff_filters_str),
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
        ] = header[:30]

        if export_version != EXPORT_VERSION:
            error = f"Invalid export version {export_version}"
            raise AllotropeConversionError(error)

        if read_type != ReadType.ENDPOINT:
            error = f"Only Endpoint measurements can be processed at this time."
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=try_int_or_none(num_wavelengths_raw) or 1,
            wavelengths=PlateBlock.split_wavelengths(wavelengths_str) or [],
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="luminescence",
            read_mode="Luminescence",
            unit="RLU",
            scan_position=None,
            reads_per_well=try_int(reads_per_well, "reads_per_well"),
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=PlateBlock.split_wavelengths(
                excitation_wavelengths_str
            ),
            cutoff_filters=PlateBlock.split_wavelengths(cutoff_filters_str),
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

        if read_type != ReadType.ENDPOINT:
            error = f"Only Endpoint measurements can be processed at this time."
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=try_int_or_none(num_wavelengths_raw) or 1,
            wavelengths=PlateBlock.split_wavelengths(wavelengths_str) or [],
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="absorbance",
            read_mode="Absorbance",
            unit="mAU",
            scan_position=None,
            reads_per_well=None,
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

    def get_plate_block(self) -> PlateBlock:
        plate_blocks = [
            block for block in self.block_list.blocks if isinstance(block, PlateBlock)
        ]

        if len(plate_blocks) != 1:
            block_types = [block.block_type for block in self.block_list.blocks]
            block_counts = {bt: block_types.count(bt) for bt in set(block_types)}
            error = f"Expected exactly 1 plate block; got {block_counts}."
            raise AllotropeConversionError(error)

        return plate_blocks[0]

    @staticmethod
    def create(reader: CsvReader) -> Data:
        return Data(block_list=BlockList.create(reader))
