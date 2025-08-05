from __future__ import annotations

from dataclasses import dataclass
import itertools
from pathlib import Path
import re
from typing import Any

from dateutil.parser import parse, ParserError
import pandas as pd

from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Analyte,
    Calibration,
    Error,
    Measurement as MapperMeasurement,
    MeasurementGroup,
    Metadata,
    StatisticDimension,
    StatisticsDocument,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NEGATIVE_ZERO
from allotropy.parsers.luminex_xponent.constants import (
    CALCULATED_DATA_SECTIONS,
    DEFAULT_CONTAINER_TYPE,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_SOFTWARE_NAME,
    EXPECTED_CALIBRATION_RESULT_LEN,
    MINIMUM_CALIBRATION_LINE_COLS,
    REQUIRED_SECTIONS,
    STATISTIC_SECTIONS_CONF,
)
from allotropy.parsers.luminex_xponent.luminex_xponent_reader import (
    LuminexXponentReader,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_non_nan_float_or_negative_zero,
    try_non_nan_float_or_none,
)


@dataclass(frozen=True)
class Header:
    model_number: str | None
    software_version: str | None
    equipment_serial_number: str | None
    analytical_method_identifier: str | None
    method_version: str | None
    experimental_data_identifier: str | None
    sample_volume_setting: float | None
    plate_well_count: float
    measurement_time: str
    data_system_instance_identifier: str
    detector_gain_setting: str | None
    minimum_assay_bead_count_setting: float | None
    analyst: str | None

    @classmethod
    def create(
        cls, header_data: pd.DataFrame, minimum_assay_bead_count_setting: float | None
    ) -> Header:
        info_row = SeriesData(header_data.iloc[0])
        raw_datetime = info_row[str, "BatchStartTime"]
        sample_volume = info_row.get(str, ["SampleVolume", "MaxSampleUptakeVolume"])

        # Capture unread header data to prevent warnings
        info_row.get_unread()

        return Header(
            model_number=cls._get_model_number(header_data),
            software_version=info_row.get(str, "Build"),
            equipment_serial_number=info_row.get(str, "SN"),
            analytical_method_identifier=info_row.get(str, "ProtocolName"),
            method_version=info_row.get(str, "ProtocolVersion"),
            experimental_data_identifier=info_row.get(str, "Batch"),
            sample_volume_setting=(
                try_float(sample_volume.split()[0], "sample volume setting")
                if sample_volume
                else None
            ),
            plate_well_count=cls._get_plate_well_count(header_data),
            measurement_time=raw_datetime,
            detector_gain_setting=info_row.get(
                str, ["ProtocolReporterGain", "ProtocolOperatingMode"]
            ),
            data_system_instance_identifier=info_row[str, "ComputerName"],
            minimum_assay_bead_count_setting=minimum_assay_bead_count_setting,
            analyst=info_row.get(str, "Operator"),
        )

    @classmethod
    def _get_model_number(cls, header_data: pd.DataFrame) -> str | None:
        if "Program" not in header_data:
            return None
        program_data = header_data["Program"]

        try:
            model_number = program_data.iloc[2]
        except IndexError as e:
            msg = (
                "Unable to find model number in Program row, expected value at index 2"
            )
            raise AllotropeConversionError(msg) from e

        return str(model_number) if model_number else None

    @classmethod
    def _get_plate_well_count(cls, header_data: pd.DataFrame) -> float:
        if "ProtocolPlate" not in header_data:
            msg = "Unable to find required value 'ProtocolPlate' data in header block."
            raise AllotropeConversionError(msg)
        protocol_plate_data = header_data["ProtocolPlate"]

        try:
            plate_well_count = protocol_plate_data.iloc[3]
        except IndexError as e:
            msg = "Unable to find plate well count in ProtocolPlate row, expected value at index 3."
            raise AllotropeConversionError(msg) from e

        return try_float(str(plate_well_count), "plate well count")


def create_calibration(calibration_data: SeriesData) -> Calibration:
    """Create a CalibrationItem from a calibration line.

    Each line should follow one of these patterns:
    - "Last <calibration_name>,<calibration_report> <calibration_time><,,,,"
    - "Last <calibration_name>,<calibration_time><,,,,"
    """
    if len(calibration_data.series.index) < MINIMUM_CALIBRATION_LINE_COLS:
        msg = f"Expected at least two columns on the calibration line, got:\n{calibration_data.series}."
        raise AllotropeConversionError(msg)

    # Read the calibration data using SeriesData methods
    calibration_name = calibration_data.series.iloc[0]
    calibration_info = str(calibration_data.series.iloc[1]).strip()

    # Check if the calibration info starts with a known status value
    status_values = ["Passed", "Failed", "Calibrated", "Verified"]
    first_word = calibration_info.split()[0] if calibration_info.split() else ""

    report = None
    time = None

    if first_word in status_values:
        calibration_result = calibration_info.split(maxsplit=1)
        if len(calibration_result) == EXPECTED_CALIBRATION_RESULT_LEN:
            report = calibration_result[0]
            time = calibration_result[1]
    else:
        try:
            parse(calibration_info)
            time = calibration_info
        except ParserError:
            pass

    if not time:
        msg = f"Invalid calibration result format, got: ['{calibration_info}']."
        raise AllotropeConversionError(msg)

    return Calibration(
        name=calibration_name.replace("Last", "").strip(),
        time=time,
        report=report,
    )


