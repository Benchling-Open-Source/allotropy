from __future__ import annotations

from abc import ABC
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    ErrorDocument,
    MeasurementType,
    ScanPositionSettingPlateReader,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    get_key_or_error,
)
from allotropy.parsers.constants import NEGATIVE_ZERO
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.pandas import SeriesData, set_columns
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    num_to_chars,
    try_float,
    try_float_or_none,
    try_int,
    try_int_or_none,
    try_non_nan_float_or_none,
)

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"
EXPORT_VERSION = "1.3"
VALID_NAN_VALUES = ("Masked", "Range?", "Error")


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


def time_to_seconds(time: str) -> float:
    """Transforms HH:MM:SS formatted time into seconds"""
    try:
        pt = datetime.strptime(time, "%H:%M:%S").astimezone()
    except ValueError as e:
        msg = "Bad time formatting, expected HH:MM:SS, got {time}"
        raise AllotropeConversionError(msg) from e

    return pt.hour * 3600 + pt.minute * 60 + pt.second


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


@dataclass
class GroupDataElement:
    sample: str
    positions: list[str]
    plate: str | None
    entries: list[GroupDataElementEntry]
    errors: list[ErrorDocument]
    custom_info: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GroupSampleData:
    identifier: str
    data_elements: list[GroupDataElement]

    @classmethod
    def create(cls, data: pd.DataFrame, calc_data_cols: list[str]) -> GroupSampleData:
        row_data = [SeriesData(row) for _, row in data.iterrows()]
        identifier = row_data[0][str, "Sample"]

        data_columns = list(
            data.columns.difference(["Sample", "Well", "Wells", "WellPlateName"])
        )

        data_elements: dict[str, list[GroupDataElement]] = {
            column: [] for column in data_columns
        }
        for row in row_data:
            row_results = cls._get_row_results(row, data_columns)
            position = row[str, ["Well", "Wells"]]
            plate = row.get(str, "WellPlateName", validate=SeriesData.NOT_NAN)
            for column in data_columns:
                if (column_result := row_results.get(column)) is not None:
                    # A GroupDataElement can either contain a calculated data (entry), or a
                    # custom_information element, if it is calculated data, it might also report an error
                    data_elements[column].append(
                        GroupDataElement(
                            sample=identifier,
                            positions=[position],
                            plate=plate,
                            # Entries are calculated data
                            entries=cls._get_entries(
                                column, column_result, calc_data_cols
                            ),
                            custom_info=(
                                {column: str(column_result)}
                                if column not in calc_data_cols
                                else {}
                            ),
                            errors=(
                                cls._get_errors(column, column_result, calc_data_cols)
                            ),
                        )
                    )
                elif data_elements[column]:
                    data_elements[column][-1].positions.append(position)

        return GroupSampleData(
            identifier=identifier,
            data_elements=[
                elem for elements in data_elements.values() for elem in elements
            ],
        )

    @classmethod
    def _get_errors(
        cls, column: str, result: float | str, calc_data_cols: list[str]
    ) -> list[ErrorDocument]:
        return (
            [ErrorDocument(str(result), column)]
            if column in calc_data_cols
            and (isinstance(result, str) or abs(result) == math.inf)
            else []
        )

    @classmethod
    def _get_entries(
        cls, column: str, result: float | str, calc_data_cols: list[str]
    ) -> list[GroupDataElementEntry]:
        if column not in calc_data_cols:
            return []
        return [
            GroupDataElementEntry(
                column,
                (
                    result
                    if isinstance(result, float) and abs(result) != math.inf
                    else NEGATIVE_ZERO
                ),
            )
        ]

    @classmethod
    def _get_row_results(
        cls, data_row: SeriesData, column_names: list[str]
    ) -> dict[str, float | str]:
        result: dict[str, float | str] = {}
        for column in column_names:
            value = data_row.get(float, column, validate=SeriesData.NOT_NAN)
            if value is not None:
                result[column] = value
            elif (str_val := data_row.get(str, column)) is not None:
                result[column] = str_val
        return result


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

        with pd.option_context("future.no_silent_downcasting", True):  # noqa: FBT003
            data = assert_not_none(
                reader.pop_csv_block_as_df(sep="\t", header=0),
                msg="Unable to find group block data.",
            ).replace(r"^\s+$", None, regex=True)
            # TODO: what to do with columns full of NaN values?
            # 1. Ignore them
            # 2. Add them to the list of calculated data columns
            # 3. Add them to the list of custom data columns
            # We are doing 1 for now, but we should check
            data = data.dropna(axis=1, how="all")

        assert_not_none(
            data.get("Sample"),
            msg=f"Unable to find sample identifier column in group data {name}",
        )

        calc_data_cols = GroupData.get_calculated_data_columns(data)

        samples = data["Sample"].ffill()
        try:
            sample_data = [
                GroupSampleData.create(data.iloc[sample_entries.index], calc_data_cols)
                for _, sample_entries in samples.groupby(samples)
            ]
        except ValueError as e:
            msg = f"Unable to read Group data format for group {name}."
            raise AllotropeConversionError(msg) from e
        return GroupData(name=name, sample_data=sample_data)

    @staticmethod
    def get_calculated_data_columns(data: pd.DataFrame) -> list[str]:
        # If the column has at least on numeric value, it is considered a numeric column (calculated data)
        # The VALID_NAN_VALUES are considered as valid values for the numeric columns.
        def is_numeric(scalar: Any) -> bool:
            return (
                try_non_nan_float_or_none(scalar) is not None
                or scalar in VALID_NAN_VALUES
            )

        calculated_data_columns = [
            column for column in data.columns if data[column].apply(is_numeric).any()
        ]
        return calculated_data_columns


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
            msg = "Unable to find 'Formula Name' in group block columns."
            raise AllotropeConversionError(msg)

        if "Formula" not in data:
            msg = "Unable to find 'Formula' in group block columns."
            raise AllotropeConversionError(msg)

        return GroupColumns(
            data=dict(zip(data["Formula Name"], data["Formula"], strict=True)),
        )


