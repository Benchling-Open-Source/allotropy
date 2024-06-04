# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import Optional

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    TransmittedLightSetting,
)
from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader
from allotropy.parsers.agilent_gen5_image.constants import (
    AUTOFOCUS_STRINGS,
    CHANNEL_HEADER_REGEX,
    DEFAULT_EXPORT_FORMAT_ERROR,
    DetectionType,
    DETECTOR_DISTANCE_REGEX,
    FILENAME_REGEX,
    HEADER_PREFIXES,
    ReadType,
    SETTINGS_SECTION_REGEX,
    TRANSMITTED_LIGHT_MAP,
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


def parse_settings(settings: list[str]) -> dict:
    """Returns a dictionary containing all key values identified in a list of settings.

    If there are additional (non key value) settings, they are also returned under the
    'non_kv_settings' key.

    Supported settings lines format:
        - key: value -> returned as {'key': 'value}
        - key1: value1, key2: value2, ... -> returned as {'key1': 'value1', key2', 'value2', ...}
        - Non keyvalue setting -> returned as {'non_kv_settings': ['Non keyvalue setting', ...]}
    """
    settings_dict: dict = {"non_kv_settings": []}
    for line in settings:
        strp_line = str(line.strip())

        line_data: list[str] = strp_line.split(", ")
        for read_datum in line_data:
            splitted_datum = read_datum.split(": ")
            if len(splitted_datum) == 1:
                settings_dict["non_kv_settings"].append(splitted_datum[0])
            elif len(splitted_datum) == 2:  # noqa: PLR2004
                settings_dict[splitted_datum[0]] = splitted_datum[1]

    return settings_dict


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


@dataclass
class InstrumentSettings:
    auto_focus: bool
    detector_distance: Optional[float]
    fluorescent_tag: Optional[str] = None
    excitation_wavelength: Optional[float] = None
    detector_wavelength: Optional[float] = None
    transmitted_light: Optional[TransmittedLightSetting] = None
    illumination: Optional[float] = None
    exposure_duration: Optional[float] = None
    detector_gain: Optional[str] = None

    @classmethod
    def create(cls, settings_lines: list[str]) -> InstrumentSettings:
        channel_settings = cls._get_channel_line_settings(settings_lines[0])

        settings_dict = parse_settings(settings_lines[1:])
        non_kv_settings = settings_dict["non_kv_settings"]

        if exposure_duration := settings_dict.get("Integration time"):
            exposure_duration = str(exposure_duration).split()[0]

        return InstrumentSettings(
            auto_focus=cls._get_auto_focus(non_kv_settings),
            detector_distance=cls._get_detector_distance(non_kv_settings),
            fluorescent_tag=channel_settings.get("fluorescent_tag"),
            excitation_wavelength=try_float_or_none(
                channel_settings.get("excitation_wavelength")
            ),
            detector_wavelength=try_float_or_none(
                channel_settings.get("detector_wavelength")
            ),
            transmitted_light=cls._get_transmitted_light(non_kv_settings),
            illumination=try_float_or_none(settings_dict.get("LED intensity")),
            exposure_duration=try_float_or_none(exposure_duration),
            detector_gain=settings_dict.get("Camera gain"),
        )

    @classmethod
    def _get_channel_line_settings(cls, settings_header: str) -> dict:
        if matches := re.match(CHANNEL_HEADER_REGEX, settings_header):
            return matches.groupdict()
        return {}

    @classmethod
    def _get_auto_focus(cls, settings: list[str]) -> bool:
        return any(str_ in settings for str_ in AUTOFOCUS_STRINGS)

    @classmethod
    def _get_detector_distance(cls, settings: list[str]) -> Optional[float]:
        if match := re.search(DETECTOR_DISTANCE_REGEX, "\n".join(settings)):
            return try_float(match.groups()[0], "Detector Distance")
        return None

    @classmethod
    def _get_transmitted_light(
        cls, settings: list[str]
    ) -> Optional[TransmittedLightSetting]:
        for line in settings:
            if line in TRANSMITTED_LIGHT_MAP:
                return TRANSMITTED_LIGHT_MAP[line]
        return None


@dataclass(frozen=True)
class ReadSection:
    image_mode: DetectionType
    magnification_setting: Optional[float]
    image_count_setting: Optional[float]
    instrument_settings_list: list[InstrumentSettings]

    @classmethod
    def create(cls, reader: LinesReader) -> ReadSection:
        top_read_lines = list(reader.pop_until(SETTINGS_SECTION_REGEX))

        detection_type = cls._get_detection_type("\n".join(top_read_lines))
        instrument_settings_list = cls._get_instrument_settings_list(reader)

        bottom_read_lines = list(reader.pop_until_empty())
        read_settings = parse_settings(top_read_lines + bottom_read_lines)

        if objective := read_settings.get("Objective"):
            objective = str(objective).replace("x", "")

        return ReadSection(
            image_mode=detection_type,
            magnification_setting=try_float_or_none(objective),
            image_count_setting=cls._get_image_count_setting(read_settings),
            instrument_settings_list=instrument_settings_list,
        )

    @classmethod
    def _get_detection_type(cls, read_chunk: str) -> DetectionType:
        if DetectionType.SINGLE_IMAGE.value in read_chunk:
            return DetectionType.SINGLE_IMAGE
        elif DetectionType.MONTAGE.value in read_chunk:
            return DetectionType.MONTAGE
        elif DetectionType.Z_STACK.value in read_chunk:
            return DetectionType.Z_STACK

        msg = f"Measurement mode not found; expected to find one of {sorted(DetectionType._member_names_)}."

        raise AllotropeConversionError(msg)

    @classmethod
    def _get_settings_sections(cls, reader: LinesReader) -> Iterator[list[str]]:
        while True:
            initial_line = reader.get() or ""
            if not re.search(SETTINGS_SECTION_REGEX, initial_line):
                break
            reader.pop()
            lines = [initial_line, *reader.pop_until(r"^\t\w")]
            yield lines

    @classmethod
    def _get_instrument_settings_list(
        cls, reader: LinesReader
    ) -> list[InstrumentSettings]:
        settings_list = []
        auto_focus = False
        for idx, settings_section in enumerate(cls._get_settings_sections(reader)):
            instrument_settings = InstrumentSettings.create(settings_section)
            # The autofocus setting is only reported in the first section but applies to all others
            if idx == 0:
                auto_focus = instrument_settings.auto_focus
            else:
                instrument_settings.auto_focus = auto_focus
            settings_list.append(instrument_settings)
        return settings_list

    @classmethod
    def _get_image_count_setting(cls, read_settings: dict) -> Optional[float]:
        montage_rows = read_settings.get("Montage rows")
        montage_columns = read_settings.get("columns")
        if montage_rows and montage_columns:
            return try_float(montage_rows, "Montage rows") * try_float(
                montage_columns, "Montage columns"
            )
        return None


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

        section_lines_reader = SectionLinesReader(procedure_details.splitlines())

        return ReadData(
            read_sections=[
                ReadSection.create(read_section)
                for read_section in section_lines_reader.iter_sections("^Read\t")
            ]
        )

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
class ImageFeature:
    identifier: str
    name: str
    result: JsonFloat


@dataclass(frozen=True)
class Results:
    image_features: dict[str, list[ImageFeature]]

    @staticmethod
    def create(results: str) -> Results:
        image_features = defaultdict(list)

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
            feature_name = values[-1]
            for col_num in range(1, len(values) - 1):
                well_position = f"{current_row}{col_num}"
                well_value = try_float_or_nan(values[col_num])

                image_features[well_position].append(
                    ImageFeature(
                        identifier=random_uuid_str(),
                        name=feature_name,
                        result=well_value,
                    )
                )

        return Results(image_features)


@dataclass(frozen=True)
class PlateData:
    header_data: HeaderData
    read_data: ReadData
    layout_data: LayoutData
    results: Results

    @staticmethod
    def create(reader: LinesReader, file_name: str) -> PlateData:
        header_data = HeaderData.create(reader, file_name)
        read_data = ReadData.create(reader)
        layout_data = LayoutData.create_default()
        results = None

        while reader.current_line_exists():
            data_section = read_data_section(reader)
            if data_section.startswith("Layout"):
                layout_data = LayoutData.create(data_section)
            elif data_section.startswith("Results"):
                results = Results.create(data_section)

        # If there is no results table, it might mean that the export format includes results in
        # separate tables, or that there are no results at all (also bad format)
        if results is None:
            raise AllotropeConversionError(DEFAULT_EXPORT_FORMAT_ERROR)

        return PlateData(
            header_data=header_data,
            read_data=read_data,
            layout_data=layout_data,
            results=results,
        )
