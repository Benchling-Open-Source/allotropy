# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import Optional

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader
from allotropy.parsers.agilent_gen5_image.constants import (
    CHANNEL_HEADER_REGEX,
    FILENAME_REGEX,
    HEADER_PREFIXES,
    DetectionType,
    ReadType,
    SETTINGS_SECTION_REGEX,
    UNSUPORTED_READ_TYPE_ERROR,
)
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_float_or_nan,
    try_float_or_none,
)


def read_data_section(reader: LinesReader) -> str:
    data_section = "\n".join(
        [
            reader.pop() or "",
            *reader.pop_until_empty(),
        ]
    )
    reader.drop_empty()
    return data_section


@dataclass(frozen=True)
class HeaderData:
    software_version: str
    experiment_file_path: str
    protocol_file_path: str
    datetime: str
    well_plate_identifier: str
    model_number: str
    equipment_serial_number: str

    @classmethod
    def create(cls, reader: LinesReader, file_name: str) -> HeaderData:
        assert_not_none(reader.drop_until("^Software Version"), "Software Version")
        metadata_dict = cls._parse_metadata(reader)
        datetime_ = cls._parse_datetime(metadata_dict["Date"], metadata_dict["Time"])
        plate_identifier = cls._get_identifier_from_filename_or_none(file_name)

        return HeaderData(
            software_version=metadata_dict["Software Version"],
            experiment_file_path=metadata_dict["Experiment File Path:"],
            protocol_file_path=metadata_dict["Protocol File Path:"],
            datetime=datetime_,
            well_plate_identifier=plate_identifier or metadata_dict["Plate Number"],
            model_number=metadata_dict["Reader Type:"],
            equipment_serial_number=metadata_dict["Reader Serial Number:"],
        )

    @classmethod
    def _parse_metadata(cls, reader: LinesReader) -> dict:
        metadata_dict: dict = {}
        for metadata_line in reader.pop_until("Procedure Details"):
            reader.drop_empty()
            line_split = metadata_line.split("\t")
            if line_split[0] not in HEADER_PREFIXES:
                msg = msg_for_error_on_unrecognized_value(
                    "metadata key", line_split[0], HEADER_PREFIXES
                )
                raise AllotropeConversionError(msg)
            try:
                metadata_dict[line_split[0]] = line_split[1]
            except IndexError:
                metadata_dict[line_split[0]] = ""

        return metadata_dict

    @classmethod
    def _parse_datetime(cls, date_: str, time_: str) -> str:
        return f"{date_} {time_}"

    @classmethod
    def _get_identifier_from_filename_or_none(cls, file_name: str) -> Optional[str]:
        matches = re.match(FILENAME_REGEX, file_name)
        if not matches:
            return None

        matches_dict = matches.groupdict()
        return matches_dict["plate_identifier"]


@dataclass(frozen=True)
class InstrumentSettings:
    fluorescent_tag_setting: Optional[str] = None
    excitation_wavelength_setting: Optional[float] = None
    detector_wavelength_setting: Optional[float] = None
    auto_focus_setting: bool = False
    detector_gain_setting: Optional[float] = None

    @classmethod
    def create(cls, settings_section: list[str]) -> InstrumentSettings:
        channel_line_settings = cls._get_channel_line_settings(settings_section[0])

        return InstrumentSettings(
            fluorescent_tag_setting=channel_line_settings.get("fluorescent_tag"),
            excitation_wavelength_setting=try_float_or_none(
                channel_line_settings.get("excitation_wavelength")
            ),
            detector_wavelength_setting=try_float_or_none(
                channel_line_settings.get("detector_wavelength")
            ),
        )

    @classmethod
    def _get_channel_line_settings(cls, settings_header: str) -> dict:
        if matches := re.match(CHANNEL_HEADER_REGEX, settings_header):
            return matches.groupdict()
        return {}


@dataclass(frozen=True)
class ReadSection:
    image_mode: DetectionType
    instrment_settings_list: list[InstrumentSettings]

    @classmethod
    def create(cls, reader: LinesReader) -> ReadSection:
        top_read_chunk = assert_not_none(
            reader.pop_until(SETTINGS_SECTION_REGEX),
            msg="Expected at least one Channel or Color Camera settings in the Read section.",
        )
        detection_type = cls.get_detection_type("\n".join(top_read_chunk))

        instrment_settings_list = [
            InstrumentSettings.create(settings_section)
            for settings_section in cls._get_settings_sections(reader)
        ]

        return ReadSection(
            image_mode=detection_type,
            instrment_settings_list=instrment_settings_list,
        )

    @property
    def auto_focus_setting(self):
        if not self.instrment_settings_list:
            return None
        return self.instrment_settings_list[0].auto_focus_setting

    @staticmethod
    def get_detection_type(read_chunk: str) -> DetectionType:
        if DetectionType.SINGLE_IMAGE.value in read_chunk:
            return DetectionType.SINGLE_IMAGE
        elif DetectionType.MONTAGE.value in read_chunk:
            return DetectionType.MONTAGE
        elif DetectionType.Z_STACKING.value in read_chunk:
            return DetectionType.Z_STACKING

        msg = f"Measurement mode not found; expected to find one of {sorted(DetectionType._member_names_)}."

        raise AllotropeConversionError(msg)

    def _get_settings_sections(reader: LinesReader) -> Iterator[list[str]]:
        while True:
            initial_line = reader.get()
            if not re.search(SETTINGS_SECTION_REGEX, initial_line):
                break
            lines = [reader.pop(), *reader.pop_until(r"^\t\w")]
            yield lines