@dataclass(frozen=True)
class SummaryDataElement:
    name: str
    value: float
    description: str | None


@dataclass(frozen=True)
class GroupBlock(Block):
    group_data: GroupData
    group_columns: GroupColumns
    group_summaries_data: list[SummaryDataElement]

    @staticmethod
    def create(reader: CsvReader) -> GroupBlock:
        return GroupBlock(
            block_type="Group",
            group_data=GroupData.create(reader),
            group_columns=GroupColumns.create(reader),
            group_summaries_data=GroupBlock.create_summary_data(reader),
        )

    @staticmethod
    def create_summary_data(reader: CsvReader) -> list[SummaryDataElement]:
        data_elements = []
        for line in reader.pop_until_empty():
            if match := re.match(r"^([^\t]+)\t([^\t]*)\t([\d.]+)\t([^\t]+)", line):
                data_elements.append(
                    SummaryDataElement(
                        name=match.groups()[0],
                        value=try_float(match.groups()[2], "summary result"),
                        description=match.groups()[3],
                    )
                )
        return data_elements


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
    read_time: float | None
    read_interval: float | None
    scan_position: ScanPositionSettingPlateReader | None
    reads_per_well: float | None
    pmt_gain: str | None
    num_rows: int
    excitation_wavelengths: list[int] | None
    cutoff_filters: list[int] | None


