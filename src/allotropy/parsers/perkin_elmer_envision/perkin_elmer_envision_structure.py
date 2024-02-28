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
from re import search
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_from_series,
    try_float_from_series_or_none,
    try_str_from_series,
    try_str_from_series_or_none,
)


def df_to_series(df: pd.DataFrame) -> pd.Series[Any]:
    df.columns = df.iloc[0]  # type: ignore[assignment]
    return pd.Series(df.iloc[-1], index=df.columns)


def num_to_chars(n: int) -> str:
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return "" if n < 0 else num_to_chars(d - 1) + chr(m + 65)  # chr(65) = 'A'


@dataclass(frozen=True)
class PlateInfo:
    number: str
    barcode: str
    measurement_time: Optional[str]
    measured_height: Optional[float]
    chamber_temperature_at_start: Optional[float]

    @staticmethod
    def get_series(reader: CsvReader) -> pd.Series[str]:
        assert_not_none(
            reader.pop_if_match("^Plate information"),
            msg="Unable to find expected plate information",
        )

        return df_to_series(
            assert_not_none(
                reader.pop_csv_block_as_df(),
                "Plate information CSV block",
            )
        ).replace(np.nan, None)

    @staticmethod
    def get_plate_number(series: pd.Series[str]) -> str:
        return try_str_from_series(
            series,
            "Plate",
            msg="Unable to find plate number",
        )

    @staticmethod
    def get_barcode(series: pd.Series[str], plate_number: str) -> str:
        raw_barcode = try_str_from_series_or_none(series, "Barcode")
        barcode = (raw_barcode or '=""').removeprefix('="').removesuffix('"')
        return barcode or f"Plate {plate_number}"


@dataclass(frozen=True)
class CalculatedPlateInfo(PlateInfo):
    formula: str
    name: str

    @staticmethod
    def create(series: pd.Series[str]) -> CalculatedPlateInfo:
        plate_number = PlateInfo.get_plate_number(series)

        formula = try_str_from_series(
            series,
            "Formula",
            msg="Unable to find expected formula for calculated results section.",
        )
        name = assert_not_none(
            search(r"^([^=]*)=", formula),
            msg="Unable to find expected formula name for calculated results section.",
        ).group(1)

        return CalculatedPlateInfo(
            number=plate_number,
            barcode=PlateInfo.get_barcode(series, plate_number),
            measurement_time=try_str_from_series_or_none(series, "Measurement date"),
            measured_height=try_float_from_series_or_none(series, "Measured height"),
            chamber_temperature_at_start=try_float_from_series_or_none(
                series,
                "Chamber temperature at start",
            ),
            formula=formula,
            name=name.strip(),
        )


@dataclass(frozen=True)
class ResultPlateInfo(PlateInfo):
    label: str
    measinfo: str
    emission_filter_id: str

    @staticmethod
    def create(series: pd.Series[str]) -> Optional[ResultPlateInfo]:
        label = try_str_from_series_or_none(series, "Label")
        if label is None:
            return None

        measinfo = try_str_from_series_or_none(series, "Measinfo")
        if measinfo is None:
            return None

        plate_number = PlateInfo.get_plate_number(series)
        barcode = PlateInfo.get_barcode(series, plate_number)

        return ResultPlateInfo(
            plate_number,
            barcode,
            try_str_from_series_or_none(series, "Measurement date"),
            try_float_from_series_or_none(series, "Measured height"),
            try_float_from_series_or_none(series, "Chamber temperature at start"),
            label=label,
            measinfo=measinfo,
            emission_filter_id=assert_not_none(
                search("De=(...)", measinfo),
                msg=f"Unable to find emission filter ID for Plate {barcode}.",
            ).group(1),
        )

    def match(self, background_info: BackgroundInfo) -> bool:
        return all(
            [
                background_info.plate_num == self.number,
                background_info.label in self.label,
                background_info.measinfo == self.measinfo,
            ]
        )


@dataclass
class BackgroundInfo:
    plate_num: str
    label: str
    measinfo: str


