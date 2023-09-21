# plate (repeated for N plates measured)
#     Plate information
#     Background information (optional)
#     Calculated results (optional)
#     Measured results (repeated for N measurements performed per plate)
# Basic assay information
# Protocol information
# Plate type
# Platemap (repeated for N plates measured)
# Calculations
# Auto export parameters
# Operations
# Labels
#     Filters (dependent on detection modality)
#     Mirrors (dependent on detection modality)
# Instrument
from __future__ import annotations

from dataclasses import dataclass
import logging
from re import search
from typing import Optional

import numpy as np
import pandas as pd

from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import assert_not_none, try_float


def df_to_series(df: pd.DataFrame) -> pd.Series:
    df.columns = df.iloc[0]  # type: ignore[assignment]
    return pd.Series(df.iloc[-1], index=df.columns)


def num_to_chars(n: int) -> str:
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return "" if n < 0 else num_to_chars(d - 1) + chr(m + 65)  # chr(65) = 'A'


@dataclass
class PlateInfo:
    number: str
    barcode: str
    emission_filter_id: str
    measurement_time: Optional[str]
    measured_height: Optional[float]
    chamber_temperature_at_start: Optional[float]

    @staticmethod
    def create(reader: LinesReader) -> Optional[PlateInfo]:
        data = reader.pop_csv_block("^Plate information")
        series = df_to_series(data).replace(np.nan, None)
        series.index = pd.Series(series.index).replace(np.nan, "empty label")  # type: ignore[assignment]

        plate_number = assert_not_none(
            str(series.get("Plate")), "Plate information: Plate"
        )
        barcode = (
            str(series.get("Barcode") or '=""').removeprefix('="').removesuffix('"')
            or f"Plate {plate_number}"
        )

        search_result = search("De=...", str(series.get("Measinfo", "")))
        if not search_result:
            msg = f"Unable to get emition filter id from plate {barcode}"
            raise Exception(msg)
        emission_filter_id = search_result.group().removeprefix("De=")

        measurement_time = str(series.get("Measurement date", ""))

        return PlateInfo(
            plate_number,
            barcode,
            emission_filter_id,
            measurement_time,
            try_float(str(series.get("Measured height"))),
            try_float(str(series.get("Chamber temperature at start"))),
        )


@dataclass
class Result:
    col: str
    row: str
    value: int

    @staticmethod
    def create(reader: LinesReader) -> list[Result]:
        if not reader.current_line_exists() or reader.match(
            "(^Plate information)|(^Basic assay information)"
        ):
            return []

        # Results may or may not have a title
        reader.pop_if_match("^Results")

        data = reader.pop_csv_block()
        series = (
            data.drop(0, axis=0).drop(0, axis=1) if data.iloc[1, 0] == "A" else data
        )
        rows, cols = series.shape
        series.index = [num_to_chars(i) for i in range(rows)]  # type: ignore[assignment]
        series.columns = [str(i).zfill(2) for i in range(1, cols + 1)]  # type: ignore[assignment]

        return [
            Result(col, row, int(series.loc[col, row]))
            for col, row in series.stack().index
        ]


@dataclass
class Plate:
    plate_info: PlateInfo
    results: list[Result]

    @staticmethod
    def create(reader: LinesReader) -> list[Plate]:
        plates: list[Plate] = []

        while True:
            if not reader.match("^Plate information"):
                break

            plate_info: Optional[PlateInfo] = None
            try:
                plate_info = PlateInfo.create(reader)
            except Exception as e:
                logging.warning(f"Failed to parse plate info with error: {e}")

            reader.drop_sections("^Background information|^Calculated results")

            results = Result.create(reader)

            if plate_info:
                plates.append(Plate(plate_info, results=results))

        return plates