@dataclass(frozen=True)
class Measurement:
    identifier: str
    sample_identifier: str
    location_identifier: str
    dilution_factor_setting: float
    assay_bead_count: float
    analytes: list[Analyte]
    calculated_data: list[CalculatedDocument]
    errors: list[Error] | None = None
    custom_info: dict[str, Any] | None = None

    @classmethod
    def create(
        cls,
        results_data: dict[str, pd.DataFrame],
        count_data: SeriesData,
        bead_ids_data: SeriesData,
    ) -> Measurement:
        location = str(count_data.series.name)
        dilution_factor_data = results_data["Dilution Factor"]
        errors_data = results_data.get("Warnings/Errors")
        measurement_identifier = random_uuid_str()

        if location not in dilution_factor_data.index:
            msg = f"Could not find 'Dilution Factor' data for: '{location}'."
            raise AllotropeConversionError(msg)

        # Keys in the median data that are not analyte data.
        metadata_keys = ["Sample", "Total Events"]

        well_location, location_id = cls._get_location_details(location)
        dilution_factor_series = SeriesData(dilution_factor_data.loc[location])
        dilution_factor_setting = dilution_factor_series.get(
            float, "Dilution Factor", NEGATIVE_ZERO, validate=SeriesData.NOT_NAN
        )
        # Capture unread dilution factor data to prevent warnings
        dilution_factor_series.get_unread()
        errors: list[Error] = []
        data_errors = cls._get_errors(errors_data, well_location) or []
        for data_error in data_errors:
            errors.append(Error(error=data_error))

        if dilution_factor_setting == NEGATIVE_ZERO:
            errors.append(
                Error(error="Not reported in file", feature="dilution factor setting")
            )

        def get_statistics_error(
            raw_value: Any, analyte: str, role: str
        ) -> Error | None:
            """Check if the raw value is empty or NaN and return an Error if so."""
            error = None
            if raw_value == "":
                error = "Not reported"
            elif try_non_nan_float_or_none(raw_value) is None:
                error = "NaN"
            return Error(error=error, feature=f"{analyte} <{role}>") if error else None

        def get_statistic_dimensions(analyte: str) -> list[StatisticDimension]:
            statistic_dimensions = []
            for section, statistic_conf in STATISTIC_SECTIONS_CONF.items():
                if (statistic_table := results_data.get(section)) is None:
                    continue
                raw_value = statistic_table.at[location, analyte]
                role = statistic_conf.role
                if error := get_statistics_error(raw_value, analyte, role.value):
                    errors.append(error)
                statistic_dimensions.append(
                    StatisticDimension(
                        value=try_non_nan_float_or_negative_zero(raw_value),
                        unit=statistic_conf.unit,
                        statistic_datum_role=role,
                    )
                )
            return statistic_dimensions

        analytes = []
        calculated_data = []
        analyte_keys = [
            key for key in count_data.series.index if key not in metadata_keys
        ]
        for analyte in analyte_keys:
            analytes.append(
                Analyte(
                    identifier=(analyte_identifier := random_uuid_str()),
                    name=analyte,
                    assay_bead_identifier=bead_ids_data[str, analyte],
                    assay_bead_count=count_data[float, analyte],
                    statistics=[
                        StatisticsDocument(
                            statistical_feature="fluorescence",
                            statistic_dimensions=get_statistic_dimensions(analyte),
                        ),
                    ],
                )
            )

            for section_name, unit in CALCULATED_DATA_SECTIONS.items():
                calculated_data_section = results_data.get(section_name, pd.DataFrame())
                # Some sections don't include the location as an index, in those cases we cannot associate
                # the calculated data with the measurement.
                if location not in calculated_data_section.index:
                    continue
                raw_value = calculated_data_section.at[location, analyte]
                if error := get_statistics_error(raw_value, analyte, section_name):
                    errors.append(error)
                calculated_data_id = random_uuid_str()
                calculated_data.append(
                    CalculatedDocument(
                        uuid=calculated_data_id,
                        name=section_name,
                        value=try_non_nan_float_or_negative_zero(raw_value),
                        unit=unit,
                        data_sources=[
                            DataSource(
                                feature="fluorescence",
                                reference=Referenceable(uuid=analyte_identifier),
                            )
                        ],
                    )
                )

        return Measurement(
            identifier=measurement_identifier,
            sample_identifier=count_data[str, "Sample"],
            location_identifier=location_id,
            dilution_factor_setting=dilution_factor_setting,
            assay_bead_count=count_data[float, "Total Events"],
            analytes=analytes,
            errors=errors,
            calculated_data=calculated_data,
            # Get unread data after all keys have been read
            custom_info=count_data.get_unread() if count_data.get_unread() else None,
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
        cls, errors_data: pd.DataFrame | None, well_location: str
    ) -> list[str] | None:
        if errors_data is None or well_location not in errors_data.index:
            return None

        def extract_message(data: SeriesData) -> str:
            message = data[str, "Message"]
            # Capture unread error data to prevent warnings
            data.get_unread()
            return message

        return map_rows(errors_data.loc[[well_location]], extract_message)


