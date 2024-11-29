from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.tecan_magellan import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_float


@dataclass
class MeasurementSettings:
    measurement_mode: MeasurementType
    wavelength_setting: float
    number_of_averages: float
    plate_identifier: str
    temperature: float

    @staticmethod
    def create(setting_lines: list[str], temperature: float) -> MeasurementSettings:
        # TODO: parse setting lines
        _ = setting_lines
        return MeasurementSettings(
            measurement_mode=MeasurementType.ULTRAVIOLET_ABSORBANCE,
            wavelength_setting=1,
            number_of_averages=1,
            plate_identifier="A123",
            temperature=temperature,
        )


@dataclass(frozen=True)
class MagellanMetadata:
    measurement_time: str
    analytical_method_identifier: str
    experimental_data_identifier: str
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
        reader.pop()
        analytical_method_identifier = assert_not_none(reader.pop())
        reader.pop()
        experimental_data_identifier = assert_not_none(reader.pop())
        # skip wavelengths
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
            measurements_settings=cls.get_measurements_settings(reader),
        )

    @classmethod
    def parse_measurement_time(cls, raw_datetime: str) -> str:
        if match := re.match(constants.MEASUREMENT_TIME_REGEX, raw_datetime):
            return f"{match.groups()[0]} {match.groups()[1]}"
        msg = "Unable to get measurement time from {raw_datetime}"
        raise AllotropeConversionError(msg)

    @classmethod
    def get_measurements_settings(
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
        asm_file_identifier=path.with_suffix("json").name,
        device_identifier=data.device_identifier,
        model_number=NOT_APPLICABLE,
        data_system_instance_id=NOT_APPLICABLE,
        software_name=constants.SOFTWARE_NAME,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        equipment_serial_number=data.equipment_serial_number,
    )


def create_measurement_groups(
    data: SeriesData, metadata: MagellanMetadata
) -> MeasurementGroup:
    # This function will be called for every row in the dataset, use it to create
    # a corresponding measurement group.
    return MeasurementGroup(
        analyst=data[str, "Analyst"],
        analytical_method_identifier=metadata.analytical_method_identifier,
        experimental_data_identifier=metadata.experimental_data_identifier,
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                # Example of the kind of value that might be set from a measurement row
                sample_identifier=data[str, "Sample ID"],
                viability=data[float, "Viability"],
            )
        ],
    )
