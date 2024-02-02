from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import re
from typing import Any, Optional

import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_float_from_series,
    try_str_from_series,
    try_str_from_series_or_none,
)

EMPTY_CSV_LINE = r"^,*$"
CALIBRATION_BLOCK_HEADER = "Most Recent Calibration and Verification Results"
TABLE_HEADER_PATTERN = "DataType:,{}"
MINIMUM_CALIBRATION_LINE_COLS = 2
EXPECTED_CALIBRATION_RESULT_LEN = 2


@dataclass(frozen=True)
class Header:
    model_number: str
    software_version: str
    equipment_serial_number: str
    analytical_method_identifier: str
    method_version: str
    experimental_data_identifier: str
    sample_volume_setting: float
    plate_well_count: float
    measurement_time: str
    detector_gain_setting: str
    data_system_instance_identifier: str
    analyst: Optional[str] = None

    @classmethod
    def create(cls, header_data: pd.DataFrame) -> Header:
        info_row = header_data.iloc[0]
        raw_datetime = try_str_from_series(info_row, "BatchStartTime")

        return Header(
            model_number=cls._get_model_number(header_data),
            software_version=try_str_from_series(info_row, "Build"),
            equipment_serial_number=try_str_from_series(info_row, "SN"),
            analytical_method_identifier=try_str_from_series(info_row, "ProtocolName"),
            method_version=try_str_from_series(info_row, "ProtocolVersion"),
            experimental_data_identifier=try_str_from_series(info_row, "Batch"),
            sample_volume_setting=cls._get_sample_volume_setting(info_row),
            plate_well_count=cls._get_plate_well_count(header_data),
            measurement_time=raw_datetime,
            detector_gain_setting=try_str_from_series(info_row, "ProtocolReporterGain"),
            data_system_instance_identifier=try_str_from_series(
                info_row, "ComputerName"
            ),
            analyst=try_str_from_series_or_none(info_row, "Operator"),
        )

    @classmethod
    def _get_sample_volume_setting(cls, info_row: pd.Series[Any]) -> float:
        sample_volume = try_str_from_series(info_row, "SampleVolume")

        return try_float(sample_volume.split()[0], "sample volume setting")

    @classmethod
    def _get_model_number(cls, header_data: pd.DataFrame) -> str:
        program_data = cls._try_col_from_header(header_data, "Program")

        try:
            model_number = program_data.iloc[2]
        except IndexError as e:
            msg = "Unable to find model number in Program row."
            raise AllotropeConversionError(msg) from e

        return str(model_number)

    @classmethod
    def _get_plate_well_count(cls, header_data: pd.DataFrame) -> float:
        protocol_plate_data = cls._try_col_from_header(header_data, "ProtocolPlate")

        try:
            plate_well_count = protocol_plate_data.iloc[3]
        except IndexError as e:
            msg = "Unable to find plate well count in ProtocolPlate row."
            raise AllotropeConversionError(msg) from e

        return try_float(plate_well_count, "plate well count")

    @classmethod
    def _try_col_from_header(
        cls, header_data: pd.DataFrame, key: str
    ) -> pd.Series[Any]:
        if key not in header_data:
            msg = f"Unable to find {key} data on header block."
            raise AllotropeConversionError(msg)

        return header_data[key]


@dataclass(frozen=True)
class CalibrationItem:
    name: str
    report: str
    time: str

    @classmethod
    def create(cls, calibration_line: str) -> CalibrationItem:
        """Create a CalibrationItem from a calibration line.

        Each line should follow the pattern "Last <calibration_name>,<calibration_report> <calibration_time><,,,,"
        example: "Last F3DeCAL1 Calibration,Passed 05/17/2023 09:25:11,,,,,,"
        """
        calibration_data = calibration_line.split(",")
        if len(calibration_data) < MINIMUM_CALIBRATION_LINE_COLS:
            msg = f"Expected at least two columns on the calibration line, got: {calibration_line}"
            raise AllotropeConversionError(msg)

        calibration_result = calibration_data[1].split(maxsplit=1)

        if len(calibration_result) != EXPECTED_CALIBRATION_RESULT_LEN:
            msg = f"Invalid calibration result format, got: {calibration_data[1]}"
            raise AllotropeConversionError(msg)

        return CalibrationItem(
            name=calibration_data[0].replace("Last", "").strip(),
            report=calibration_result[0],
            time=calibration_result[1],
        )


@dataclass(frozen=True)
class Analyte:
    analyte_name: str
    assay_bead_identifier: str
    assay_bead_count: float
    fluorescence: float