@dataclass(frozen=True)
class MeasurementList:
    measurements: list[Measurement]

    @classmethod
    def create(cls, results_data: dict[str, pd.DataFrame]) -> MeasurementList:
        if missing_sections := [
            section for section in REQUIRED_SECTIONS if section not in results_data
        ]:
            msg = f"Unable to parse input file, missing expected sections: {missing_sections}."
            raise AllotropeConversionError(msg)

        # Validate that there's at least one statistic section in results_data
        if not any(
            section in results_data for section in STATISTIC_SECTIONS_CONF.keys()
        ):
            msg = f"Unable to parse input file, expecting at least one of the following sections: {STATISTIC_SECTIONS_CONF.keys()}."
            raise AllotropeConversionError(msg)

        if "BeadID:" not in results_data["Units"].index:
            msg = (
                "Could not parse bead data from 'Units' section, missing 'BeadID:' row"
            )
            raise AllotropeConversionError()
        bead_ids_data = SeriesData(results_data["Units"].loc["BeadID:"])

        def create_measurement(count_data: SeriesData) -> Measurement:
            return Measurement.create(
                results_data=results_data,
                count_data=count_data,
                bead_ids_data=bead_ids_data,
            )

        # Capture unread bead IDs data to prevent warnings
        bead_ids_data.get_unread()

        return MeasurementList(map_rows(results_data["Count"], create_measurement))


@dataclass(frozen=True)
class Data:
    header: Header
    calibrations: list[Calibration]
    measurement_list: MeasurementList

    @classmethod
    def create(cls, reader: LuminexXponentReader) -> Data:
        return Data(
            header=Header.create(
                reader.header_data, reader.minimum_assay_bead_count_setting
            ),
            calibrations=map_rows(reader.calibration_data, create_calibration),
            measurement_list=MeasurementList.create(reader.results_data),
        )


def create_metadata(
    header: Header, calibrations: list[Calibration], file_path: str
) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        asm_file_identifier=path.with_suffix(".json").name,
        unc_path=file_path,
        equipment_serial_number=header.equipment_serial_number,
        model_number=header.model_number,
        calibrations=calibrations,
        data_system_instance_identifier=header.data_system_instance_identifier,
        software_name=DEFAULT_SOFTWARE_NAME,
        software_version=header.software_version,
        device_type=DEFAULT_DEVICE_TYPE,
    )


def create_measurement_groups(
    measurements: list[Measurement], header: Header
) -> tuple[list[MeasurementGroup], list[CalculatedDocument] | None]:
    measurement_groups = [
        MeasurementGroup(
            analyst=header.analyst,
            analytical_method_identifier=header.analytical_method_identifier,
            method_version=header.method_version,
            experimental_data_identifier=header.experimental_data_identifier,
            container_type=DEFAULT_CONTAINER_TYPE,
            plate_well_count=header.plate_well_count,
            measurements=[
                MapperMeasurement(
                    identifier=measurement.identifier,
                    measurement_time=header.measurement_time,
                    sample_identifier=measurement.sample_identifier,
                    location_identifier=measurement.location_identifier,
                    sample_volume_setting=header.sample_volume_setting,
                    dilution_factor_setting=measurement.dilution_factor_setting,
                    minimum_assay_bead_count_setting=header.minimum_assay_bead_count_setting,
                    detector_gain_setting=header.detector_gain_setting,
                    assay_bead_count=measurement.assay_bead_count,
                    analytes=measurement.analytes,
                    errors=measurement.errors if measurement.errors else None,
                    custom_info=measurement.custom_info,
                )
            ],
        )
        for measurement in measurements
    ]
    calculated_documents = list(
        itertools.chain(*[measurement.calculated_data for measurement in measurements])
    )
    return measurement_groups, calculated_documents
