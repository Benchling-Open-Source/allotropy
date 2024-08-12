from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Analyte,
    Calibration,
    Data as MapperData,
    Error,
    Measurement as MapperMeasurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.luminex_xponent.constants import (
    CALIBRATION_BLOCK_HEADER,
    CONTAINER_TYPE,
    DEVICE_TYPE,
    EXPECTED_CALIBRATION_RESULT_LEN,
    EXPECTED_HEADER_COLUMNS,
    LUMINEX_EMPTY_PATTERN,
    MINIMUM_CALIBRATION_LINE_COLS,
    SOFTWARE_NAME,
    TABLE_HEADER_PATTERN,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
)


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
    analyst: str | None = None

    @classmethod
    def create(cls, header_data: pd.DataFrame) -> Header:
        info_row = SeriesData(header_data.iloc[0])
        return Header(
            model_number=cls._get_model_number(header_data),
            software_version=info_row[str, "Build"],
            equipment_serial_number=info_row[str, "SN"],
            analytical_method_identifier=info_row[str, "ProtocolName"],
            method_version=info_row[str, "ProtocolVersion"],
            experimental_data_identifier=info_row[str, "Batch"],
            sample_volume_setting=cls._get_sample_volume_setting(info_row),
            plate_well_count=cls._get_plate_well_count(header_data),
            measurement_time=info_row[str, "BatchStartTime"],
            detector_gain_setting=info_row[str, "ProtocolReporterGain"],
            data_system_instance_identifier=info_row[str, "ComputerName"],
            analyst=info_row.get(str, "Operator"),
        )

    @classmethod
    def _get_sample_volume_setting(cls, info_row: SeriesData) -> float:
        sample_volume = info_row[str, "SampleVolume"]

        return try_float(sample_volume.split()[0], "sample volume setting")

    @classmethod
    def _get_model_number(cls, header_data: pd.DataFrame) -> str:
        program_data = cls._try_col_from_header(header_data, "Program")

        try:
            model_number = program_data.iloc[2]
        except IndexError as e:
            msg = (
                "Unable to find model number in Program row, expected value at index 2"
            )
            raise AllotropeConversionError(msg) from e

        return str(model_number)

    @classmethod
    def _get_plate_well_count(cls, header_data: pd.DataFrame) -> float:
        protocol_plate_data = cls._try_col_from_header(header_data, "ProtocolPlate")

        try:
            plate_well_count = protocol_plate_data.iloc[3]
        except IndexError as e:
            msg = "Unable to find plate well count in ProtocolPlate row, expected value at index 3."
            raise AllotropeConversionError(msg) from e

        return try_float(str(plate_well_count), "plate well count")

    @classmethod
    def _try_col_from_header(
        cls, header_data: pd.DataFrame, key: str
    ) -> pd.Series[Any]:
        if key not in header_data:
            msg = f"Unable to find {key} data in header block."
            raise AllotropeConversionError(msg)

        return header_data[key]


def create_calibration(calibration_line: str) -> Calibration:
    """Create a Calibration from a calibration line.

    Each line should follow the pattern "Last <calibration_name>,<calibration_report> <calibration_time><,,,,"
    example: "Last F3DeCAL1 Calibration,Passed 05/17/2023 09:25:11,,,,,,"
    """
    calibration_data = calibration_line.replace('"', "").split(",")
    if len(calibration_data) < MINIMUM_CALIBRATION_LINE_COLS:
        msg = f"Expected at least two columns on the calibration line, got: {calibration_line}."
        raise AllotropeConversionError(msg)

    calibration_result = calibration_data[1].split(maxsplit=1)

    if len(calibration_result) != EXPECTED_CALIBRATION_RESULT_LEN:
        msg = f"Invalid calibration result format, expected to split into two values, got: {calibration_result}."
        raise AllotropeConversionError(msg)

    return Calibration(
        name=calibration_data[0].replace("Last", "").strip(),
        report=calibration_result[0],
        time=calibration_result[1],
    )


