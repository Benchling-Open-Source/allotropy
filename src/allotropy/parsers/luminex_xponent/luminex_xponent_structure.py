from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Optional

from dateutil import parser
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_str_from_series,
    try_str_from_series_or_none,
)

EMPTY_CSV_LINE = r"^,*$"
CALIBRATION_BLOCK_HEADER = "Most Recent Calibration and Verification Results"


@dataclass(frozen=True)
class Header:
    model_number: str
    equipment_serial_number: str  # SN
    analytical_method_identifier: str  # ProtocolName
    method_version: str  # ProtocolVersion
    experimental_data_identifier: str  # Batch
    sample_volume: str  # SampleVolume
    plate_well_count: float  # ProtocolPlate, column 5 (after Type)
    measurement_time: str  # BatchStartTime  MM/DD/YYYY HH:MM:SS %p ->  YYYY-MM-DD HH:MM:SS
    detector_gain_setting: str  # ProtocolReporterGain
    data_system_instance_identifier: str  # ComputerName
    analyst: Optional[str] = None  # Operator row

    @staticmethod
    def create(header_data: pd.DataFrame) -> Header:
        info_row = header_data.iloc[0]
        raw_datetime = try_str_from_series(info_row, "BatchStartTime")

        return Header(
            model_number=Header._get_model_number(header_data),
            equipment_serial_number=try_str_from_series(info_row, "SN"),
            analytical_method_identifier=try_str_from_series(info_row, "ProtocolName"),
            method_version=try_str_from_series(info_row, "ProtocolVersion"),
            experimental_data_identifier=try_str_from_series(info_row, "Batch"),
            sample_volume=try_str_from_series(info_row, "SampleVolume"),
            plate_well_count=Header._get_plate_well_count(header_data),
            measurement_time=parser.parse(raw_datetime).isoformat(),
            detector_gain_setting=try_str_from_series(info_row, "ProtocolReporterGain"),
            data_system_instance_identifier=try_str_from_series(
                info_row, "ComputerName"
            ),
            # TODO: ask about NA in the Operator entry (was in a previous version of the requirements)
            analyst=try_str_from_series_or_none(info_row, "Operator"),
        )

    @staticmethod
    def _get_model_number(header_data: pd.DataFrame) -> str:
        program_data = Header._try_col_from_header(header_data, "Program")

        try:
            model_number = program_data.iloc[2]
        except IndexError as e:
            error = "Unable to find model number in Program row."
            raise AllotropeConversionError(error) from e

        return str(model_number)

    @staticmethod
    def _get_plate_well_count(header_data: pd.DataFrame) -> float:
        protocol_plate_data = Header._try_col_from_header(header_data, "ProtocolPlate")

        try:
            plate_well_count = protocol_plate_data.iloc[3]
        except IndexError as e:
            error = "Unable to find plate well count in ProtocolPlate row."
            raise AllotropeConversionError(error) from e

        return try_float(plate_well_count, "plate well count")

    @staticmethod
    def _try_col_from_header(header_data: pd.DataFrame, key: str) -> pd.Series:
        if key not in header_data:
            error = f"Unable to find {key} data on header block."
            raise AllotropeConversionError(error)

        return header_data[key]


@dataclass(frozen=True)
class CalibrationItem:
    name: str
    report: str
    time: str

    @staticmethod
    def create(calibration_line: str) -> CalibrationItem:
        """Createds a CalibrationItem from a calibration line.

        Each line should follow the pattern "Last <calibration_name>,<calibration_report> <calibration_time><,,,,"
        example: "Last F3DeCAL1 Calibration,Passed 05/17/2023 09:25:11,,,,,,"
        """
        calibration_data = calibration_line.split(',')
        if len(calibration_data) < 2:
            error = f"Expected at least two columns on the calibration line, got: {calibration_line}"
            raise AllotropeConversionError(error)

        calibration_result = calibration_data[1].split(maxsplit=1)
        if len(calibration_result) != 2:
            error = f"Invalid calibration result format, got: {calibration_data[1]}"
            raise AllotropeConversionError(error)

        try:
            callibration_time = parser.parse(calibration_result[1]).isoformat()
        except parser.ParserError as e:
            error = "Invalid calibration time format."
            raise AllotropeConversionError(error) from e

        return CalibrationItem(
            name=calibration_data[0].replace("Last", "").strip(),
            report=calibration_result[0],
            time=callibration_time,
        )


@dataclass(frozen=True)
class Data:
    header: Header
    calibration_data: list[CalibrationItem]
    minimum_bead_count_setting: float

    @staticmethod
    def create(reader: CsvReader) -> Data:
        return Data(
            header=Header.create(Data._get_header_data(reader)),
            calibration_data=Data._get_calibration_data(reader),
            minimum_bead_count_setting=Data._get_minimum_bead_count_setting(reader),
        )

    @staticmethod
    def _get_header_data(reader: CsvReader) -> pd.DataFrame:
        header_lines = assert_not_none(
            reader.pop_until(CALIBRATION_BLOCK_HEADER), "Unable to find Header block."
        )
        header_data = pd.read_csv(
            StringIO("\n".join(header_lines)),
            header=None,
            index_col=0,
        ).dropna(how="all")
        return header_data.T

    @staticmethod
    def _get_calibration_data(reader: CsvReader) -> list[CalibrationItem]:
        reader.drop_until_inclusive(CALIBRATION_BLOCK_HEADER)
        calibration_lines = assert_not_none(
            reader.pop_csv_block_as_lines(empty_pat=EMPTY_CSV_LINE),
            "Unable to find Calibration Block.",
        )

        calibration_list = []

        for line in calibration_lines:
            calibration_list.append(CalibrationItem.create(line))

        return calibration_list

    def _get_minimum_bead_count_setting(reader: CsvReader) -> str:
        reader.drop_until(match_pat="Samples,")
        samples_info = assert_not_none(reader.pop(), "Unable to find Samples info.")
        try:
            min_bead_count_setting = samples_info.split(',')[3]
        except IndexError as e:
            error = "Unable to find minimum bead count setting in Samples info."
            raise AllotropeConversionError(error) from e

        return try_float(min_bead_count_setting, "minimum bead count setting")