@dataclass
class DataElement:
    uuid: str
    plate: str
    temperature: float | None
    wavelength: float
    position: str
    value: float | None
    error_document: list[ErrorDocument]
    custom_info: dict[str, str] = field(default_factory=dict)
    elapsed_time: list[float] = field(default_factory=list)
    kinetic_measures: list[float | None] = field(default_factory=list)
    sample_id: str | None = None
    group_id: str | None = None

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
        header: PlateHeader,
        temperature: float | None,
        elapsed_time: float | None,
        wavelength: float,
        df_data: pd.DataFrame,
    ) -> PlateWavelengthData:
        data = {
            f"{num_to_chars(row_idx)}{col}": raw_value
            for row_idx, *row_data in df_data.itertuples()
            for col, raw_value in zip(df_data.columns, row_data, strict=True)
        }
        data_elements = {}
        for position, raw_value in data.items():
            value = try_non_nan_float_or_none(raw_value)
            if value is None and elapsed_time is not None:
                msg = f"Missing kinetic measurement for well position {position} at {elapsed_time}s."
                raise AllotropeConversionError(msg)
            data_elements[str(position)] = DataElement(
                uuid=random_uuid_str(),
                plate=header.name,
                temperature=temperature,
                wavelength=wavelength,
                position=str(position),
                value=value,
                error_document=(
                    [ErrorDocument(str(raw_value), header.read_mode)]
                    if value is None
                    else []
                ),
                elapsed_time=[elapsed_time] if elapsed_time is not None else [],
                kinetic_measures=[value] if elapsed_time is not None else [],
            )

        return PlateWavelengthData(wavelength, data_elements)

    def update_kinetic_data_elements(
        self, elapsed_time: float, df_data: pd.DataFrame
    ) -> None:
        data = {
            f"{num_to_chars(row_idx)}{col}": try_non_nan_float_or_none(raw_value)
            for row_idx, *row_data in df_data.itertuples()
            for col, raw_value in zip(df_data.columns, row_data, strict=True)
        }
        for position, value in data.items():
            if value is None:
                msg = f"Missing kinetic measurement for well position {position} at {elapsed_time}s."
                raise AllotropeConversionError(msg)

            self.data_elements[position].elapsed_time.append(elapsed_time)
            self.data_elements[position].kinetic_measures.append(value)


@dataclass(frozen=True)
class RawData:
    wavelength_data: list[PlateWavelengthData]

    @staticmethod
    def get_measurement_section(
        reader: CsvReader, columns: pd.Series[str], rows: int
    ) -> pd.DataFrame:
        lines = []
        # read number of rows in plate section
        for i in range(rows):
            if not (line := reader.pop()):
                msg = f"Expected {rows} rows in measurement table, got {i}."
                raise AllotropeConversionError(msg)
            lines.append(line)
        reader.drop_empty()

        # convert rows to df
        data = assert_not_none(
            reader.lines_as_df(lines=lines, sep="\t"),
            msg="unable to find data from plate block.",
        )

        # Truncate columns Series to match the actual number of data columns
        if len(columns) >= data.shape[1]:
            columns = columns.iloc[: data.shape[1]]
        elif len(columns) < data.shape[1]:
            data = data.loc[:, : len(columns) - 1]

        set_columns(data, columns)
        return data


@dataclass(frozen=True)
class PlateRawData(RawData):
    @staticmethod
    def create(reader: CsvReader, header: PlateHeader) -> PlateRawData:

        columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find data columns for plate block raw data.",
        )

        # use plate dimensions to determine how many rows of plate block to read
        dimensions = assert_not_none(
            NUM_WELLS_TO_PLATE_DIMENSIONS.get(header.num_wells),
            msg="unable to determine plate dimensions",
        )
        rows = dimensions[1]
        data = RawData.get_measurement_section(reader, columns, rows)

        # get temperature and elapsed time (kinetic) from the first column of the first row with value
        first_row_idx = int(pd.to_numeric(data.first_valid_index()))
        temperature = try_non_nan_float_or_none(str(data.iloc[first_row_idx, 1]))
        elapsed_time = None
        if pd.notna(elapsed := data.iloc[first_row_idx, 0]):
            elapsed_time = time_to_seconds(str(elapsed))

        plate_raw_data = PlateRawData(
            wavelength_data=PlateRawData._get_wavelength_data(
                temperature,
                elapsed_time,
                header,
                data.iloc[:, 2:],
            )
        )

        if elapsed_time is not None and header.kinetic_points > 1:
            for _ in range(header.kinetic_points - 1):
                data = RawData.get_measurement_section(reader, columns, rows)

                elapsed_time = time_to_seconds(str(data.iloc[0, 0]))
                plate_raw_data._update_kinetic_data(
                    elapsed_time, header, data.iloc[:, 2:]
                )

        return plate_raw_data

    @staticmethod
    def _get_wavelength_data(
        temperature: float | None,
        elapsed_time: float | None,
        header: PlateHeader,
        w_data: pd.DataFrame,
    ) -> list[PlateWavelengthData]:
        wavelength_data = []
        for idx in range(header.num_wavelengths):
            start = idx * (header.num_columns + 1)
            end = start + header.num_columns
            wavelength_data.append(
                PlateWavelengthData.create(
                    header=header,
                    temperature=temperature,
                    elapsed_time=elapsed_time,
                    wavelength=header.wavelengths[idx],
                    df_data=w_data.iloc[:, start:end],
                )
            )
        return wavelength_data

    def _update_kinetic_data(
        self, elapsed_time: float, header: PlateHeader, w_data: pd.DataFrame
    ) -> None:
        for idx, plate_wavelength_data in enumerate(self.wavelength_data):
            start = idx * (header.num_columns + 1)
            end = start + header.num_columns
            plate_wavelength_data.update_kinetic_data_elements(
                elapsed_time, w_data.iloc[:, start:end]
            )