@dataclass
class BasicAssayInfo:
    protocol_id: str
    assay_id: str

    @staticmethod
    def create(reader: LinesReader) -> BasicAssayInfo:
        reader.drop_until("^Basic assay information")
        data = reader.pop_csv_block("^Basic assay information").T
        data.iloc[0].replace(":.*", "", regex=True, inplace=True)
        series = df_to_series(data)
        return BasicAssayInfo(
            str(series.get("Protocol ID")),
            str(series.get("Assay ID")),
        )


@dataclass
class PlateType:
    number_of_wells: Optional[float] = None

    @staticmethod
    def create(reader: LinesReader) -> PlateType:
        reader.drop_until("^Plate type")
        data = reader.pop_csv_block("^Plate type").T
        return PlateType(
            try_float(str(df_to_series(data).get("Number of the wells in the plate")))
        )


def get_sample_role_type(encoding: str) -> SampleRoleType:
    # BL        blank               blank_role
    # CTL       control             control_sample_role
    # LB        lance_blank         blank_role
    # LC        lance_crosstalk     control_sample_role
    # LH        lance_high          control_sample_role
    # S         pl_sample           sample_role
    # STD       standard            standard_sample_role
    # -         undefined           <UNDEFINED>
    # UNK       unknown             unknown_sample_role
    # ZH        z_high              control_sample_role
    # ZL        z_low               control_sample_role
    sample_role_type_map = {
        "BL": SampleRoleType.blank_role,
        "CTL": SampleRoleType.control_sample_role,
        "LB": SampleRoleType.blank_role,
        "LC": SampleRoleType.control_sample_role,
        "LH": SampleRoleType.control_sample_role,
        "STD": SampleRoleType.standard_sample_role,
        "S": SampleRoleType.sample_role,
        "-": SampleRoleType.undefined_sample_role,
        "UNK": SampleRoleType.unknown_sample_role,
        "ZH": SampleRoleType.control_sample_role,
        "ZL": SampleRoleType.control_sample_role,
    }
    for pattern, value in sample_role_type_map.items():
        if encoding.startswith(pattern):
            return value

    msg = f"Unable to determine sample role type of plate map encoding {encoding}"
    raise ValueError(msg)


@dataclass
class PlateMap:
    plate_n: str
    group_n: str
    sample_role_type_mapping: dict[str, dict[str, SampleRoleType]]

    @staticmethod
    def create(reader: LinesReader) -> Optional[PlateMap]:
        if not reader.current_line_exists() or reader.match("^Calculations"):
            return None

        plate_n = assert_not_none(reader.pop(), "Platemap number").split(",")[-1]
        group_n = assert_not_none(reader.pop(), "Platemap group").split(",")[-1]

        data = reader.pop_csv_block().replace(" ", "", regex=True)

        reader.pop_data()  # drop type specification
        reader.drop_empty()

        series = (
            data.drop(0, axis=0).drop(0, axis=1) if data.iloc[1, 0] == "A" else data
        )
        rows, cols = series.shape
        series.index = [num_to_chars(i) for i in range(rows)]  # type: ignore[assignment]
        series.columns = [str(i).zfill(2) for i in range(1, cols + 1)]  # type: ignore[assignment]

        sample_role_type_mapping: dict[str, dict[str, SampleRoleType]] = {}
        for row, row_data in series.replace([np.nan, "''"], None).to_dict().items():
            col_mapping: dict[str, SampleRoleType] = {}
            for col, value in row_data.items():
                if value:
                    role_type = get_sample_role_type(str(value))
                    if role_type:
                        col_mapping[str(col)] = role_type
            if col_mapping:
                sample_role_type_mapping[str(row)] = col_mapping

        return PlateMap(plate_n, group_n, sample_role_type_mapping)

    def get_sample_role_type(self, col: str, row: str) -> SampleRoleType:
        try:
            return self.sample_role_type_mapping[row][col]
        except KeyError as e:
            msg = (
                f"Invalid plate map location for plate map {self.plate_n}: {col} {row}"
            )
            raise Exception(msg) from e


