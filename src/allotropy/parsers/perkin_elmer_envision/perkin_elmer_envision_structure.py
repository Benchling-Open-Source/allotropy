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
from typing import Any

import numpy as np
import pandas as pd

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    num_to_chars,
)


# TODO(nstender): figure out how to integrate this with pandas util function
def df_to_series(df: pd.DataFrame) -> pd.Series[Any]:
    df.columns = df.iloc[0]  # type: ignore[assignment]
    return pd.Series(df.iloc[-1], index=df.columns)


@dataclass(frozen=True)
class PlateInfo:
    number: str
    barcode: str
    measurement_time: str | None
    measured_height: float | None
    chamber_temperature_at_start: float | None

    @staticmethod
    def get_series(reader: CsvReader) -> SeriesData:
        assert_not_none(
            reader.pop_if_match("^Plate information"),
            msg="Unable to find expected plate information",
        )

        return SeriesData(
            df_to_series(
                assert_not_none(
                    reader.pop_csv_block_as_df(),
                    "Plate information CSV block",
                )
            ).replace(np.nan, None)
        )


@dataclass(frozen=True)
class CalculatedPlateInfo(PlateInfo):
    formula: str
    name: str

    @staticmethod
    def create(data: SeriesData) -> CalculatedPlateInfo:
        plate_number = data[str, "Plate"]
        formula = data[
            str,
            "Formula",
            "Unable to find expected formula for calculated results section.",
        ]

        name = assert_not_none(
            search(r"^([^=]*)=", formula),
            msg="Unable to find expected formula name for calculated results section.",
        ).group(1)

        raw_barcode = data.get(str, "Barcode")
        barcode = (raw_barcode or '=""').removeprefix('="').removesuffix('"')
        barcode = barcode or f"Plate {plate_number}"

        return CalculatedPlateInfo(
            number=plate_number,
            barcode=barcode,
            measurement_time=data.get(str, "Measurement date"),
            measured_height=data.get(float, "Measured height"),
            chamber_temperature_at_start=data.get(
                float, "Chamber temperature at start"
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
    def create(series: SeriesData) -> ResultPlateInfo | None:
        label = series.get(str, "Label")
        if label is None:
            return None

        measinfo = series.get(str, "Measinfo")
        if measinfo is None:
            return None

        plate_number = series[str, "Plate"]
        raw_barcode = series.get(str, "Barcode")
        barcode = (raw_barcode or '=""').removeprefix('="').removesuffix('"')
        barcode = barcode or f"Plate {plate_number}"

        return ResultPlateInfo(
            plate_number,
            barcode,
            series.get(str, "Measurement date"),
            series.get(float, "Measured height"),
            series.get(float, "Chamber temperature at start"),
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
    def create(reader: CsvReader) -> BackgroundInfoList | None:
        title = reader.pop_if_match("^Background information")
        if title is None:
            return None

        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(header=0),
            "background information",
        )

        row_data = [SeriesData(series) for _, series in data_frame.iterrows()]

        return BackgroundInfoList(
            background_info=[
                BackgroundInfo(
                    plate_num=data[
                        str,
                        "Plate",
                        "Unable to find plate number from background info.",
                    ],
                    label=data[
                        str, "Label", "Unable to find label from background info."
                    ],
                    measinfo=data[
                        str,
                        "MeasInfo",
                        "Unable to find meas info from background info.",
                    ],
                )
                for data in row_data
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

        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(),
            "results data",
        )
        series = (
            data_frame.drop(0, axis=0).drop(0, axis=1)
            if data_frame.iloc[1, 0] == "A"
            else data_frame
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

        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(),
            "reader data",
        )
        series = (
            data_frame.drop(0, axis=0).drop(0, axis=1)
            if data_frame.iloc[1, 0] == "A"
            else data_frame
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
    plate_info: CalculatedPlateInfo | ResultPlateInfo
    background_info_list: BackgroundInfoList | None
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

    def get_result_plate(self, background_info: BackgroundInfo) -> Plate | None:
        for plate in self.plates:
            if isinstance(plate.plate_info, CalculatedPlateInfo):
                continue

            if plate.plate_info.match(background_info):
                return plate
        return None


@dataclass(frozen=True)
class BasicAssayInfo:
    protocol_id: str | None
    assay_id: str | None

    @staticmethod
    def create(reader: CsvReader) -> BasicAssayInfo:
        reader.drop_until_inclusive("^Basic assay information")
        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Basic assay information",
        ).T
        data_frame.iloc[0] = data_frame.iloc[0].replace(":.*", "", regex=True)
        data = SeriesData(df_to_series(data_frame))
        return BasicAssayInfo(data.get(str, "Protocol ID"), data.get(str, "Assay ID"))


@dataclass(frozen=True)
class PlateType:
    number_of_wells: float

    @staticmethod
    def create(reader: CsvReader) -> PlateType:
        reader.drop_until_inclusive("^Plate type")
        data_frame = assert_not_none(reader.pop_csv_block_as_df(), "Plate type").T
        data = SeriesData(df_to_series(data_frame))
        return PlateType(
            number_of_wells=data[float, "Number of the wells in the plate"]
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
    def create(reader: CsvReader) -> PlateMap | None:
        if not reader.current_line_exists() or reader.match("^Calculations"):
            return None

        *_, plate_n = assert_not_none(reader.pop(), "Platemap number").split(",")
        *_, group_n = assert_not_none(reader.pop(), "Platemap group").split(",")

        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Platemap data",
        ).replace(" ", "", regex=True)

        reader.pop_data()  # drop type specification
        reader.drop_empty()

        series = (
            data_frame.drop(0, axis=0).drop(0, axis=1)
            if data_frame.iloc[1, 0] == "A"
            else data_frame
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
    bandwidth: float | None = None

    @staticmethod
    def create(reader: CsvReader) -> Filter | None:
        if not reader.current_line_exists() or reader.match(
            "(^Mirror modules)|(^Instrument:)|(^Aperture:)"
        ):
            return None

        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Filter information",
        )
        data = SeriesData(df_to_series(data_frame.T))
        name = str(data.series.index[0])
        description = data[str, "Description"]

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
    excitation_filter: Filter | None
    emission_filters: dict[str, Filter | None]
    scan_position_setting: ScanPositionSettingPlateReader | None = None
    number_of_flashes: float | None = None
    detector_gain_setting: str | None = None

    @staticmethod
    def create(reader: CsvReader) -> Labels:
        reader.drop_until_inclusive("^Labels")
        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Labels",
        )
        data = SeriesData(df_to_series(data_frame.T).replace(np.nan, None))
        filters = create_filters(reader)
        filter_position_map = {
            "Bottom": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
            "Top": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
        }

        return Labels(
            label=data.series.index[0],
            excitation_filter=filters.get(data.get(str, "Exc. filter", NOT_APPLICABLE)),
            emission_filters={
                "1st": filters.get(
                    data.get(str, "Ems. filter", NOT_APPLICABLE),
                ),
                "2nd": filters.get(data.get(str, "2nd ems. filter", NOT_APPLICABLE)),
            },
            scan_position_setting=filter_position_map.get(
                data.get(str, "Using of emission filter", NOT_APPLICABLE)
            ),
            number_of_flashes=data.get(float, "Number of flashes"),
            detector_gain_setting=data.get(str, "Reference AD gain"),
        )

    def get_emission_filter(self, id_val: str) -> Filter | None:
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
