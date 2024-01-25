from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import re
from typing import Any, Optional

from dateutil import parser
import pandas as pd

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
LOCATION_REGEX = r"\d+,(\w+)"


def _get_location_identifier(location: str) -> str:
    match = assert_not_none(
        re.search(LOCATION_REGEX, location),
        msg="Unable to find location identifier.",
    )

    return match.group(1)


@dataclass(frozen=True)
class Header:
    model_number: str
    software_version: str
    equipment_serial_number: str  # SN
    analytical_method_identifier: str  # ProtocolName
    method_version: str  # ProtocolVersion
    experimental_data_identifier: str  # Batch
    sample_volume_setting: float  # SampleVolume
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
            software_version=try_str_from_series(info_row, "Build"),
            equipment_serial_number=try_str_from_series(info_row, "SN"),
            analytical_method_identifier=try_str_from_series(info_row, "ProtocolName"),
            method_version=try_str_from_series(info_row, "ProtocolVersion"),
            experimental_data_identifier=try_str_from_series(info_row, "Batch"),
            sample_volume_setting=Header._get_sample_volume_setting(info_row),
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
    def _get_sample_volume_setting(info_row: pd.Series[Any]) -> float:
        sample_volume = try_str_from_series(info_row, "SampleVolume")

        return try_float(sample_volume.split()[0], "sample volume setting")

    @staticmethod
    def _get_model_number(header_data: pd.DataFrame) -> str:
        program_data = Header._try_col_from_header(header_data, "Program")

        try:
            model_number = program_data.iloc[2]
        except IndexError as e:
            msg = "Unable to find model number in Program row."
            raise AllotropeConversionError(msg) from e

        return str(model_number)

    @staticmethod
    def _get_plate_well_count(header_data: pd.DataFrame) -> float:
        protocol_plate_data = Header._try_col_from_header(header_data, "ProtocolPlate")

        try:
            plate_well_count = protocol_plate_data.iloc[3]
        except IndexError as e:
            msg = "Unable to find plate well count in ProtocolPlate row."
            raise AllotropeConversionError(msg) from e

        return try_float(plate_well_count, "plate well count")

    @staticmethod
    def _try_col_from_header(header_data: pd.DataFrame, key: str) -> pd.Series[Any]:
        if key not in header_data:
            msg = f"Unable to find {key} data on header block."
            raise AllotropeConversionError(msg)

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
        calibration_data = calibration_line.split(",")
        if len(calibration_data) < MINIMUM_CALIBRATION_LINE_COLS:
            msg = f"Expected at least two columns on the calibration line, got: {calibration_line}"
            raise AllotropeConversionError(msg)

        calibration_result = calibration_data[1].split(maxsplit=1)

        if len(calibration_result) != EXPECTED_CALIBRATION_RESULT_LEN:
            msg = f"Invalid calibration result format, got: {calibration_data[1]}"
            raise AllotropeConversionError(msg)

        try:
            callibration_time = parser.parse(calibration_result[1]).isoformat()
        except parser.ParserError as e:
            msg = "Invalid calibration time format."
            raise AllotropeConversionError(msg) from e

        return CalibrationItem(
            name=calibration_data[0].replace("Last", "").strip(),
            report=calibration_result[0],
            time=callibration_time,
        )


@dataclass(frozen=True)
class ErrorDocument:
    error: str


@dataclass(frozen=True)
class Analyte:
    analyte_name: str
    assay_bead_identifier: str
    assay_bead_count: float
    fluorescence: float

    @staticmethod
    def create(analyte_name: str, fluorescence: float) -> Analyte:
        return Analyte(
            analyte_name=analyte_name,
            assay_bead_identifier="29",
            assay_bead_count=1,
            fluorescence=fluorescence,
        )


@dataclass(frozen=True)
class Measurement:
    sample_identifier: str
    location_identifier: str
    dilution_factor_setting: float
    assay_bead_count: float
    analytes: Optional[list[Analyte]] = None
    errors: Optional[list[ErrorDocument]] = None

    @staticmethod
    def create(
        median_data: pd.Series[Any],
        count_data: pd.DataFrame,
        units_data: pd.DataFrame,
        dilution_factor_data: pd.DataFrame,
        analyte_names: list[str],
    ) -> Measurement:
        location = try_str_from_series(median_data, "Location")
        dilution_factor_setting = try_float_from_series(
            dilution_factor_data.loc[location], "Dilution Factor"
        )
        return Measurement(
            sample_identifier=try_str_from_series(median_data, "Sample"),
            location_identifier=_get_location_identifier(location),
            dilution_factor_setting=dilution_factor_setting,
            assay_bead_count=try_float_from_series(median_data, "Total Events"),
            analytes=[
                Analyte(
                    analyte_name=analyte,
                    assay_bead_identifier=units_data[analyte].iloc[0],
                    assay_bead_count=count_data.loc[location][analyte],
                    fluorescence=median_data[analyte],
                )
                for analyte in analyte_names
            ],
        )