@dataclass(frozen=True)
class ReadData:
    read_sections: list[ReadSection]

    @classmethod
    def create(cls, reader: LinesReader) -> ReadData:
        assert_not_none(reader.drop_until("^Procedure Details"), "Procedure Details")
        reader.pop()
        reader.drop_empty()
        procedure_details = read_data_section(reader)

        read_type = cls._get_read_type(procedure_details)
        if read_type != ReadType.IMAGE:
            raise AllotropeConversionError(UNSUPORTED_READ_TYPE_ERROR)

        # TODO: get read chunks and create a ReadSection object for each
        section_lines_reader = SectionLinesReader(procedure_details.splitlines())
        read_sections = []
        for read_section in section_lines_reader.iter_sections("^Read\t"):
            read_sections.append(ReadSection.create(read_section))

        return ReadData(read_sections=read_sections)

    @classmethod
    def _get_read_type(cls, procedure_details: str) -> ReadType:
        if ReadType.KINETIC.value in procedure_details:
            return ReadType.KINETIC
        elif ReadType.AREASCAN.value in procedure_details:
            return ReadType.AREASCAN
        elif ReadType.SPECTRAL.value in procedure_details:
            return ReadType.SPECTRAL
        elif ReadType.ENDPOINT.value in procedure_details:
            return ReadType.ENDPOINT
        elif ReadType.IMAGE.value in procedure_details:
            return ReadType.IMAGE

        msg = f"Read type not found; expected to find one of {sorted(ReadType._member_names_)}."
        raise AllotropeConversionError(msg)


@dataclass(frozen=True)
class LayoutData:
    sample_identifiers: dict

    @staticmethod
    def create_default() -> LayoutData:
        return LayoutData(sample_identifiers={})

    @staticmethod
    def create(layout_str: str) -> LayoutData:
        identifiers = {}

        layout_lines: list[str] = layout_str.splitlines()
        # first line is "Layout", second line is column numbers
        current_row = "A"
        for i in range(2, len(layout_lines)):
            split_line = layout_lines[i].split("\t")
            if split_line[0]:
                current_row = split_line[0]
            label = split_line[-1]
            for j in range(1, len(split_line) - 1):
                well_loc = f"{current_row}{j}"
                if label == "Name":
                    identifiers[well_loc] = split_line[j]
                elif label == "Well ID":
                    # give prevalence to the "Name" field if present
                    sample_id = identifiers.get(well_loc)
                    identifiers[well_loc] = sample_id if sample_id else split_line[j]

        return LayoutData(sample_identifiers=identifiers)


@dataclass(frozen=True)
class ActualTemperature:
    value: Optional[float] = None

    @staticmethod
    def create_default() -> ActualTemperature:
        return ActualTemperature()

    @staticmethod
    def create(actual_temperature: str) -> ActualTemperature:
        if len(actual_temperature.split("\n")) != 1:
            msg = f"Expected the Temperature section '{actual_temperature}' to contain exactly 1 line."
            raise AllotropeConversionError(msg)

        return ActualTemperature(
            value=try_float(
                actual_temperature.strip().split("\t")[-1], "Actual Temperature"
            ),
        )


@dataclass(frozen=True)
class Measurement:
    identifier: str
    value: JsonFloat
    label: str


@dataclass(frozen=True)
class Results:
    measurements: defaultdict[str, list[Measurement]]
    wells: list

    @staticmethod
    def create() -> Results:
        return Results(
            measurements=defaultdict(list),
            calculated_data=[],
            wells=[],
        )

    def parse_results(
        self,
        results: str,
    ) -> None:
        result_lines = results.splitlines()

        if result_lines[0].strip() != "Results":
            msg = f"Expected the first line of the results section '{result_lines[0]}' to be 'Results'."
            raise AllotropeConversionError(msg)

        # result_lines[1] contains column numbers
        current_row = "A"
        for row_num in range(2, len(result_lines)):
            values = result_lines[row_num].split("\t")
            if values[0]:
                current_row = values[0]
            label = values[-1]  # last column gives information about the type of read
            for col_num in range(1, len(values) - 1):
                well_pos = f"{current_row}{col_num}"
                if well_pos not in self.wells:
                    self.wells.append(well_pos)
                well_value = try_float_or_nan(values[col_num])

                self.measurements[well_pos].append(
                    Measurement(random_uuid_str(), well_value, label)
                )


@dataclass(frozen=True)
class PlateData:
    header_data: HeaderData
    read_data: list[ReadSection]
    layout_data: LayoutData
    results: Results

    @staticmethod
    def create(reader: LinesReader, file_name: str) -> PlateData:
        header_data = HeaderData.create(reader, file_name)
        read_data = ReadData.create(reader)
        layout_data = LayoutData.create_default()
        ActualTemperature.create_default()
        results = Results.create()

        while reader.current_line_exists():
            data_section = read_data_section(reader)
            if data_section.startswith("Layout"):
                layout_data = LayoutData.create(data_section)
            elif data_section.startswith("Results"):
                results.parse_results(
                    data_section,
                    read_data,
                )

        return PlateData(
            header_data=header_data,
            read_data=read_data,
            layout_data=layout_data,
            results=results,
        )