@dataclass
class BackgroundInfoList:
    background_info: list[BackgroundInfo]

    @staticmethod
    def create(reader: CsvReader) -> Optional[BackgroundInfoList]:
        title = reader.pop_if_match("^Background information")
        if title is None:
            return None

        data = assert_not_none(
            reader.pop_csv_block_as_df(header=0),
            "background information",
        )

        return BackgroundInfoList(
            background_info=[
                BackgroundInfo(
                    plate_num=assert_not_none(
                        try_str_from_series_or_none(series, "Plate"),
                        msg="Unable to find plate number from background info.",
                    ),
                    label=assert_not_none(
                        try_str_from_series_or_none(series, "Label"),
                        msg="Unable to find label from background info.",
                    ),
                    measinfo=assert_not_none(
                        try_str_from_series_or_none(series, "MeasInfo"),
                        msg="Unable to find meas info from background info.",
                    ),
                )
                for _, series in data.iterrows()
            ]
        )


@dataclass
class CalculatedResult:
    uuid: str
    col: str
    row: str
    value: float


@dataclass
class CalculatedResultList:
    calculated_results: list[CalculatedResult]

    @staticmethod
    def create(reader: CsvReader) -> CalculatedResultList:
        # Calculated results may or may not have a title
        reader.pop_if_match("^Calculated results")

        data = assert_not_none(
            reader.pop_csv_block_as_df(),
            "results data",
        )
        series = (
            data.drop(0, axis=0).drop(0, axis=1) if data.iloc[1, 0] == "A" else data
        )
        rows, cols = series.shape
        series.index = [num_to_chars(i) for i in range(rows)]  # type: ignore[assignment]
        series.columns = [str(i).zfill(2) for i in range(1, cols + 1)]  # type: ignore[assignment]

        return CalculatedResultList(
            calculated_results=[
                CalculatedResult(
                    uuid=random_uuid_str(),
                    col=col,
                    row=row,
                    value=series.loc[col, row],
                )
                for col, row in series.stack().index
            ]
        )


@dataclass
class Result:
    uuid: str
    col: str
    row: str
    value: int


@dataclass
class ResultList:
    results: list[Result]

    @staticmethod
    def create(reader: CsvReader) -> ResultList:
        # Results may or may not have a title
        reader.pop_if_match("^Results")

        data = assert_not_none(
            reader.pop_csv_block_as_df(),
            "reader data",
        )
        series = (
            data.drop(0, axis=0).drop(0, axis=1) if data.iloc[1, 0] == "A" else data
        )
        rows, cols = series.shape
        series.index = [num_to_chars(i) for i in range(rows)]  # type: ignore[assignment]
        series.columns = [str(i).zfill(2) for i in range(1, cols + 1)]  # type: ignore[assignment]

        return ResultList(
            results=[
                Result(
                    uuid=random_uuid_str(),
                    col=col,
                    row=row,
                    value=int(series.loc[col, row]),
                )
                for col, row in series.stack().index
            ]
        )


@dataclass
class Plate:
    plate_info: Union[CalculatedPlateInfo, ResultPlateInfo]
    background_info_list: Optional[BackgroundInfoList]
    calculated_result_list: CalculatedResultList
    result_list: ResultList

    @staticmethod
    def create(reader: CsvReader) -> Plate:
        series = PlateInfo.get_series(reader)
        if result_plate_info := ResultPlateInfo.create(series):
            return Plate(
                plate_info=result_plate_info,
                background_info_list=BackgroundInfoList.create(reader),
                calculated_result_list=CalculatedResultList([]),
                result_list=ResultList.create(reader),
            )
        else:
            return Plate(
                plate_info=CalculatedPlateInfo.create(series),
                background_info_list=BackgroundInfoList.create(reader),
                calculated_result_list=CalculatedResultList.create(reader),
                result_list=ResultList([]),
            )

    def collect_result_plates(self, plate_list: PlateList) -> list[Plate]:
        background_info_list = assert_not_none(
            self.background_info_list,
            msg=f"Unable to collect result plates, there is no background information for plate {self.plate_info.number}",
        )

        return [
            assert_not_none(
                plate_list.get_result_plate(background_info),
                msg=f"Unable to find result plate {background_info.label}.",
            )
            for background_info in background_info_list.background_info
        ]


