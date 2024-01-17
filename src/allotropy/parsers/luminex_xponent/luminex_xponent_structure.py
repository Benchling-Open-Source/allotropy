from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Optional

from dateutil import parser
import pandas as pd

from allotropy.parsers.lines_reader import LinesReader
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
    analyst: Optional[str] = None  # Operator row

    @staticmethod
    def create(header_data: pd.DataFrame) -> Header:
        info_row = header_data.iloc[0]
        program_data = assert_not_none(
            header_data["Program"], "Unable to find Program row on header block."
        )
        model_number = program_data.iloc[2]
        raw_datetime = try_str_from_series(info_row, "BatchStartTime")

        return Header(
            model_number=model_number,
            equipment_serial_number=try_str_from_series(info_row, "SN"),
            analytical_method_identifier=try_str_from_series(info_row, "ProtocolName"),
            method_version=try_str_from_series(info_row, "ProtocolVersion"),
            experimental_data_identifier=try_str_from_series(info_row, "Batch"),
            sample_volume=try_str_from_series(info_row, "SampleVolume"),
            plate_well_count=try_float(
                header_data["ProtocolPlate"].iloc[3], "plate well count"
            ),
            measurement_time=parser.parse(raw_datetime).isoformat(),
            detector_gain_setting=try_str_from_series(info_row, "ProtocolReporterGain"),
            # TODO: ask about NA in the Operator entry (was in a previous version of the requirements)
            analyst=try_str_from_series_or_none(info_row, "Operator"),
        )


@dataclass(frozen=True)
class Data:
    header: Header

    @staticmethod
    def create(reader: LinesReader) -> Data:
        header_lines = reader.pop_until(
            "Most Recent Calibration and Verification Results"
        )
        header_df = pd.read_csv(
            StringIO("\n".join(header_lines)),
            header=None,
            index_col=0,
        ).dropna(how="all")
        header_df = header_df.T

        return Data(header=Header.create(header_df))