@dataclass(frozen=True)
class SpectrumRawPlateData(RawData):
    maximum_wavelength_signal: dict[str, float | None]

    @staticmethod
    def create(reader: CsvReader, header: PlateHeader) -> SpectrumRawPlateData:

        columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find data columns for plate block raw data.",
        )
        dimensions = assert_not_none(
            NUM_WELLS_TO_PLATE_DIMENSIONS.get(header.num_wells),
            msg="unable to determine plate dimensions",
        )
        rows = dimensions[1]
        wavelength_data: list[PlateWavelengthData] = []

        for wavelength in header.wavelengths:
            data = RawData.get_measurement_section(reader, columns, rows)
            first_row_idx = int(pd.to_numeric(data.first_valid_index()))
            temperature = try_non_nan_float_or_none(str(data.iloc[first_row_idx, 1]))
            wavelength_data.append(
                PlateWavelengthData.create(
                    header=header,
                    temperature=temperature,
                    elapsed_time=None,
                    wavelength=wavelength,
                    df_data=data.iloc[:, 2:],
                )
            )
        reader.pop()
        reader.drop_empty()
        max_wavelength_signal_data = RawData.get_measurement_section(
            reader, columns, rows
        ).iloc[:, 2:]
        signal_data = {
            f"{num_to_chars(row_idx)}{col}": try_float_or_none(str(raw_value))
            for row_idx, *row_data in max_wavelength_signal_data.itertuples()
            for col, raw_value in zip(
                max_wavelength_signal_data.columns, row_data, strict=True
            )
        }

        return SpectrumRawPlateData(
            wavelength_data=wavelength_data,
            maximum_wavelength_signal=signal_data,
        )


@dataclass(frozen=True)
class PlateReducedData:
    data: list[ReducedDataElement]

    @staticmethod
    def create(reader: CsvReader, header: PlateHeader) -> PlateReducedData:
        if header.read_type == ReadType.SPECTRUM.value:
            return PlateReducedData(data=[])

        raw_data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t", header=0),
            msg="Unable to find reduced data for plate block.",
        )

        start = 2
        df_data = raw_data.iloc[:, start : (start + header.num_columns)]

        reduced_data_elements = []
        for row, *data in df_data.itertuples():
            for col, str_value in zip(df_data.columns, data, strict=True):
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
    raw_data: PlateRawData | SpectrumRawPlateData
    reduced_data: PlateReducedData | None

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> PlateData:
        raw_data: PlateRawData | SpectrumRawPlateData = (
            SpectrumRawPlateData.create(reader, header)
            if header.read_type == ReadType.SPECTRUM.value
            else PlateRawData.create(reader, header)
        )
        return PlateData(
            raw_data=raw_data,
            reduced_data=(
                PlateReducedData.create(reader, header)
                if reader.current_line_exists()
                else None
            ),
        )

    def iter_data_elements(self, position: str) -> Iterator[DataElement]:
        for plate_wavelength_data in self.raw_data.wavelength_data:
            yield plate_wavelength_data.data_elements[position]

    def position_exists(self, position: str) -> bool:
        for plate_wavelength_data in self.raw_data.wavelength_data:
            if position in plate_wavelength_data.data_elements:
                return True
        return False