@dataclass
class PlateList:
    plates: list[Plate]

    @staticmethod
    def create(reader: CsvReader) -> PlateList:
        plates: list[Plate] = []

        while reader.match("^Plate information"):
            plates.append(Plate.create(reader))
        return PlateList(plates)

    def get_result_plate(self, background_info: BackgroundInfo) -> Optional[Plate]:
        for plate in self.plates:
            if isinstance(plate.plate_info, CalculatedPlateInfo):
                continue

            if plate.plate_info.match(background_info):
                return plate
        return None


@dataclass(frozen=True)
class BasicAssayInfo:
    protocol_id: Optional[str]
    assay_id: Optional[str]

    @staticmethod
    def create(reader: CsvReader) -> BasicAssayInfo:
        reader.drop_until_inclusive("^Basic assay information")
        data = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Basic assay information",
        )
        data = data.T
        data.iloc[0].replace(":.*", "", regex=True, inplace=True)
        series = df_to_series(data)
        return BasicAssayInfo(
            try_str_from_series_or_none(series, "Protocol ID"),
            try_str_from_series_or_none(series, "Assay ID"),
        )


@dataclass(frozen=True)
class PlateType:
    number_of_wells: float

    @staticmethod
    def create(reader: CsvReader) -> PlateType:
        reader.drop_until_inclusive("^Plate type")
        data = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Plate type",
        )
        return PlateType(
            number_of_wells=try_float_from_series(
                df_to_series(data.T),
                "Number of the wells in the plate",
            ),
        )


def get_sample_role_type(encoding: str) -> SampleRoleType:
    # BL        blank               blank_role
    # CTL       control             control_sample_role
    # LB        lance_blank         blank_role
    # LC        lance_crosstalk     control_sample_role
    # LH        lance_high          control_sample_role
    # S         pl_sample           sample_role
    # STD       standard            standard_sample_role
    # -         unknown             unknown_sample_role
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
        "-": SampleRoleType.unknown_sample_role,
        "UNK": SampleRoleType.unknown_sample_role,
        "ZH": SampleRoleType.control_sample_role,
        "ZL": SampleRoleType.control_sample_role,
    }
    for pattern, value in sample_role_type_map.items():
        if encoding.startswith(pattern):
            return value

    msg = f"Unable to determine sample role type of plate map encoding {encoding}; expected to start with one of {sorted(sample_role_type_map.keys())}."
    raise AllotropeConversionError(msg)


@dataclass(frozen=True)
class PlateMap:
    plate_n: str
    group_n: str
    sample_role_type_mapping: dict[str, dict[str, SampleRoleType]]

    @staticmethod
    def create(reader: CsvReader) -> Optional[PlateMap]:
        if not reader.current_line_exists() or reader.match("^Calculations"):
            return None

        *_, plate_n = assert_not_none(reader.pop(), "Platemap number").split(",")
        *_, group_n = assert_not_none(reader.pop(), "Platemap group").split(",")

        data = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Platemap data",
        ).replace(" ", "", regex=True)

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
                    if role_type := get_sample_role_type(str(value)):
                        col_mapping[str(col)] = role_type
            if col_mapping:
                sample_role_type_mapping[str(row)] = col_mapping

        return PlateMap(plate_n, group_n, sample_role_type_mapping)

    def get_sample_role_type(self, col: str, row: str) -> SampleRoleType:
        try:
            return self.sample_role_type_mapping[row][col]
        except KeyError as e:
            msg = (
                f"Invalid plate map location for plate map {self.plate_n}: {col} {row}."
            )
            raise AllotropeConversionError(msg) from e


def create_plate_maps(reader: CsvReader) -> dict[str, PlateMap]:
    assert_not_none(
        reader.drop_until("^Platemap"),
        msg="No 'Platemap' section found.",
    )

    reader.pop()  # remove title

    maps: dict[str, PlateMap] = {}
    while _map := PlateMap.create(reader):
        maps[_map.plate_n] = _map
    return maps


