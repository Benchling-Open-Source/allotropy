from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Any, Optional, Union

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    num_to_chars,
    try_float,
    try_float_or_nan,
    try_float_or_none,
    try_int,
    try_int_or_none,
    try_str_from_series,
    try_str_from_series_or_none,
)

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"
EXPORT_VERSION = "1.3"


def try_non_nan_float_or_none(value: Optional[str]) -> Optional[float]:
    number = try_float_or_none(value)
    return None if number is None or math.isnan(number) else number


def can_parse_as_float_non_nan(value: Any) -> bool:
    try:
        number = float(value)
    except ValueError:
        return False
    return not math.isnan(number)


def rm_df_columns(data: pd.DataFrame, pattern: str) -> pd.DataFrame:
    return data.drop(
        columns=[column for column in data.columns if re.match(pattern, column)]
    )


def try_str_from_series_multikey_or_none(
    data: pd.Series[Any],
    possible_keys: set[str],
) -> Optional[str]:
    for key in possible_keys:
        value = try_str_from_series_or_none(data, key)
        if value is not None:
            return value
    return None


def try_str_from_series_multikey(
    data: pd.Series[Any],
    possible_keys: set[str],
    msg: Optional[str] = None,
) -> str:
    return assert_not_none(
        try_str_from_series_multikey_or_none(data, possible_keys),
        msg=msg,
    )


NUM_WELLS_TO_PLATE_DIMENSIONS: dict[int, tuple[int, int]] = {
    6: (3, 2),
    12: (4, 3),
    24: (6, 4),
    48: (8, 6),
    96: (12, 8),
    384: (24, 16),
    1536: (48, 32),
}


def num_wells_to_n_columns(well_count: int) -> int:
    if dimensions := NUM_WELLS_TO_PLATE_DIMENSIONS.get(well_count):
        return dimensions[0]

    num_wells = ",".join(
        [str(num_wells) for num_wells in NUM_WELLS_TO_PLATE_DIMENSIONS]
    )
    msg = (
        f"Unknown number of wells '{well_count}'. Only accepted values are {num_wells}"
    )
    raise AllotropeConversionError(msg)


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
    BOTH = "Both"


class ScanPosition(Enum):
    BOTTOM = "Bottom"
    TOP = "Top"
    NONE = None


@dataclass(frozen=True)
class Block:
    block_type: str


@dataclass(frozen=True)
class GroupDataElementEntry:
    name: str
    value: float


@dataclass(frozen=True)
class GroupDataElement:
    sample: str
    position: str
    plate: str
    entries: list[GroupDataElementEntry]


@dataclass(frozen=True)
class GroupSampleData:
    identifier: str
    data_elements: list[GroupDataElement]
    aggregated_entries: list[GroupDataElementEntry]

    @staticmethod
    def create(data: pd.DataFrame) -> GroupSampleData:
        top_row = data.iloc[0]
        identifier = str(top_row["Sample"])
        data = rm_df_columns(data, r"^Sample$|^Standard Value|^R$|^Unnamed: \d+$")
        numeric_columns = [
            column
            for column in data.columns
            if can_parse_as_float_non_nan(top_row[column])
        ]

        normal_columns = []
        aggregated_columns = []
        for column in numeric_columns:
            if data[column].iloc[1:].isnull().all():
                aggregated_columns.append(column)
            else:
                normal_columns.append(column)

        return GroupSampleData(
            identifier=identifier,
            data_elements=[
                GroupDataElement(
                    sample=identifier,
                    position=try_str_from_series_multikey(
                        row,
                        {"Well", "Wells"},
                        msg="Unable to find well position in group data.",
                    ),
                    plate=try_str_from_series(row, "WellPlateName"),
                    entries=[
                        GroupDataElementEntry(
                            name=column_name,
                            value=try_float(row[column_name], column_name),
                        )
                        for column_name in normal_columns
                    ],
                )
                for _, row in data.iterrows()
            ],
            aggregated_entries=[
                GroupDataElementEntry(
                    name=column_name,
                    value=try_float(top_row[column_name], column_name),
                )
                for column_name in aggregated_columns
            ],
        )


@dataclass(frozen=True)
class GroupData:
    name: str
    sample_data: list[GroupSampleData]

    @staticmethod
    def create(reader: CsvReader) -> GroupData:
        name = assert_not_none(
            reader.pop(),
            msg="Unable to find group block name.",
        ).removeprefix("Group: ")

        data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t", header=0),
            msg="Unable to find group block data.",
        ).replace(r"^\s+$", None, regex=True)

        assert_not_none(
            data.get("Sample"),
            msg=f"Unable to find sample identifier column in group data {name}",
        )

        samples = data["Sample"].ffill()
        return GroupData(
            name=name,
            sample_data=[
                GroupSampleData.create(data.iloc[sample_entries.index])
                for _, sample_entries in samples.groupby(samples)
            ],
        )