@dataclass(frozen=True)
class TimeMeasurementData:
    data_elements: dict[str, DataElement]

    @staticmethod
    def create(
        header: PlateHeader,
        wavelength: float,
        row: pd.Series[float],
    ) -> TimeMeasurementData:
        temperature = try_non_nan_float_or_none(str(row.iloc[1]))
        data_elements = {}

        for position, raw_value in row.iloc[2:].items():
            value = try_non_nan_float_or_none(raw_value)
            error_document = []
            if value is None:
                error_document.append(ErrorDocument(str(raw_value), header.read_mode))
            data_elements[str(position)] = DataElement(
                uuid=random_uuid_str(),
                plate=header.name,
                temperature=temperature,
                wavelength=wavelength,
                position=str(position),
                value=value,
                error_document=error_document,
            )

        return TimeMeasurementData(data_elements)


@dataclass(frozen=True)
class TimeWavelengthData:
    wavelength: float
    measurement_data: list[TimeMeasurementData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
        wavelength: float,
        columns: pd.Series[str],
    ) -> TimeWavelengthData:
        data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t"),
            msg="unable to find raw data from time block.",
        )
        set_columns(data, columns)

        return TimeWavelengthData(
            wavelength=wavelength,
            measurement_data=[
                TimeMeasurementData.create(header, wavelength, row)
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
                    header,
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
    reduced_data: TimeReducedData | None

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> TimeData:
        raw_data = None
        reduced_data = None

        # Read raw data if data_type is RAW or BOTH
        if header.data_type in (DataType.RAW.value, DataType.BOTH.value):
            raw_data = TimeRawData.create(reader, header)
        # For REDUCED only, create synthetic raw data with error message
        else:
            raw_data = TimeData._create_synthetic_raw_data(header)

        # Read reduced data if available, regardless of data_type (RAW can have reduced data!)
        if reader.current_line_exists():
            reduced_data = TimeReducedData.create(reader, header)

        return TimeData(
            raw_data=raw_data,
            reduced_data=reduced_data,
        )

    @staticmethod
    def _create_synthetic_raw_data(header: PlateHeader) -> TimeRawData:
        """Create synthetic raw data with error messages when only reduced data is available."""
        synthetic_wavelength_data = []

        for wavelength in header.wavelengths:
            # For each position in the plate, create a data element with an error document
            num_cols = header.num_columns
            num_rows = header.num_rows

            # Create synthetic data elements for all well positions
            data_elements = {}
            for row in range(1, num_rows + 1):
                for col in range(1, num_cols + 1):
                    position = f"{num_to_chars(row-1)}{col}"
                    data_elements[position] = DataElement(
                        uuid=random_uuid_str(),
                        plate=header.name,
                        temperature=None,
                        wavelength=wavelength,
                        position=position,
                        value=NEGATIVE_ZERO,
                        error_document=[
                            ErrorDocument("Not reported", header.read_mode)
                        ],
                        elapsed_time=[
                            0.0
                        ],  # Add a dummy value to ensure array is not empty
                        kinetic_measures=[
                            NEGATIVE_ZERO
                        ],  # Add a dummy value to ensure array is not empty
                    )

            # Create a single TimeMeasurementData with all positions
            measurement_data = [TimeMeasurementData(data_elements=data_elements)]

            # Add this wavelength data to our list
            synthetic_wavelength_data.append(
                TimeWavelengthData(
                    wavelength=wavelength,
                    measurement_data=measurement_data,
                )
            )

        # Create TimeRawData with our synthetic wavelength data
        return TimeRawData(wavelength_data=synthetic_wavelength_data)

    def iter_data_elements(self, position: str) -> Iterator[DataElement]:
        for time_wavelength_data in self.raw_data.wavelength_data:
            for measurement_data in time_wavelength_data.measurement_data:
                yield measurement_data.data_elements[position]

    def position_exists(self, position: str) -> bool:
        for time_wavelength_data in self.raw_data.wavelength_data:
            if any(
                position in measurement.data_elements
                for measurement in time_wavelength_data.measurement_data
            ):
                return True
        return False


@dataclass(frozen=True)
class PlateBlock(ABC, Block):
    header: PlateHeader
    block_data: PlateData | TimeData

    @staticmethod
    def read_header(reader: CsvReader) -> pd.Series[str]:
        raw_header_series = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="Unable to find plate block header.",
        )
        return raw_header_series.astype(str).replace("", None).str.strip()

    @staticmethod
    def get_plate_block_cls(header_series: pd.Series[str]) -> type[PlateBlock]:
        plate_block_cls: dict[str, type[PlateBlock]] = {
            "Absorbance": AbsorbancePlateBlock,
            "Fluorescence": FluorescencePlateBlock,
            "Luminescence": LuminescencePlateBlock,
        }
        read_mode = header_series[5]
        return get_key_or_error("read mode", read_mode, plate_block_cls)

    @property
    def measurement_type(self) -> MeasurementType:
        if self.header.read_type == ReadType.SPECTRUM.value:
            if self.header.concept == "absorbance":
                return MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_SPECTRUM
            elif self.header.concept == "fluorescence":
                return MeasurementType.EMISSION_FLUORESCENCE_CUBE_SPECTRUM
            elif self.header.concept == "luminescence":
                return MeasurementType.EMISSION_LUMINESCENCE_CUBE_SPECTRUM

        # Handle non-spectrum measurements
        read_mode_to_measurement_type = {
            "Absorbance": MeasurementType.ULTRAVIOLET_ABSORBANCE,
            "Fluorescence": MeasurementType.FLUORESCENCE,
            "Luminescence": MeasurementType.LUMINESCENCE,
            "Kinetic Absorbance": MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_DETECTOR,
            "Kinetic Fluorescence": MeasurementType.FLUORESCENCE_CUBE_DETECTOR,
            "Kinetic Luminescence": MeasurementType.LUMINESCENCE_CUBE_DETECTOR,
        }
        return read_mode_to_measurement_type[self.header.read_mode]

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        raise NotImplementedError

    @classmethod
    def check_export_version(cls, export_version: str) -> None:
        if export_version != EXPORT_VERSION:
            msg = f"Unsupported export version {export_version}; only {EXPORT_VERSION} is supported."
            raise AllotropeConversionError(msg)

    @classmethod
    def check_read_type(cls, read_type: str) -> None:
        if read_type not in (
            ReadType.ENDPOINT.value,
            ReadType.KINETIC.value,
            ReadType.SPECTRUM.value,
        ):
            msg = f"Only Endpoint, Spectrum or Kinetic measurements can be processed at this time, got: {read_type}"
            raise AllotropeConversionError(msg)

    @classmethod
    def get_read_mode(cls, read_type: str, read_mode_raw: str) -> str:
        return f"{'Kinetic ' if read_type == ReadType.KINETIC.value else ''}{read_mode_raw}"

    @classmethod
    def check_data_type(cls, data_type: str) -> None:
        if data_type not in (
            DataType.RAW.value,
            DataType.BOTH.value,
            DataType.REDUCED.value,
        ):
            msg = f"Unexpected data type: {data_type}, supported values are RAW, REDUCED, or BOTH."
            raise AllotropeConversionError(msg)

    @classmethod
    def check_num_wavelengths(
        cls, wavelengths: list[float], num_wavelengths: int
    ) -> None:
        if len(wavelengths) != num_wavelengths:
            msg = f"Unable to find expected number of wavelength values, expected {num_wavelengths}, found {len(wavelengths)}."
            raise AllotropeConversionError(msg)

    @classmethod
    def get_num_wavelengths(cls, num_wavelengths_raw: str | None) -> int:
        return try_int_or_none(num_wavelengths_raw) or 1

    @classmethod
    def get_wavelengths(cls, wavelengths_str: str | None) -> list[float]:
        if wavelengths_str is None:
            return []
        return [
            try_float(wavelength, "wavelength")
            for wavelength in wavelengths_str.split()
        ]

    @classmethod
    def get_wavelengths_from_start_end_step(
        cls, start: str, end: str, step: str
    ) -> list[float]:
        start_f = try_float(start, "start wavelength")
        end_f = try_float(end, "end wavelength")
        step_f = try_float(step, "wavelength step")

        return [
            start_f + step_f * i for i in range(int((end_f - start_f) / step_f) + 1)
        ]

    def iter_wells(self) -> Iterator[str]:
        cols, rows = NUM_WELLS_TO_PLATE_DIMENSIONS[self.header.num_wells]
        for row in range(rows):
            for col in range(1, cols + 1):
                position = f"{num_to_chars(row)}{col}"
                if self.block_data.position_exists(position):
                    yield position

    def iter_data_elements(self, position: str | list[str]) -> Iterator[DataElement]:
        position = [position] if isinstance(position, str) else position
        for p in position:
            yield from self.block_data.iter_data_elements(p)

    def iter_reduced_data(self) -> Iterator[ReducedDataElement]:
        if self.block_data.reduced_data:
            yield from self.block_data.reduced_data.data


@dataclass(frozen=True)
class FluorescencePlateBlock(PlateBlock):
    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            read_mode_raw,
            raw_scan_position,
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            read_time,  # read_time_or_scan_pattern
            read_interval,  # read_interval_or_scan_density
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
        if read_type == ReadType.SPECTRUM.value:
            msg = (
                "Spectrum read type is not currently supported for fluorescence plates."
            )
            raise AllotropeConversionError(msg)

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
            msg = f"Unable to find expected number of excitation values, expected {num_wavelengths}, found {len(excitation_wavelengths)}"
            raise AllotropeConversionError(msg)

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
            msg = f"Unable to find expected number of cutoff filter values, expected {num_wavelengths}, found {len(cutoff_filters)}."
            raise AllotropeConversionError(msg)

        if raw_scan_position == "TRUE":
            scan_position = (
                ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_
            )
        elif raw_scan_position == "FALSE":
            scan_position = (
                ScanPositionSettingPlateReader.top_scan_position__plate_reader_
            )
        else:
            msg = f"{raw_scan_position} is not a valid scan position, expected 'TRUE' or 'FALSE'."
            raise AllotropeConversionError(msg)

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
            read_mode=cls.get_read_mode(read_type, read_mode_raw),
            unit="RFU",
            read_time=try_float_or_none(read_time),
            read_interval=try_float_or_none(read_interval),
            scan_position=scan_position,
            reads_per_well=try_float(reads_per_well, "reads_per_well"),
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=excitation_wavelengths,
            cutoff_filters=cutoff_filters,
        )