@dataclass(frozen=True)
class MeasurementList:
    measurements: list[Measurement]

    @staticmethod
    def create(reader: CsvReader) -> MeasurementList:
        median_data = MeasurementList._get_median_data(reader)
        count_data = MeasurementList._get_count_data(reader)
        units_data = MeasurementList._get_units_data(reader)
        dilution_factor_data = MeasurementList._get_dilution_factor_data(reader)
        reader.current_line = 0
        MeasurementList._get_table_from_reader_as_df(reader, "Units")
        # analyte names are columns 3 through the penultimate
        analyte_names = list(median_data.columns)[2:-1]

        return MeasurementList(
            measurements=[
                Measurement.create(
                    median_data=median_data.iloc[i],
                    count_data=count_data,
                    dilution_factor_data=dilution_factor_data,
                    units_data=units_data,
                    analyte_names=analyte_names,
                )
                for i in range(len(median_data))
            ]
        )

    @staticmethod
    def _get_median_data(reader: CsvReader) -> pd.DataFrame:
        reader.drop_until_inclusive(TABLE_HEADER_PATTERN.format("Median"))
        return assert_not_none(
            reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE, header="infer"),
            msg="Unable to find Median table.",
        )

    @staticmethod
    def _get_units_data(reader: CsvReader) -> pd.DataFrame:
        reader.drop_until_inclusive(TABLE_HEADER_PATTERN.format("Units"))
        return assert_not_none(
            reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE, header="infer"),
            msg="Unable to find Units table.",
        )

    @staticmethod
    def _get_count_data(reader: CsvReader) -> pd.DataFrame:
        return MeasurementList._get_table_from_reader_as_df(reader, "Count")

    @staticmethod
    def _get_dilution_factor_data(reader: CsvReader) -> pd.DataFrame:
        return MeasurementList._get_table_from_reader_as_df(reader, "Dilution Factor")

    @staticmethod
    def _get_table_from_reader_as_df(
        reader: CsvReader, table_name: str
    ) -> pd.DataFrame:
        reader.drop_until_inclusive(match_pat=TABLE_HEADER_PATTERN.format(table_name))

        table_lines = assert_not_none(
            # TODO: pop_csv_block_as_lines will not be None, validate emptyness instead
            reader.pop_csv_block_as_lines(empty_pat=EMPTY_CSV_LINE),
            f"Unable to find {table_name} table.",
        )
        return pd.read_csv(
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

    # Row in the Median table = mesurement / sample
    # column = Analyte
    # Several analytes per row (always the same number)
    # As many measurements as rows in the Median table
    @staticmethod
    def create(reader: CsvReader) -> Data:
        return Data(
            header=Header.create(Data._get_header_data(reader)),
            calibration_data=Data._get_calibration_data(reader),
            minimum_bead_count_setting=Data._get_minimum_bead_count_setting(reader),
            measurement_list=MeasurementList.create(reader),
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
            # TODO: pop_csv_block_as_lines will not be None, validate emptyness instead
            reader.pop_csv_block_as_lines(empty_pat=EMPTY_CSV_LINE),
            "Unable to find Calibration Block.",
        )

        calibration_list = []

        for line in calibration_lines:
            calibration_list.append(CalibrationItem.create(line))

        return calibration_list

    @staticmethod
    def _get_minimum_bead_count_setting(reader: CsvReader) -> float:
        reader.drop_until(match_pat="Samples,")
        samples_info = assert_not_none(reader.pop(), "Unable to find Samples info.")
        try:
            min_bead_count_setting = samples_info.split(",")[3]
        except IndexError as e:
            msg = "Unable to find minimum bead count setting in Samples info."
            raise AllotropeConversionError(msg) from e

        return try_float(min_bead_count_setting, "minimum bead count setting")