@dataclass(frozen=True)
class GroupColumns:
    data: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> GroupColumns:
        data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t", header=0),
            msg="Unable to find group block columns.",
        )

        if "Formula Name" not in data:
            error = "Unable to find formula name in group block columns."
            raise AllotropeConversionError(error)

        if "Formula" not in data:
            error = "Unable to find formula in group block columns."
            raise AllotropeConversionError(error)

        return GroupColumns(
            data=dict(zip(data["Formula Name"], data["Formula"])),
        )


@dataclass(frozen=True)
class GroupSummaries:
    data: list[str]

    @staticmethod
    def create(reader: CsvReader) -> GroupSummaries:
        data = list(reader.pop_until_empty())
        reader.drop_empty()
        return GroupSummaries(data)


@dataclass(frozen=True)
class GroupBlock(Block):
    group_data: GroupData
    group_columns: GroupColumns
    group_summaries: GroupSummaries

    @staticmethod
    def create(reader: CsvReader) -> GroupBlock:
        return GroupBlock(
            block_type="Group",
            group_data=GroupData.create(reader),
            group_columns=GroupColumns.create(reader),
            group_summaries=GroupSummaries.create(reader),
        )


# TODO do we need to do anything with these?
@dataclass(frozen=True)
class NoteBlock(Block):
    pass


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
    scan_position: ScanPosition
    reads_per_well: float
    pmt_gain: Optional[str]
    num_rows: int
    excitation_wavelengths: Optional[list[int]]
    cutoff_filters: Optional[list[int]]


@dataclass
class DataElement:
    uuid: str
    plate: str
    temperature: Optional[float]
    wavelength: float
    position: str
    value: JsonFloat
    sample_id: Optional[str] = None

    @property
    def sample_identifier(self) -> str:
        return self.sample_id if self.sample_id else f"{self.plate} {self.position}"


@dataclass(frozen=True)
class ReducedDataElement:
    position: str
    value: float


@dataclass(frozen=True)
class PlateWavelengthData:
    wavelength: float
    data_elements: dict[str, DataElement]

    @staticmethod
    def create(
        plate_name: str,
        temperature: Optional[float],
        wavelength: float,
        df_data: pd.DataFrame,
    ) -> PlateWavelengthData:
        data = {
            f"{num_to_chars(row_idx)}{col}": value
            for row_idx, *row_data in df_data.itertuples()
            for col, value in zip(df_data.columns, row_data)
        }
        return PlateWavelengthData(
            wavelength,
            data_elements={
                str(position): DataElement(
                    uuid=random_uuid_str(),
                    plate=plate_name,
                    temperature=temperature,
                    wavelength=wavelength,
                    position=str(position),
                    value=try_float_or_nan(value),
                )
                for position, value in data.items()
            },
        )


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

        # use plate dimensions to determine how many rows of plate block to read
        dimensions = assert_not_none(
            NUM_WELLS_TO_PLATE_DIMENSIONS.get(header.num_wells),
            msg="unable to determine plate dimensions",
        )
        rows = dimensions[1]
        lines = []
        # read number of rows in plate
        for _row in range(rows):
            lines.append(reader.pop() or "")
        reader.drop_empty()

        # convert rows to df
        data = assert_not_none(
            reader.lines_as_df(lines=lines, sep="\t"),
            msg="unable to find data from plate block.",
        )
        data.columns = pd.Index(columns)

        # get temprature from the first column of the first row with value
        temperature = try_float_or_none(
            str(data.iloc[int(pd.to_numeric(data.first_valid_index())), 1])
        )

        return PlateKineticData(
            temperature=temperature,
            wavelength_data=PlateKineticData._get_wavelength_data(
                header.name,
                temperature,
                header,
                data.iloc[:, 2:],
            ),
        )

    @staticmethod
    def _get_wavelength_data(
        plate_name: str,
        temperature: Optional[float],
        header: PlateHeader,
        w_data: pd.DataFrame,
    ) -> list[PlateWavelengthData]:
        wavelength_data = []
        for idx in range(header.num_wavelengths):
            wavelength = header.wavelengths[idx]
            start = idx * (header.num_columns + 1)
            end = start + header.num_columns
            wavelength_data.append(
                PlateWavelengthData.create(
                    plate_name,
                    temperature,
                    wavelength,
                    w_data.iloc[:, start:end],
                )
            )
        return wavelength_data