@dataclass(frozen=True)
class LuminescencePlateBlock(PlateBlock):
    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            read_mode_raw,
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            read_time,  # read_time_or_scan_pattern
            read_interval,  # read_interval_or_scan_density
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
        if read_type == ReadType.SPECTRUM.value:
            msg = (
                "Spectrum read type is not currently supported for luminescence plates."
            )
            raise AllotropeConversionError(msg)

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
            read_mode=cls.get_read_mode(read_type, read_mode_raw),
            unit="RLU",
            read_time=try_float_or_none(read_time),
            read_interval=try_float_or_none(read_interval),
            scan_position=None,
            reads_per_well=try_int(reads_per_well, "reads_per_well"),
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=None,
            cutoff_filters=None,
        )


@dataclass(frozen=True)
class AbsorbancePlateBlock(PlateBlock):
    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            read_mode_raw,
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            read_time,  # read_time_or_scan_pattern
            read_interval,  # read_interval_or_scan_density
            start_wavelength,  # start_wavelength
            end_wavelength,  # end_wavelength
            wavelength_step,  # wavelength_step
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
        if read_type == ReadType.SPECTRUM.value:
            num_wavelengths = try_int(kinetic_points_raw, "kinetic_points")

        wavelengths = cls.get_wavelengths(wavelengths_str)
        if read_type == ReadType.SPECTRUM.value:
            wavelengths = cls.get_wavelengths_from_start_end_step(
                start_wavelength, end_wavelength, wavelength_step
            )
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
            read_mode=cls.get_read_mode(read_type, read_mode_raw),
            unit="mAU",
            read_time=try_float_or_none(read_time),
            read_interval=try_float_or_none(read_interval),
            scan_position=None,
            reads_per_well=None,
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
                group_blocks.append(GroupBlock.create(sub_reader))
            elif sub_reader.match("^Plate"):
                header_series = PlateBlock.read_header(sub_reader)
                plate_block_cls = PlateBlock.get_plate_block_cls(header_series)
                header = plate_block_cls.parse_header(header_series)

                export_format_to_data_format = {
                    ExportFormat.TIME_FORMAT.value: TimeData,
                    ExportFormat.PLATE_FORMAT.value: PlateData,
                }
                data_format: type[TimeData] | type[PlateData] = get_key_or_error(
                    "export format", header.export_format, export_format_to_data_format
                )
                block_data = data_format.create(sub_reader, header)

                if header.name in plate_blocks:
                    msg = f"Plate IDs between Plate Blocks must be unique. '{header.name}' block name is duplicated. See connector configuration guide for handling multiple Plate Blocks."
                    raise AllotropeConversionError(msg)
                plate_blocks[header.name] = plate_block_cls(
                    block_type="Plate",
                    header=header,
                    block_data=block_data,
                )
            elif not sub_reader.match("^Note"):
                msg = f"Expected block '{sub_reader.get()}' to start with Group, Plate or Note."
                raise AllotropeConversionError(msg)

        return BlockList(
            plate_blocks=plate_blocks,
            group_blocks=group_blocks,
        )

    @staticmethod
    def _get_n_blocks(reader: CsvReader) -> int:
        start_line = reader.pop() or ""
        if search_result := re.search(BLOCKS_LINE_REGEX, start_line):
            return int(search_result.group(1))
        msg = f"Unrecognized start line, expected a line starting with ##BLOCKS, got {start_line}"
        raise AllotropeConversionError(msg)

    @staticmethod
    def _iter_blocks_reader(reader: CsvReader) -> Iterator[CsvReader]:
        n_blocks = BlockList._get_n_blocks(reader)
        for _ in range(n_blocks):
            yield CsvReader(list(reader.pop_until(END_LINE_REGEX)))
            reader.pop()  # drop end line
            reader.drop_empty()