@dataclass(frozen=True)
class Filter:
    name: str
    wavelength: float
    bandwidth: Optional[float] = None

    @staticmethod
    def create(reader: CsvReader) -> Optional[Filter]:
        if not reader.current_line_exists() or reader.match(
            "(^Mirror modules)|(^Instrument:)|(^Aperture:)"
        ):
            return None

        data = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Filter information",
        )
        series = df_to_series(data.T)
        name = str(series.index[0])
        description = try_str_from_series(series, "Description")

        if search_result := search("Longpass=(\\d+)nm", description):
            return Filter(name, wavelength=float(search_result.group(1)))
        return Filter(
            name,
            wavelength=float(
                assert_not_none(
                    search("CWL=(\\d+)nm", description),
                    msg=f"Unable to find wavelength for filter {name}.",
                ).group(1)
            ),
            bandwidth=float(
                assert_not_none(
                    search("BW=(\\d+)nm", description),
                    msg=f"Unable to find bandwidth for filter {name}.",
                ).group(1)
            ),
        )


def create_filters(reader: CsvReader) -> dict[str, Filter]:
    reader.drop_until("(^Filters:)|^Instrument:")

    if reader.match("^Instrument"):
        return {}

    reader.pop()  # remove title

    filters = {}
    while _filter := Filter.create(reader):
        filters[_filter.name] = _filter
    return filters


@dataclass(frozen=True)
class Labels:
    label: str
    excitation_filter: Optional[Filter]
    emission_filters: dict[str, Optional[Filter]]
    scan_position_setting: Optional[ScanPositionSettingPlateReader] = None
    number_of_flashes: Optional[float] = None
    detector_gain_setting: Optional[str] = None

    @staticmethod
    def create(reader: CsvReader) -> Labels:
        reader.drop_until_inclusive("^Labels")
        data = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Labels",
        )
        series = df_to_series(data.T).replace(np.nan, None)
        filters = create_filters(reader)
        filter_position_map = {
            "Bottom": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
            "Top": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
        }

        return Labels(
            label=series.index[0],
            excitation_filter=filters.get(
                try_str_from_series_or_none(series, "Exc. filter") or ""
            ),
            emission_filters={
                "1st": filters.get(
                    try_str_from_series_or_none(series, "Ems. filter") or "",
                ),
                "2nd": filters.get(
                    try_str_from_series_or_none(series, "2nd ems. filter") or ""
                ),
            },
            scan_position_setting=filter_position_map.get(
                try_str_from_series_or_none(series, "Using of emission filter") or ""
            ),
            number_of_flashes=try_float_from_series_or_none(
                series, "Number of flashes"
            ),
            detector_gain_setting=try_str_from_series_or_none(
                series, "Reference AD gain"
            ),
        )

    def get_emission_filter(self, id_val: str) -> Optional[Filter]:
        return self.emission_filters.get(id_val)


@dataclass(frozen=True)
class Instrument:
    serial_number: str
    nickname: str

    @staticmethod
    def create(reader: CsvReader) -> Instrument:
        assert_not_none(
            reader.drop_until("^Instrument"),
            msg="No 'Instrument' section found.",
        )

        reader.pop()  # remove title

        *_, serial_number = assert_not_none(reader.pop(), "serial number").split(",")
        *_, nickname = assert_not_none(reader.pop(), "nickname").split(",")

        return Instrument(serial_number, nickname)


@dataclass(frozen=True)
class Software:
    software_name: str
    software_version: str

    @staticmethod
    def create(reader: CsvReader) -> Software:
        exported_with_regex = "Exported with (.+) version (.+)"
        assert_not_none(
            reader.drop_until(exported_with_regex),
            msg="Unable to find software information; no 'Exported with' section found.",
        )

        search_result = assert_not_none(
            search(
                exported_with_regex,
                assert_not_none(
                    reader.pop(),
                    "software information",
                ),
            )
        )

        return Software(
            software_name=search_result.group(1),
            software_version=search_result.group(2),
        )


@dataclass(frozen=True)
class Data:
    software: Software
    plate_list: PlateList
    basic_assay_info: BasicAssayInfo
    number_of_wells: float
    plate_maps: dict[str, PlateMap]
    labels: Labels
    instrument: Instrument

    @staticmethod
    def create(reader: CsvReader) -> Data:
        return Data(
            plate_list=PlateList.create(reader),
            basic_assay_info=BasicAssayInfo.create(reader),
            number_of_wells=PlateType.create(reader).number_of_wells,
            plate_maps=create_plate_maps(reader),
            labels=Labels.create(reader),
            instrument=Instrument.create(reader),
            software=Software.create(reader),
        )