@dataclass(frozen=True)
class PlateRawData:
    kinetic_data: list[PlateKineticData]

    @staticmethod
    def create(reader: CsvReader, header: PlateHeader) -> PlateRawData:
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
    data: list[ReducedDataElement]

    @staticmethod
    def create(reader: CsvReader, header: PlateHeader) -> PlateReducedData:
        raw_data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t", header=0),
            msg="Unable to find reduced data for plate block.",
        )

        start = 2
        df_data = raw_data.iloc[:, start : (start + header.num_columns)]

        reduced_data_elements = []
        for row, *data in df_data.itertuples():
            for col, str_value in zip(df_data.columns, data):
                value = try_non_nan_float_or_none(str_value)
                if value is not None:
                    reduced_data_elements.append(
                        ReducedDataElement(
                            position=f"{num_to_chars(row)}{col}",
                            value=value,
                        )
                    )
        return PlateReducedData(data=reduced_data_elements)


@dataclass(frozen=True)
class PlateData:
    raw_data: PlateRawData
    reduced_data: Optional[PlateReducedData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> PlateData:
        return PlateData(
            raw_data=PlateRawData.create(reader, header),
            reduced_data=(
                PlateReducedData.create(reader, header)
                if reader.current_line_exists()
                else None
            ),
        )

    def iter_data_elements(self, position: str) -> Iterator[DataElement]:
        for kinetic_data in self.raw_data.kinetic_data:
            for wavelength_data in kinetic_data.wavelength_data:
                yield wavelength_data.data_elements[position]


@dataclass(frozen=True)
class TimeKineticData:
    temperature: Optional[float]
    data_elements: dict[str, DataElement]

    @staticmethod
    def create(
        plate_name: str,
        wavelength: float,
        row: pd.Series[float],
    ) -> TimeKineticData:
        temperature = try_non_nan_float_or_none(str(row.iloc[1]))

        return TimeKineticData(
            temperature=temperature,
            data_elements={
                str(position): DataElement(
                    uuid=random_uuid_str(),
                    plate=plate_name,
                    temperature=temperature,
                    wavelength=wavelength,
                    position=str(position),
                    value=try_float_or_nan(str(value)),
                )
                for position, value in row.iloc[2:].items()
            },
        )


@dataclass(frozen=True)
class TimeWavelengthData:
    wavelength: float
    kinetic_data: list[TimeKineticData]

    @staticmethod
    def create(
        reader: CsvReader,
        plate_name: str,
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
            kinetic_data=[
                TimeKineticData.create(plate_name, wavelength, row)
                for _, row in data.iterrows()
            ],
        )


@dataclass(frozen=True)
class TimeRawData:
    wavelength_data: list[TimeWavelengthData]

    @staticmethod
    def create(reader: CsvReader, header: PlateHeader) -> TimeRawData:
        columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find data columns for time block raw data.",
        )

        return TimeRawData(
            wavelength_data=[
                TimeWavelengthData.create(
                    reader,
                    header.name,
                    wavelength,
                    columns,
                )
                for wavelength in header.wavelengths
            ]
        )


@dataclass(frozen=True)
class TimeReducedData:
    data: list[ReducedDataElement]

    @staticmethod
    def create(reader: CsvReader, header: PlateHeader) -> TimeReducedData:
        columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find columns for time block reduced data.",
        )
        data = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find reduced data from time block.",
        )
        data.index = pd.Index(columns)

        reduced_data_elements = []
        for pos, str_value in data[2 : header.num_wells + 2].items():
            value = try_non_nan_float_or_none(str_value)
            if value is not None:
                reduced_data_elements.append(
                    ReducedDataElement(
                        position=str(pos),
                        value=value,
                    )
                )
        return TimeReducedData(data=reduced_data_elements)