def create_plate_maps(reader: LinesReader) -> dict[str, PlateMap]:
    if reader.drop_until("^Platemap") is None:
        msg = "Unable to get plate map information"
        raise Exception(msg)

    reader.pop()  # remove title

    maps: dict[str, PlateMap] = {}
    while _map := PlateMap.create(reader):
        maps[_map.plate_n] = _map
    return maps


@dataclass
class Filter:
    name: str
    wavelength: float
    bandwidth: float

    @staticmethod
    def create(reader: LinesReader) -> Optional[Filter]:
        if not reader.current_line_exists() or reader.match(
            "(^Mirror modules)|(^Instrument:)"
        ):
            return None

        data = reader.pop_csv_block().T
        series = df_to_series(data)

        name = str(series.index[0])

        description = str(series.get("Description"))

        search_result = search("CWL=\\d*nm", description)
        if search_result is None:
            msg = f"Unable to find wavelength for filter {name}"
            raise Exception(msg)
        wavelength = float(
            search_result.group().removeprefix("CWL=").removesuffix("nm")
        )

        search_result = search("BW=\\d*nm", description)
        if search_result is None:
            msg = f"Unable to find bandwidth for filter {name}"
            raise Exception(msg)
        bandwidth = float(search_result.group().removeprefix("BW=").removesuffix("nm"))

        return Filter(name, wavelength, bandwidth)


def create_filters(reader: LinesReader) -> dict[str, Filter]:
    reader.drop_until("(^Filters:)|^Instrument:")

    if reader.match("^Instrument"):
        return {}

    reader.pop()  # remove title

    filters = {}
    while _filter := Filter.create(reader):
        filters[_filter.name] = _filter
    return filters


@dataclass
class Labels:
    label: str
    excitation_filter: Optional[Filter]
    emission_filters: dict[str, Optional[Filter]]
    scan_position_setting: Optional[ScanPositionSettingPlateReader] = None
    number_of_flashes: Optional[float] = None
    detector_gain_setting: Optional[str] = None

    @staticmethod
    def create(reader: LinesReader) -> Labels:
        reader.drop_until("^Labels")
        data = reader.pop_csv_block("^Labels").T
        series = df_to_series(data).replace(np.nan, None)

        filters = create_filters(reader)

        excitation_filter = filters.get(str(series.get("Exc. filter", "")))

        emission_filters = {
            "1st": filters.get(str(series.get("Ems. filter"))),
            "2nd": filters.get(str(series.get("2nd ems. filter"))),
        }
        filter_position_map = {
            "Bottom": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
            "Top": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
        }

        return Labels(
            series.index[0],
            excitation_filter,
            emission_filters,
            filter_position_map.get(str(series.get("Using of emission filter")), None),
            number_of_flashes=try_float(str(series.get("Number of flashes"))),
            detector_gain_setting=str(series.get("Reference AD gain")),
        )

    def get_emission_filter(self, id_val: str) -> Optional[Filter]:
        return self.emission_filters.get(id_val)


@dataclass
class Instrument:
    serial_number: str
    nickname: str

    @staticmethod
    def create(reader: LinesReader) -> Instrument:
        if reader.drop_until("^Instrument") is None:
            msg = "Unable to find instrument information"
            raise Exception(msg)

        reader.pop()  # remove title

        serial_number = assert_not_none(reader.pop(), "serial number").split(",")[-1]
        nickname = assert_not_none(reader.pop(), "nickname").split(",")[-1]

        return Instrument(serial_number, nickname)


@dataclass
class Data:
    plates: list[Plate]
    basic_assay_info: BasicAssayInfo
    number_of_wells: Optional[float]
    plate_maps: dict[str, PlateMap]
    labels: Labels
    instrument: Instrument

    @staticmethod
    def create(reader: LinesReader) -> Data:
        return Data(
            plates=Plate.create(reader),
            basic_assay_info=BasicAssayInfo.create(reader),
            number_of_wells=PlateType.create(reader).number_of_wells,
            plate_maps=create_plate_maps(reader),
            labels=Labels.create(reader),
            instrument=Instrument.create(reader),
        )
