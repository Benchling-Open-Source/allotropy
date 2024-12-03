from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import re

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    ErrorDocument,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NEGATIVE_ZERO, NOT_APPLICABLE
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.tecan_magellan import constants
from allotropy.parsers.utils.pandas import df_to_series_data, read_csv, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_float


def get_measurement_type(measurement_mode: str) -> MeasurementType:
    if measurement_mode.lower() == "absorbance":
        return MeasurementType.ULTRAVIOLET_ABSORBANCE

    msg = f"Only Absorbance measurements are supported as this time. Got {measurement_mode}."
    raise AllotropeConversionError(msg)


def parse_settings_lines(lines: list[str]) -> SeriesData:
    csv_stream = StringIO("\n".join(lines))
    raw_data = read_csv(
        csv_stream, header=None, sep=":", skipinitialspace=True, index_col=0
    )
    return df_to_series_data(raw_data.T)


@dataclass
class MeasurementSettings:
    measurement_mode: str
    measurement_type: MeasurementType
    wavelength_setting: float
    number_of_averages: float
    plate_identifier: str
    temperature: float

    @staticmethod
    def create(settings_lines: list[str], temperature: float) -> MeasurementSettings:
        settings = parse_settings_lines(settings_lines)
        raw_wavelength = settings[str, "Measurement wavelength"].split()[0]
        measurement_mode = settings[str, "Measurement mode"]

        return MeasurementSettings(
            measurement_mode=measurement_mode,
            measurement_type=get_measurement_type(measurement_mode),
            wavelength_setting=try_float(raw_wavelength, "Wavelength setting"),
            number_of_averages=settings[float, "Number of flashes"],
            plate_identifier=settings[str, "Plate definition file"].split(".")[0],
            temperature=temperature,
        )


@dataclass(frozen=True)
class MagellanMetadata:
    measurement_time: str
    analytical_method_identifier: str | None
    experimental_data_identifier: str | None
    analyst: str
    device_identifier: str
    equipment_serial_number: str
    measurements_settings: dict[str, MeasurementSettings]

    @classmethod
    def create(cls, metadata_lines: list[str]) -> MagellanMetadata:
        reader = LinesReader(metadata_lines)
        measurement_time = cls.parse_measurement_time(
            assert_not_none(reader.pop(), "Measurement Time")
        )
        analytical_method_identifier = cls._get_identifier_line(reader, r".*\.mth")
        experimental_data_identifier = cls._get_identifier_line(reader, r".*\.wsp")
        # skip wavelength lines
        reader.drop_until(r"^(?!\d+ ?nm).*$")
        analyst = assert_not_none(reader.pop(), "Analyst")
        device_identifier = assert_not_none(reader.pop(), "Device Identifier")
        raw_serial_number = assert_not_none(reader.pop(), "Equipment Serial Number")
        equipment_serial_number = raw_serial_number.split(": ")[1]

        return MagellanMetadata(
            measurement_time=measurement_time,
            analytical_method_identifier=analytical_method_identifier,
            experimental_data_identifier=experimental_data_identifier,
            analyst=analyst,
            device_identifier=device_identifier,
            equipment_serial_number=equipment_serial_number,
            measurements_settings=cls._get_measurements_settings(reader),
        )

    @classmethod
    def parse_measurement_time(cls, raw_datetime: str) -> str:
        if match := re.match(constants.MEASUREMENT_TIME_REGEX, raw_datetime):
            return f"{match.groups()[0]} {match.groups()[1]}"
        msg = "Unable to get measurement time from {raw_datetime}"
        raise AllotropeConversionError(msg)

    @classmethod
    def _get_identifier_line(cls, reader: LinesReader, match_pat: str) -> str | None:
        if lines := list(reader.pop_while(match_pat)):
            return lines[-1]
        return None

    @classmethod
    def _get_measurements_settings(
        cls, reader: LinesReader
    ) -> dict[str, MeasurementSettings]:
        settings_lines: list[list[str]] = []
        settings: dict[str, MeasurementSettings] = {}
        label_and_temps = []
        temp_line_re = r"Meas. temperature: (.+): ([\d\.]+) °C"

        while not re.match(temp_line_re, (first_line := assert_not_none(reader.get()))):
            if match := re.match(r"Measurement \d.", first_line):
                reader.pop()
            settings_lines.append(list(reader.pop_until_inclusive(r"Unit:.+")))

        while match := re.match(temp_line_re, assert_not_none(reader.pop())):
            label_and_temps.append(match.groups())

        if len(label_and_temps) != len(settings_lines):
            msg = "Number of temperatures does not match number of measurements."
            raise AllotropeConversionError(msg)

        for idx, lines in enumerate(settings_lines):
            label, temperature = label_and_temps[idx]
            settings[str(label)] = MeasurementSettings.create(
                lines, try_float(str(temperature), "Measurement temperature")
            )

        return settings


def create_metadata(data: MagellanMetadata, file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        unc_path=file_path,
        file_name=path.name,
        asm_file_identifier=path.with_suffix(".json").name,
        device_identifier=data.device_identifier,
        model_number=NOT_APPLICABLE,
        data_system_instance_id=NOT_APPLICABLE,
        software_name=constants.SOFTWARE_NAME,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        equipment_serial_number=data.equipment_serial_number,
    )


def create_measurement_groups(
    data: SeriesData, metadata: MagellanMetadata, well_count: float
) -> MeasurementGroup:
    measurements = []

    for measurement_label, settings in metadata.measurements_settings.items():
        errors = []
        if (measurement := data.get(float, measurement_label)) is None:
            measurement = NEGATIVE_ZERO
            errors = [
                ErrorDocument(
                    error=data[str, measurement_label],
                    error_feature=settings.measurement_mode,
                )
            ]

        location_identifier = data[str, "Well positions"]
        well_plate_identifier = data.get(str, "Plate", settings.plate_identifier)
        measurements.append(
            Measurement(
                type_=settings.measurement_type,
                device_type=constants.DEVICE_TYPE,
                identifier=random_uuid_str(),
                sample_identifier=f"{well_plate_identifier}_{location_identifier}",
                location_identifier=location_identifier,
                well_plate_identifier=well_plate_identifier,
                detection_type=settings.measurement_mode,
                compartment_temperature=settings.temperature,
                absorbance=measurement,
                number_of_averages=settings.number_of_averages,
                detector_wavelength_setting=settings.wavelength_setting,
                error_document=errors,
            )
        )

    return MeasurementGroup(
        measurements=measurements,
        plate_well_count=well_count,
        measurement_time=metadata.measurement_time,
        analyst=metadata.analyst,
        analytical_method_identifier=metadata.analytical_method_identifier,
        experimental_data_identifier=metadata.experimental_data_identifier,
    )