@dataclass(frozen=True)
class TimeData:
    raw_data: TimeRawData
    reduced_data: Optional[TimeReducedData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> TimeData:
        return TimeData(
            raw_data=TimeRawData.create(reader, header),
            reduced_data=(
                TimeReducedData.create(reader, header)
                if reader.current_line_exists()
                else None
            ),
        )

    def iter_data_elements(self, position: str) -> Iterator[DataElement]:
        for wavelength_data in self.raw_data.wavelength_data:
            for kinetic_data in wavelength_data.kinetic_data:
                yield kinetic_data.data_elements[position]


@dataclass(frozen=True)
class PlateBlock(ABC, Block):
    header: PlateHeader
    block_data: Union[PlateData, TimeData]

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
    @abstractmethod
    def get_plate_block_type() -> str:
        ...

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        raise NotImplementedError

    @classmethod
    def check_export_version(cls, export_version: str) -> None:
        if export_version != EXPORT_VERSION:
            error = f"Unsupported export version {export_version}; only {EXPORT_VERSION} is supported."
            raise AllotropeConversionError(error)

    @classmethod
    def check_read_type(cls, read_type: str) -> None:
        if read_type != ReadType.ENDPOINT.value:
            error = "Only Endpoint measurements can be processed at this time."
            raise AllotropeConversionError(error)

    @classmethod
    def check_data_type(cls, data_type: str) -> None:
        if data_type not in (DataType.RAW.value, DataType.BOTH.value):
            error = "The SoftMax Pro file is required to include either 'Raw' or 'Both' (Raw and Reduced) data for all plates"
            raise AllotropeConversionError(error)

    @classmethod
    def check_num_wavelengths(
        cls, wavelengths: list[float], num_wavelengths: int
    ) -> None:
        if len(wavelengths) != num_wavelengths:
            error = "Unable to find expected number of wavelength values."
            raise AllotropeConversionError(error)

    @classmethod
    def get_num_wavelengths(cls, num_wavelengths_raw: Optional[str]) -> int:
        return try_int_or_none(num_wavelengths_raw) or 1

    @classmethod
    def get_wavelengths(cls, wavelengths_str: Optional[str]) -> list[float]:
        return [
            try_float(wavelength, "wavelength")
            for wavelength in assert_not_none(
                wavelengths_str,
                msg="Unable to find wavelengths list.",
            ).split()
        ]

    def iter_wells(self) -> Iterator[str]:
        cols, rows = NUM_WELLS_TO_PLATE_DIMENSIONS[self.header.num_wells]
        for row in range(rows):
            for col in range(1, cols + 1):
                yield f"{num_to_chars(row)}{col}"

    def iter_data_elements(self, position: str) -> Iterator[DataElement]:
        yield from self.block_data.iter_data_elements(position)

    def iter_reduced_data(self) -> Iterator[ReducedDataElement]:
        if self.block_data.reduced_data:
            yield from self.block_data.reduced_data.data


@dataclass(frozen=True)
class FluorescencePlateBlock(PlateBlock):
    @staticmethod
    def get_plate_block_type() -> str:
        return "Fluorescence"

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            _,  # Read mode
            raw_scan_position,
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
            _,  # num_columns
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

        cls.check_export_version(export_version)
        cls.check_read_type(read_type)
        cls.check_data_type(data_type)

        num_wavelengths = cls.get_num_wavelengths(num_wavelengths_raw)
        wavelengths = cls.get_wavelengths(wavelengths_str)
        cls.check_num_wavelengths(wavelengths, num_wavelengths)

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

        # cutoff filters is an optional field in the input file
        # if present it contains a list of string numbers separated by spaces
        cutoff_filters = (
            [
                try_int(cutoff_filters, "cutoff filters")
                for cutoff_filters in cutoff_filters_str.split()
            ]
            if cutoff_filters_str is not None
            else None
        )

        # if there are cutoff filters check that the size match number of wavelengths
        if cutoff_filters is not None and len(cutoff_filters) != num_wavelengths:
            error = "Unable to find expected number of cutoff filter values."
            raise AllotropeConversionError(error)

        if raw_scan_position == "TRUE":
            scan_position = ScanPosition.BOTTOM
        elif raw_scan_position == "FALSE":
            scan_position = ScanPosition.TOP
        else:
            error = f"{raw_scan_position} is not a valid scan position."
            raise AllotropeConversionError(error)

        num_wells = try_int(num_wells_raw, "num_wells")
        num_columns = num_wells_to_n_columns(num_wells)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=num_wavelengths,
            wavelengths=wavelengths,
            num_columns=num_columns,
            num_wells=num_wells,
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
    @staticmethod
    def get_plate_block_type() -> str:
        return "Luminescence"

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
            _,  # num_columns,
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

        cls.check_export_version(export_version)
        cls.check_read_type(read_type)
        cls.check_data_type(data_type)

        num_wavelengths = cls.get_num_wavelengths(num_wavelengths_raw)
        wavelengths = cls.get_wavelengths(wavelengths_str)
        cls.check_num_wavelengths(wavelengths, num_wavelengths)

        num_wells = try_int(num_wells_raw, "num_wells")
        num_columns = num_wells_to_n_columns(num_wells)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=num_wavelengths,
            wavelengths=wavelengths,
            num_columns=num_columns,
            num_wells=num_wells,
            concept="luminescence",
            read_mode="Luminescence",
            unit="RLU",
            scan_position=ScanPosition.NONE,
            reads_per_well=try_int(reads_per_well, "reads_per_well"),
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=None,
            cutoff_filters=None,
        )


