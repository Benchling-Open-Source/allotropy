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
class Data:
    header: Header

    @staticmethod
    def create(reader: CsvReader) -> Data:
        header_df = Data._get_header_df(reader)

        return Data(header=Header.create(header_df))

    @staticmethod
    def _get_header_df(reader: CsvReader) -> pd.DataFrame:
        header_lines = assert_not_none(
            reader.pop_until("Most Recent Calibration and Verification Results")
        )
        header_df = pd.read_csv(
            StringIO("\n".join(header_lines)),
            header=None,
            index_col=0,
        ).dropna(how="all")
        return header_df.T