@dataclass(frozen=True)
class Measurement:
    sample_identifier: str
    location_identifier: str
    dilution_factor_setting: float
    assay_bead_count: float
    analytes: list[Analyte]
    errors: Optional[list[str]] = None

    @classmethod
    def create(
        cls,
        median_data: pd.Series[Any],
        count_data: pd.DataFrame,
        bead_ids_data: pd.Series[str],
        dilution_factor_data: pd.DataFrame,
        errors_data: pd.DataFrame,
    ) -> Measurement:
        location = try_str_from_series(median_data, "Location")
        dilution_factor_setting = try_float_from_series(
            dilution_factor_data.loc[location], "Dilution Factor"
        )
        # analyte names are columns 3 through the penultimate
        analyte_names = list(median_data.index)[2:-1]

        well_location, location_id = cls._get_location_details(location)

        return Measurement(
            sample_identifier=try_str_from_series(median_data, "Sample"),
            location_identifier=location_id,
            dilution_factor_setting=dilution_factor_setting,
            assay_bead_count=try_float_from_series(median_data, "Total Events"),
            analytes=[
                Analyte(
                    analyte_name=analyte,
                    assay_bead_identifier=try_str_from_series(bead_ids_data, analyte),
                    assay_bead_count=try_float_from_series(
                        count_data.loc[location], analyte
                    ),
                    fluorescence=try_float_from_series(median_data, analyte),
                )
                for analyte in analyte_names
            ],
            errors=cls._get_errors(errors_data, well_location),
        )

    @classmethod
    def _get_location_details(cls, location: str) -> tuple[str, str]:
        location_regex = r"\d+\((?P<well_location>\d+,(?P<location_id>\w+))\)"
        match = assert_not_none(
            re.search(location_regex, location),
            msg=f"Invalid location format: {location}",
        )

        return match.group("well_location"), match.group("location_id")

    @classmethod
    def _get_errors(
        cls, errors_data: pd.DataFrame, well_location: str
    ) -> Optional[list[str]]:
        try:
            measurement_errors = errors_data.loc[well_location]
        except KeyError:
            return None

        return [
            measurement_errors.iloc[i]["Message"]
            for i in range(len(measurement_errors))
        ]


@dataclass(frozen=True)
class MeasurementList:
    measurements: list[Measurement]

    @classmethod
    def create(cls, reader: CsvReader) -> MeasurementList:
        median_data = cls._get_median_data(reader)

        count_data = cls._get_table_as_df(reader, "Count")
        bead_ids_data = cls._get_bead_ids_data(reader)
        dilution_factor_data = cls._get_table_as_df(reader, "Dilution Factor")
        errors_data = cls._get_table_as_df(reader, "Warnings/Errors")

        return MeasurementList(
            measurements=[
                Measurement.create(
                    median_data=median_data.iloc[i],
                    count_data=count_data,
                    bead_ids_data=bead_ids_data,
                    dilution_factor_data=dilution_factor_data,
                    errors_data=errors_data,
                )
                for i in range(len(median_data))
            ]
        )

    @classmethod
    def _get_median_data(cls, reader: CsvReader) -> pd.DataFrame:
        reader.drop_until_inclusive(TABLE_HEADER_PATTERN.format("Median"))
        return assert_not_none(
            reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE, header="infer"),
            msg="Unable to find Median table.",
        )

    @classmethod
    def _get_bead_ids_data(cls, reader: CsvReader) -> pd.Series[str]:
        units_df = MeasurementList._get_table_as_df(reader, "Units")
        return units_df.loc["BeadID:"]

    @classmethod
    def _get_table_as_df(cls, reader: CsvReader, table_name: str) -> pd.DataFrame:
        """Returns a dataframe that has the well location as index.

        Results tables in luminex xponent output files have the location as first column.
        Having this column as the index of the dataframe allows for easier lookup when
        retrieving measurement data.
        """
        reader.drop_until_inclusive(match_pat=TABLE_HEADER_PATTERN.format(table_name))

        table_lines = reader.pop_csv_block_as_lines(empty_pat=EMPTY_CSV_LINE)

        if not table_lines:
            msg = f"Unable to find {table_name} table."
            raise AllotropeConversionError(msg)

        return read_csv(
            StringIO("\n".join(table_lines)),
            header=[0],
            index_col=[0],
        ).dropna(how="all", axis=1)


@dataclass(frozen=True)
class Data:
    header: Header
    calibration_data: list[CalibrationItem]
    minimum_bead_count_setting: float
    measurement_list: MeasurementList

    @classmethod
    def create(cls, reader: CsvReader) -> Data:
        return Data(
            header=Header.create(cls._get_header_data(reader)),
            calibration_data=cls._get_calibration_data(reader),
            minimum_bead_count_setting=cls._get_minimum_bead_count_setting(reader),
            measurement_list=MeasurementList.create(reader),
        )

    @classmethod
    def _get_header_data(cls, reader: CsvReader) -> pd.DataFrame:
        header_lines = assert_not_none(
            reader.pop_until(CALIBRATION_BLOCK_HEADER), "Unable to find Header block."
        )
        header_data = read_csv(
            StringIO("\n".join(header_lines)),
            header=None,
            index_col=0,
        ).dropna(how="all")
        return header_data.T

    @classmethod
    def _get_calibration_data(cls, reader: CsvReader) -> list[CalibrationItem]:
        reader.drop_until_inclusive(CALIBRATION_BLOCK_HEADER)
        calibration_lines = reader.pop_csv_block_as_lines(empty_pat=EMPTY_CSV_LINE)
        if not calibration_lines:
            msg = "Unable to find Calibration Block."
            raise AllotropeConversionError(msg)

        calibration_list = []

        for line in calibration_lines:
            calibration_list.append(CalibrationItem.create(line))

        return calibration_list

    @classmethod
    def _get_minimum_bead_count_setting(cls, reader: CsvReader) -> float:
        reader.drop_until(match_pat="Samples,")
        samples_info = assert_not_none(reader.pop(), "Unable to find Samples info.")
        try:
            min_bead_count_setting = samples_info.split(",")[3]
        except IndexError as e:
            msg = "Unable to find minimum bead count setting in Samples info."
            raise AllotropeConversionError(msg) from e

        return try_float(min_bead_count_setting, "minimum bead count setting")