@dataclass(frozen=True)
class AbsorbancePlateBlock(PlateBlock):
    @staticmethod
    def get_plate_block_type() -> str:
        return "Absorbance"

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
            _,  # num_columns
            num_wells_raw,
            _,
            num_rows_raw,
        ] = header[:21]

        cls.check_export_version(export_version)
        cls.check_read_type(read_type)
        cls.check_data_type(data_type)

        num_wavelengths = cls.get_num_wavelengths(num_wavelengths_raw)
        wavelengths = cls.get_wavelengths(wavelengths_str)
        cls.check_num_wavelengths(wavelengths, num_wavelengths)

        num_wells = try_int(num_wells_raw, "num_wells")
        num_columns = num_wells_to_n_columns(num_wells)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=num_wavelengths,
            wavelengths=wavelengths,
            num_columns=num_columns,
            num_wells=num_wells,
            concept="absorbance",
            read_mode="Absorbance",
            unit="mAU",
            scan_position=ScanPosition.NONE,
            reads_per_well=0,
            pmt_gain=None,
            num_rows=try_int(num_rows_raw, "num_rows"),
            excitation_wavelengths=None,
            cutoff_filters=None,
        )


@dataclass(frozen=True)
class BlockList:
    plate_blocks: dict[str, PlateBlock]
    group_blocks: list[GroupBlock]

    @staticmethod
    def create(reader: CsvReader) -> BlockList:
        plate_blocks = {}
        group_blocks = []

        for sub_reader in BlockList._iter_blocks_reader(reader):
            if sub_reader.match("^Group"):
                if "WellPlateName" in assert_not_none(
                    sub_reader.get_line(sub_reader.current_line + 1),
                    msg="Unable to get columns from group block",
                ):
                    group_blocks.append(GroupBlock.create(sub_reader))
            elif sub_reader.match("^Plate"):
                header_series = PlateBlock.read_header(sub_reader)
                cls = PlateBlock.get_plate_block_cls(header_series)
                header = cls.parse_header(header_series)

                block_data: Union[TimeData, PlateData]
                if header.export_format == ExportFormat.TIME_FORMAT.value:
                    block_data = TimeData.create(sub_reader, header)
                elif header.export_format == ExportFormat.PLATE_FORMAT.value:
                    block_data = PlateData.create(sub_reader, header)
                else:
                    error = f"unrecognized export format {header.export_format}"
                    raise AllotropeConversionError(error)

                plate_blocks[header.name] = cls(
                    block_type="Plate",
                    header=header,
                    block_data=block_data,
                )
            elif not sub_reader.match("^Note"):
                error = f"Expected block '{sub_reader.get()}' to start with Group, Plate or Note."
                raise AllotropeConversionError(error)

        return BlockList(
            plate_blocks=plate_blocks,
            group_blocks=group_blocks,
        )

    @staticmethod
    def _get_n_blocks(reader: CsvReader) -> int:
        start_line = reader.pop() or ""
        if search_result := re.search(BLOCKS_LINE_REGEX, start_line):
            return int(search_result.group(1))
        msg = msg_for_error_on_unrecognized_value("start line", start_line)
        raise AllotropeConversionError(msg)

    @staticmethod
    def _iter_blocks_reader(reader: CsvReader) -> Iterator[CsvReader]:
        n_blocks = BlockList._get_n_blocks(reader)
        for _ in range(n_blocks):
            yield CsvReader(list(reader.pop_until(END_LINE_REGEX)))
            reader.pop()  # drop end line
            reader.drop_empty()


@dataclass(frozen=True)
class Data:
    block_list: BlockList

    @staticmethod
    def create(reader: CsvReader) -> Data:
        block_list = BlockList.create(reader)

        for group_block in block_list.group_blocks:
            for group_sample_data in group_block.group_data.sample_data:
                for group_data_element in group_sample_data.data_elements:
                    plate_block = block_list.plate_blocks[group_data_element.plate]
                    for data_element in plate_block.iter_data_elements(
                        group_data_element.position
                    ):
                        data_element.sample_id = group_data_element.sample

        return Data(block_list)