@dataclass(frozen=True)
class StructureData:
    block_list: BlockList
    date_last_saved: str | None

    @staticmethod
    def create(reader: CsvReader) -> StructureData:
        block_list = BlockList.create(reader)

        # update sample_id if it was reported in the group blocks and include errors from calculated data
        for group_block in block_list.group_blocks:
            for group_sample_data in group_block.group_data.sample_data:
                for group_data_element in group_sample_data.data_elements:
                    # For experiments with only one plate, it is assumed that all group blocks belong to it.
                    if len(block_list.plate_blocks) == 1:
                        group_data_element.plate = next(iter(block_list.plate_blocks))
                    elif group_data_element.plate is None:
                        # if the group data does not include the `WellPlateName` colum, and this is a multiplate
                        # experiment, there is no way at the moment to link the group data with a plate.
                        continue
                    plate_block = block_list.plate_blocks[group_data_element.plate]
                    is_spectrum = (
                        plate_block.header.read_type == ReadType.SPECTRUM.value
                    )
                    processed_positions = set()

                    for data_element in plate_block.iter_data_elements(
                        group_data_element.positions
                    ):
                        data_element.group_id = group_block.group_data.name
                        data_element.sample_id = group_data_element.sample

                        # For spectrum measurements, only add errors to the first DataElement per well
                        if (
                            not is_spectrum
                            or data_element.position not in processed_positions
                        ):
                            data_element.error_document += group_data_element.errors
                            if is_spectrum:
                                processed_positions.add(data_element.position)

                        data_element.custom_info.update(group_data_element.custom_info)

        return StructureData(
            block_list=block_list,
            date_last_saved=StructureData._get_date_last_saved(reader),
        )

    @classmethod
    def _get_date_last_saved(cls, reader: CsvReader) -> str | None:
        last_line = reader.pop()
        if last_line and (match := re.search(r"Date Last Saved: (.+)$", last_line)):
            return match.groups()[0]
        return None