@dataclass(frozen=True)
class Measurement:
    identifier: str
    sample_identifier: str
    location_identifier: str
    dilution_factor_setting: float
    assay_bead_count: float
    analytes: list[Analyte]
    errors: list[Error] | None = None

    @classmethod
    def create(
        cls,
        median_data: SeriesData,
        count_data: pd.DataFrame,
        bead_ids_data: SeriesData,
        dilution_factor_data: pd.DataFrame,
        errors_data: pd.DataFrame,
    ) -> Measurement:
        location = median_data[str, "Location"]
        dilution_factor_setting = SeriesData(dilution_factor_data.loc[location])[
            float, "Dilution Factor"
        ]
        # analyte names are columns 3 through the penultimate
        analyte_names = list(median_data.series.index)[2:-1]

        well_location, location_id = cls._get_location_details(location)

        return Measurement(
            identifier=random_uuid_str(),
            sample_identifier=median_data[str, "Sample"],
            location_identifier=location_id,
            dilution_factor_setting=dilution_factor_setting,
            assay_bead_count=median_data[float, "Total Events"],
            analytes=[
                Analyte(
                    identifier=random_uuid_str(),
                    name=analyte,
                    assay_bead_identifier=bead_ids_data[str, analyte],
                    assay_bead_count=SeriesData(count_data.loc[location])[
                        float, analyte
                    ],
                    fluorescence=median_data[float, analyte],
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
    ) -> list[Error] | None:
        try:
            measurement_errors = errors_data.loc[well_location]
        except KeyError:
            return None

        if not isinstance(measurement_errors, pd.DataFrame):
            msg = f"Uxpected data shape in errors data: {measurement_errors}."
            raise AllotropeParsingError(msg)

        return map_rows(measurement_errors, lambda data: Error(data[str, "Message"]))


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

        def create_measurement(data: SeriesData) -> Measurement:
            return Measurement.create(
                median_data=data,
                count_data=count_data,
                bead_ids_data=bead_ids_data,
                dilution_factor_data=dilution_factor_data,
                errors_data=errors_data,
            )

        return MeasurementList(measurements=map_rows(median_data, create_measurement))

    @classmethod
    def _get_median_data(cls, reader: CsvReader) -> pd.DataFrame:
        reader.drop_until_inclusive(TABLE_HEADER_PATTERN.format("Median"))
        return assert_not_none(
            reader.pop_csv_block_as_df(empty_pat=LUMINEX_EMPTY_PATTERN, header="infer"),
            msg="Unable to find Median table.",
        )

    @classmethod
    def _get_bead_ids_data(cls, reader: CsvReader) -> SeriesData:
        units_df = MeasurementList._get_table_as_df(reader, "Units")
        return SeriesData(units_df.loc["BeadID:"])

    @classmethod
    def _get_table_as_df(cls, reader: CsvReader, table_name: str) -> pd.DataFrame:
        """Returns a dataframe that has the well location as index.

        Results tables in luminex xponent output files have the location as first column.
        Having this column as the index of the dataframe allows for easier lookup when
        retrieving measurement data.
        """
        reader.drop_until_inclusive(match_pat=TABLE_HEADER_PATTERN.format(table_name))

        table_lines = reader.pop_csv_block_as_lines(empty_pat=LUMINEX_EMPTY_PATTERN)

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
    calibration_data: list[Calibration]
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
        header_lines = list(reader.pop_until(CALIBRATION_BLOCK_HEADER))

        n_columns = 0
        for line in header_lines:
            n_row_columns = len(line.split(","))
            if n_row_columns > n_columns:
                n_columns = n_row_columns

        if n_columns < EXPECTED_HEADER_COLUMNS:
            msg = "Unable to parse header. Not enough data."
            raise AllotropeConversionError(msg)

        header_data = read_csv(
            StringIO("\n".join(header_lines)),
            header=None,
            index_col=0,
            names=range(n_columns),
        ).dropna(how="all")

        return header_data.T

    @classmethod
    def _get_calibration_data(cls, reader: CsvReader) -> list[Calibration]:
        reader.drop_until_inclusive(CALIBRATION_BLOCK_HEADER)
        calibration_lines = reader.pop_csv_block_as_lines(
            empty_pat=LUMINEX_EMPTY_PATTERN
        )
        if not calibration_lines:
            msg = "Unable to find Calibration Block."
            raise AllotropeConversionError(msg)

        calibration_list = []

        for line in calibration_lines:
            calibration_list.append(create_calibration(line))

        return calibration_list

    @classmethod
    def _get_minimum_bead_count_setting(cls, reader: CsvReader) -> float:
        reader.drop_until(match_pat='^"?Samples"?,')
        samples_info = assert_not_none(reader.pop(), msg="Unable to find Samples info.")
        try:
            min_bead_count_setting = samples_info.replace('"', "").split(",")[3]
        except IndexError as e:
            msg = f"Unable to find minimum bead count setting in Samples info: {samples_info}."
            raise AllotropeConversionError(msg) from e

        return try_float(min_bead_count_setting, "minimum bead count setting")


def create_data(reader: CsvReader, file_name: str) -> MapperData:
    data = Data.create(reader)
    return MapperData(
        metadata=Metadata(
            file_name=file_name,
            device_type=DEVICE_TYPE,
            container_type=CONTAINER_TYPE,
            software_name=SOFTWARE_NAME,
            software_version=data.header.software_version,
            model_number=data.header.model_number,
            equipment_serial_number=data.header.equipment_serial_number,
            data_system_instance_identifier=data.header.data_system_instance_identifier,
            analytical_method_identifier=data.header.analytical_method_identifier,
            experimental_data_identifier=data.header.experimental_data_identifier,
            method_version=data.header.method_version,
            plate_well_count=data.header.plate_well_count,
            calibrations=data.calibration_data,
        ),
        measurement_groups=[
            MeasurementGroup(
                analyst=data.header.analyst,
                measurements=[
                    MapperMeasurement(
                        identifier=measurement.identifier,
                        measurement_time=data.header.measurement_time,
                        sample_identifier=measurement.sample_identifier,
                        location_identifier=measurement.location_identifier,
                        assay_bead_count=measurement.assay_bead_count,
                        dilution_factor_setting=measurement.dilution_factor_setting,
                        sample_volume_setting=data.header.sample_volume_setting,
                        detector_gain_setting=data.header.detector_gain_setting,
                        minimum_bead_count_setting=data.minimum_bead_count_setting,
                        analytes=measurement.analytes,
                        errors=measurement.errors,
                    )
                ]
            )
            for measurement in data.measurement_list.measurements
        ],
    )
