from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Analyte,
    Calibration,
    Error,
    Measurement as MapperMeasurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NEGATIVE_ZERO
from allotropy.parsers.luminex_xponent import constants
from allotropy.parsers.luminex_xponent.luminex_xponent_reader import (
    LuminexXponentReader,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_float


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
    detector_gain_setting: str | None
    data_system_instance_identifier: str | None
    minimum_assay_bead_count_setting: float | None
    analyst: str | None

    @classmethod
    def create(
        cls, header_data: pd.DataFrame, minimum_assay_bead_count_setting: float | None
    ) -> Header:
        info_row = SeriesData(header_data.iloc[0])
        raw_datetime = info_row[str, "BatchStartTime"]
        sample_volume = info_row.get(str, ["SampleVolume", "MaxSampleUptakeVolume"])

        return Header(
            model_number=cls._get_model_number(header_data),
            software_version=info_row.get(str, "Build"),
            equipment_serial_number=info_row.get(str, "SN"),
            analytical_method_identifier=info_row.get(str, "ProtocolName"),
            method_version=info_row.get(str, "ProtocolVersion"),
            experimental_data_identifier=info_row.get(str, "Batch"),
            sample_volume_setting=try_float(
                sample_volume.split()[0], "sample volume setting"
            )
            if sample_volume
            else None,
            plate_well_count=cls._get_plate_well_count(header_data),
            measurement_time=raw_datetime,
            detector_gain_setting=info_row.get(
                str, ["ProtocolReporterGain", "ProtocolOperatingMode"]
            ),
            data_system_instance_identifier=info_row.get(str, "ComputerName"),
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

    Each line should follow the pattern "Last <calibration_name>,<calibration_report> <calibration_time><,,,,"
    example: "Last F3DeCAL1 Calibration,Passed 05/17/2023 09:25:11,,,,,,"
    """
    if len(calibration_data.series.index) < constants.MINIMUM_CALIBRATION_LINE_COLS:
        msg = f"Expected at least two columns on the calibration line, got:\n{calibration_data.series}."
        raise AllotropeConversionError(msg)

    calibration_result = calibration_data.series.iloc[1].split(maxsplit=1)
    if len(calibration_result) != constants.EXPECTED_CALIBRATION_RESULT_LEN:
        msg = f"Invalid calibration result format, expected to split into two values, got: {calibration_result}."
        raise AllotropeConversionError(msg)

    return Calibration(
        name=calibration_data.series.iloc[0].replace("Last", "").strip(),
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
        errors_data: pd.DataFrame | None,
    ) -> Measurement:
        location = str(median_data.series.name)
        if location not in dilution_factor_data.index:
            msg = f"Could not find 'Dilution Factor' data for: '{location}'."
            raise AllotropeConversionError(msg)
        if location not in count_data.index:
            msg = f"Could not find 'Count' data for: '{location}'."
            raise AllotropeConversionError(msg)

        # Keys in the median data that are not analyte data.
        metadata_keys = ["Sample", "Total Events"]

        well_location, location_id = cls._get_location_details(location)
        dilution_factor_setting = SeriesData(dilution_factor_data.loc[location]).get(
            float, "Dilution Factor", NEGATIVE_ZERO, validate=SeriesData.NOT_NAN
        )
        errors: list[Error] = []
        data_errors = cls._get_errors(errors_data, well_location) or []
        for error in data_errors:
            errors.append(Error(error=error))

        if dilution_factor_setting == NEGATIVE_ZERO:
            errors.append(
                Error(error="Not reported in file", feature="dilution factor setting")
            )

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
                    value=median_data[float, analyte],
                    statistic_datum_role=TStatisticDatumRole.median_role,
                )
                for analyte in [
                    key for key in median_data.series.index if key not in metadata_keys
                ]
            ],
            errors=errors,
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
        return map_rows(
            errors_data.loc[[well_location]], lambda data: data[str, "Message"]
        )


@dataclass(frozen=True)
class MeasurementList:
    measurements: list[Measurement]

    @classmethod
    def create(cls, results_data: dict[str, pd.DataFrame]) -> MeasurementList:
        if missing_sections := [
            section
            for section in constants.REQUIRED_SECTIONS
            if section not in results_data
        ]:
            msg = f"Unable to parse input file, missing expected sections: {missing_sections}."
            raise AllotropeConversionError(msg)

        if "BeadID:" not in results_data["Units"].index:
            msg = (
                "Could not parse bead data from 'Units' section, missing 'BeadID:' row"
            )
            raise AllotropeConversionError()
        bead_ids_data = SeriesData(results_data["Units"].loc["BeadID:"])

        def create_measurement(data: SeriesData) -> Measurement:
            return Measurement.create(
                median_data=data,
                count_data=results_data["Count"],
                bead_ids_data=bead_ids_data,
                dilution_factor_data=results_data["Dilution Factor"],
                errors_data=results_data["Warnings/Errors"]
                if "Warnings/Errors" in results_data
                else None,
            )

        return MeasurementList(map_rows(results_data["Median"], create_measurement))


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
    return Metadata(
        file_name=Path(file_path).name,
        unc_path=file_path,
        equipment_serial_number=header.equipment_serial_number,
        model_number=header.model_number,
        calibrations=calibrations,
        data_system_instance_identifier=header.data_system_instance_identifier,
        software_name=constants.DEFAULT_SOFTWARE_NAME,
        software_version=header.software_version,
        device_type=constants.DEFAULT_DEVICE_TYPE,
    )


def create_measurement_groups(
    measurements: list[Measurement], header: Header
) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            analyst=header.analyst,
            analytical_method_identifier=header.analytical_method_identifier,
            method_version=header.method_version,
            experimental_data_identifier=header.experimental_data_identifier,
            container_type=constants.DEFAULT_CONTAINER_TYPE,
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
                )
            ],
        )
        for measurement in measurements
    ]
