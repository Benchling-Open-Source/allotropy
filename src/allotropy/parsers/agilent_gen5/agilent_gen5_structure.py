from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
import math
from pathlib import Path
import re

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import (
    MilliAbsorbanceUnit,
    Nanometer,
    UNITLESS,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    ErrorDocument,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import (
    AllotropeConversionError,
    AllotropyParserError,
)
from allotropy.parsers.agilent_gen5.agilent_gen5_reader import AgilentGen5Reader
from allotropy.parsers.agilent_gen5.constants import (
    ALPHALISA_FLUORESCENCE_FOUND,
    DATA_SOURCE_FEATURE_VALUES,
    DEFAULT_SOFTWARE_NAME,
    DEVICE_TYPE,
    ELAPSED_TIME,
    EMISSION_KEY,
    EMISSION_START_KEY,
    EXCITATION_KEY,
    EXCITATION_START_KEY,
    FILENAME_REGEX,
    FIXED_EMISSION_KEY,
    FIXED_EXCITATION_KEY,
    GAIN_KEY,
    LIGHT_DIRECTIONS,
    MEASUREMENTS_DATA_POINT_KEY,
    MIRROR_KEY,
    NAN_EMISSION_EXCITATION,
    OPTICS_KEY,
    PATHLENGTH_CORRECTION_KEY,
    READ_DATA_MEASUREMENT_ERROR,
    READ_HEIGHT_KEY,
    READ_MODE_UNITS,
    READ_SPEED_KEY,
    ReadMode,
    ReadType,
    SECONDS,
    UNSUPPORTED_READ_MODE_ERROR,
    UNSUPPORTED_READ_TYPE_ERROR,
    WAVELENGTHS_KEY,
)
from allotropy.parsers.constants import (
    NEGATIVE_ZERO,
    NOT_APPLICABLE,
    POSSIBLE_WELL_COUNTS,
)
from allotropy.parsers.lines_reader import SectionLinesReader
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.pandas import read_csv, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float,
    try_float_or_none,
    try_non_nan_float_or_none,
)


@dataclass(frozen=True)
class HeaderData:
    datetime: str
    software_version: str
    experiment_file_path: str | None
    protocol_file_path: str | None
    well_plate_identifier: str | None
    model_number: str | None
    equipment_serial_number: str | None
    additional_data: dict[str, str | float | None]
    plate_well_count: float
    file_name: str
    unc_path: str

    @classmethod
    def create(cls, data: SeriesData, file_path: str) -> HeaderData:
        file_name = Path(file_path).name
        matches = re.match(FILENAME_REGEX, file_name)
        plate_identifier = matches.groupdict()["plate_identifier"] if matches else None
        plate_well_count = cls._extract_well_count(data[str, "Plate Type"])
        return HeaderData(
            software_version=data[str, "Software Version"],
            experiment_file_path=data.get(str, "Experiment File Path:"),
            file_name=file_name,
            unc_path=file_path,
            protocol_file_path=data.get(str, "Protocol File Path:"),
            datetime=f'{data[str, "Date"]} {data[str, "Time"]}',
            well_plate_identifier=plate_identifier or data.get(str, "Plate Number"),
            model_number=data.get(str, "Reader Type:"),
            equipment_serial_number=data.get(str, "Reader Serial Number:"),
            plate_well_count=plate_well_count,
            additional_data=data.get_unread(),
        )

    @staticmethod
    def _extract_well_count(plate_type: str) -> float:
        match = re.search(
            rf"({'|'.join(str(count) for count in POSSIBLE_WELL_COUNTS)})", plate_type
        )
        if match:
            return float(match.group())
        return 0


@dataclass(frozen=True)
class FilterSet:
    gain: str
    emission: str | None = None
    excitation: str | None = None
    mirror: str | None = None
    optics: str | None = None
    light_direction: str | None = None

    @property
    def detector_wavelength_setting(self) -> float | None:
        if not self.emission:
            return None
        return try_non_nan_float_or_none(self.emission.split("/")[0])

    @property
    def detector_bandwidth_setting(self) -> float | None:
        if not self.emission:
            return None
        try:
            return try_non_nan_float_or_none(self.emission.split("/")[1])
        except IndexError:
            return None

    @property
    def excitation_wavelength_setting(self) -> float | None:
        if self.excitation:
            return try_non_nan_float_or_none(self.excitation.split("/")[0])
        return None

    @property
    def excitation_bandwidth_setting(self) -> float | None:
        if not self.excitation:
            return None
        try:
            return try_float(self.excitation.split("/")[1], "Excitation bandwith")
        except IndexError:
            return None

    @property
    def wavelength_filter_cutoff_setting(self) -> float | None:
        if self.mirror:
            return try_float(self.mirror.split(" ")[1], "Wavelength filter cutoff")
        return None

    @property
    def scan_position_setting(self) -> ScanPositionSettingPlateReader | None:
        position_lookup = {
            "Top": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
            "Bottom": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
        }
        position = self.optics
        if self.mirror:
            position = self.mirror.split(" ")[0]

        # TODO: Raise if position is not a valid lookup value
        return position_lookup.get(position) if position is not None else None


@dataclass
class DeviceControlData:
    step_label: str | None
    _list_data: dict[str, list[str]]
    _single_data: dict[str, str]
    is_polarization: bool = False

    LIST_KEYS = frozenset(
        {
            EMISSION_KEY,
            EXCITATION_KEY,
            FIXED_EXCITATION_KEY,
            FIXED_EMISSION_KEY,
            EMISSION_START_KEY,
            EXCITATION_START_KEY,
            OPTICS_KEY,
            GAIN_KEY,
            MIRROR_KEY,
            WAVELENGTHS_KEY,
        }
    )

    def __init__(self) -> None:
        self.step_label = None
        self._list_data = {key: [] for key in self.LIST_KEYS}
        self._single_data = {}

    def add(self, key: str, value: str | list[str]) -> None:
        if key in self.LIST_KEYS:
            if isinstance(value, str):
                self._list_data[key].append(value)
            else:
                self._list_data[key].extend(value)
        else:
            if not isinstance(value, str):
                msg = f"Unexpected list passed to key: {key}"
                raise AllotropyParserError(msg)
            self._single_data[key] = value

    def get_list(self, key: str) -> list[str]:
        return self._list_data.get(key, [])

    def get(self, key: str) -> str | None:
        return self._single_data.get(key)

    @classmethod
    def create(cls, lines: list[str], read_mode: ReadMode) -> DeviceControlData:

        device_control_data = DeviceControlData()

        for line in lines:
            strp_line = str(line.strip())
            if strp_line == "Fluorescence Polarization":
                device_control_data.is_polarization = True
                continue

            if strp_line.startswith("Read\t"):
                device_control_data.step_label = cls._get_step_label(line, read_mode)
                continue

            elif strp_line.startswith(WAVELENGTHS_KEY):
                wavelengths = strp_line.split(":  ")
                device_control_data.add(WAVELENGTHS_KEY, wavelengths[1].split(", "))
                continue

            # Handle excitation/emission wavelengths in special patterns
            elif "Fixed Excitation:" in strp_line:
                fixed_excitation = strp_line.split("Fixed Excitation:")[1].strip()
                device_control_data.add(FIXED_EXCITATION_KEY, fixed_excitation)
                continue

            elif "Fixed Emission:" in strp_line:
                fixed_emission = strp_line.split("Fixed Emission:")[1].strip()
                device_control_data.add(FIXED_EMISSION_KEY, fixed_emission)
                continue

            elif "Emission Start:" in strp_line:
                emission_start = strp_line.split("Emission Start:")[1].strip()
                device_control_data.add(EMISSION_START_KEY, emission_start)
                continue

            elif "Excitation Start:" in strp_line:
                excitation_start = strp_line.split("Excitation Start:")[1].strip()
                device_control_data.add(EXCITATION_START_KEY, excitation_start)
                continue

            line_data: list[str] = strp_line.split(",  ")
            for read_datum in line_data:
                splitted_datum = read_datum.split(": ")
                if len(splitted_datum) != 2:
                    continue
                device_control_data.add(splitted_datum[0], splitted_datum[1])

        return device_control_data

    @classmethod
    def _get_step_label(cls, read_line: str, read_mode: str) -> str | None:
        split_line = read_line.strip().split("\t")
        if len(split_line) != 2:
            msg = (
                f"Expected the Read data line {split_line} to contain exactly 2 values."
            )
            raise AllotropeConversionError(msg)
        if split_line[1] != f"{read_mode.title()} Endpoint":
            return split_line[1]

        return None


@dataclass(frozen=True)
class KineticData:
    run_time: str | None
    interval: str | None
    reads: int | None

    @classmethod
    def create(cls, lines: list[str]) -> KineticData | None:
        for line in lines:
            if line.startswith("Start Kinetic\t"):
                return cls._parse_kinetic_section(line)
        return None

    @classmethod
    def _parse_kinetic_section(cls, line: str) -> KineticData:
        split_line = line.strip().split("\t")[1].split(", ")
        run_value = [part for part in split_line if "Runtime" in part]
        if len(run_value) != 1:
            msg = f"Could not find 'Runtime' in Kinetic line: {line}."
            raise AllotropeConversionError(msg)
        interval = [part for part in split_line if "Interval" in part]
        if len(interval) != 1:
            msg = f"Could not find 'Interval' in Kinetic line: {line}."
            raise AllotropeConversionError(msg)
        reads = [part for part in split_line if "Reads" in part]
        if len(reads) != 1:
            msg = f"Could not find 'Reads' in Kinetic line: {line}."
            raise AllotropeConversionError(msg)
        return KineticData(
            run_time=run_value[0].split(" ")[1].strip(),
            interval=interval[0].split(" ")[1].strip(),
            reads=int(reads[0].split(" ")[0].strip()),
        )


@dataclass(frozen=True)
class ReadData:
    read_mode: ReadMode
    read_type: ReadType
    measurement_labels: set[str]
    pathlength_correction: str | None
    step_label: str | None
    number_of_averages: float | None
    detector_distance: float | None
    detector_carriage_speed: str | None
    filter_sets: dict[str, FilterSet]
    is_emission: bool = False
    is_excitation: bool = False

    @classmethod
    def create(cls, lines: list[str]) -> list[ReadData]:
        procedure_details = "\n".join(lines)
        read_type = cls.get_read_type(procedure_details)
        if read_type == ReadType.AREASCAN:
            raise AllotropeConversionError(UNSUPPORTED_READ_TYPE_ERROR)
        read_modes = cls.get_read_modes(procedure_details)
        read_sections = list(SectionLinesReader(lines).iter_sections(r"^\s*Read\t"))
        if len(read_modes) != len(read_sections):
            msg = "Expected the number of read modes to match the number of read sections."
            raise AllotropeConversionError(msg)

        read_data_list: list[ReadData] = []
        for read_mode, read_section in zip(read_modes, read_sections, strict=True):
            device_control_data = DeviceControlData.create(
                read_section.lines, read_mode
            )
            measurement_labels, label_aliases = cls._get_measurement_labels(
                device_control_data, read_mode, read_type
            )
            all_labels = {
                alias for aliases in label_aliases.values() for alias in aliases
            }
            number_of_averages = device_control_data.get(MEASUREMENTS_DATA_POINT_KEY)
            read_height = device_control_data.get(READ_HEIGHT_KEY) or ""

            is_emission = bool(
                device_control_data.get_list(FIXED_EXCITATION_KEY)
            ) or "EM Spectrum" in "\n".join(read_section.lines)
            is_excitation = bool(
                device_control_data.get_list(FIXED_EMISSION_KEY)
            ) or "EX Spectrum" in "\n".join(read_section.lines)

            read_data_list.append(
                ReadData(
                    read_mode=read_mode,
                    read_type=read_type,
                    step_label=device_control_data.step_label,
                    measurement_labels=set(measurement_labels) | all_labels,
                    detector_carriage_speed=device_control_data.get(READ_SPEED_KEY),
                    # Absorbance attributes
                    pathlength_correction=device_control_data.get(
                        PATHLENGTH_CORRECTION_KEY
                    ),
                    number_of_averages=try_float_or_none(number_of_averages),
                    # Luminescence attributes
                    detector_distance=try_float_or_none(read_height.split(" ")[0]),
                    # Fluorescence attributes
                    filter_sets=cls._get_filter_sets(
                        measurement_labels,
                        label_aliases,
                        device_control_data,
                        read_mode,
                    ),
                    is_emission=is_emission,
                    is_excitation=is_excitation,
                )
            )
        return read_data_list

    @staticmethod
    def get_read_modes(procedure_details: str) -> list[ReadMode]:
        read_modes = []
        for read_mode in ReadMode:
            # Construct the regex pattern for the current read mode

            pattern = fr"\t{re.escape(read_mode.value)} (?:Endpoint|Spectrum)"
            # Use regex to find all occurrences of the read mode pattern in the procedure details
            matches = re.findall(pattern, procedure_details)
            if matches:
                # Add the read_mode to the list for each match found
                read_modes.extend([read_mode] * len(matches))

        if not read_modes:
            raise AllotropeConversionError(UNSUPPORTED_READ_MODE_ERROR)

        if ReadMode.ALPHALISA in read_modes and ReadMode.FLUORESCENCE in read_modes:
            raise AllotropeConversionError(ALPHALISA_FLUORESCENCE_FOUND)

        # Replace ALPHALISA with FLUORESCENCE
        read_modes = [
            ReadMode.FLUORESCENCE if read_mode == ReadMode.ALPHALISA else read_mode
            for read_mode in read_modes
        ]

        return read_modes

    @staticmethod
    def get_read_type(procedure_details: str) -> ReadType:
        if ReadType.AREASCAN.value in procedure_details:
            return ReadType.AREASCAN
        elif ReadType.SPECTRUM.value in procedure_details:
            return ReadType.SPECTRUM
        # check for this last, because other modes still contain the word "Endpoint"
        elif ReadType.ENDPOINT.value in procedure_details:
            return ReadType.ENDPOINT

        msg = f"Read type not found; expected to find one of {sorted(ReadType._member_names_)}."
        raise AllotropeConversionError(msg)

    @classmethod
    def _get_measurement_labels(
        cls, device_control_data: DeviceControlData, read_mode: str, read_type: str
    ) -> tuple[list[str], dict[str, set[str]]]:
        step_label = device_control_data.step_label
        label_prefix = f"{step_label}:" if step_label else ""
        measurement_labels = []
        # Some measurement labels may be reported in more than one format in the result rows, e.g.
        # fluorescence measurements may include bandwidths, or not: 360/40,460/40 or 360,460.
        label_aliases: dict[str, set[str]] = {}
        if read_mode == ReadMode.ABSORBANCE:
            measurement_labels = cls._get_absorbance_measurement_labels(
                label_prefix, device_control_data
            )
            if not measurement_labels and read_type == ReadType.SPECTRUM:
                measurement_labels = [f"{step_label}:Spectrum"]

        if read_mode == ReadMode.FLUORESCENCE:
            excitations: list[str] = (
                device_control_data.get_list(EXCITATION_KEY)
                or device_control_data.get_list(FIXED_EXCITATION_KEY)
                or device_control_data.get_list(EXCITATION_START_KEY)
            )
            emissions: list[str] = (
                device_control_data.get_list(EMISSION_KEY)
                or device_control_data.get_list(FIXED_EMISSION_KEY)
                or device_control_data.get_list(EMISSION_START_KEY)
            )

            measurement_labels = [
                f"{label_prefix}{excitation},{emission}"
                for excitation, emission in zip(excitations, emissions, strict=True)
            ]
            if device_control_data.is_polarization:
                if len(measurement_labels) != 2:
                    msg = "Expected the Fluorescence Polarization read mode to contain exactly 2 filter sets."
                    raise AllotropeConversionError(msg)
                measurement_labels = [
                    f"{label} [{light_direction}]"
                    for label, light_direction in zip(
                        measurement_labels, LIGHT_DIRECTIONS, strict=True
                    )
                ]
                label_aliases = {}
            else:
                label_aliases = {
                    f"{label_prefix}{excitation},{emission}": {
                        f"{label_prefix}{excitation.split('/')[0]},{emission.split('/')[0]}"
                    }
                    for excitation, emission in zip(excitations, emissions, strict=True)
                }

            if not measurement_labels:
                measurement_labels = ["Alpha"]

        if read_mode == ReadMode.LUMINESCENCE:
            emissions = (
                device_control_data.get_list(EMISSION_KEY)
                or device_control_data.get_list(FIXED_EMISSION_KEY)
                or device_control_data.get_list(EMISSION_START_KEY)
            )
            for emission in emissions:
                label = "Lum" if emission in NAN_EMISSION_EXCITATION else emission
                measurement_labels.append(f"{label_prefix}{label}")

        return measurement_labels, label_aliases

    @classmethod
    def _get_absorbance_measurement_labels(
        cls, label_prefix: str | None, device_control_data: DeviceControlData
    ) -> list[str]:
        pathlength_correction = device_control_data.get(PATHLENGTH_CORRECTION_KEY)
        measurement_labels = []

        for wavelength in device_control_data.get_list(WAVELENGTHS_KEY):
            label = f"{label_prefix}{wavelength}"
            measurement_labels.append(label)

        if pathlength_correction:
            test, ref = pathlength_correction.split(" / ")
            test_label = f"{label_prefix}{test} [Test]"
            ref_label = f"{label_prefix}{ref} [Ref]"
            measurement_labels.extend([test_label, ref_label])

        return measurement_labels

    @classmethod
    def _get_filter_sets(
        cls,
        measurement_labels: list[str],
        label_aliases: dict[str, set[str]],
        device_control_data: DeviceControlData,
        read_mode: ReadMode,
    ) -> dict[str, FilterSet]:
        filter_data: dict[str, FilterSet] = {}
        if read_mode == ReadMode.ABSORBANCE:
            return filter_data

        emissions = device_control_data.get_list(EMISSION_KEY)
        excitations = device_control_data.get_list(EXCITATION_KEY)
        fixed_emissions = device_control_data.get_list(FIXED_EMISSION_KEY)
        fixed_excitations = device_control_data.get_list(FIXED_EXCITATION_KEY)
        emission_start = device_control_data.get_list(EMISSION_START_KEY)
        excitation_start = device_control_data.get_list(EXCITATION_START_KEY)
        mirrors = device_control_data.get_list(MIRROR_KEY)
        optics = device_control_data.get_list(OPTICS_KEY)
        gains = device_control_data.get_list(GAIN_KEY)

        if len(measurement_labels) != len(gains):
            msg = f"Expected the number of measurement labels: {measurement_labels} to match the number of gains: {gains}."
            raise AllotropeConversionError(msg)

        for idx, label in enumerate(measurement_labels):
            mirror = None
            if mirrors and read_mode == ReadMode.FLUORESCENCE:
                mirror = mirrors[idx]

            # Logic to determine which emission/excitation value to use
            excitation = None
            if idx < len(excitations) and excitations:
                excitation = excitations[idx]
            elif idx < len(fixed_excitations) and fixed_excitations:
                excitation = fixed_excitations[idx]
            elif idx < len(excitation_start) and excitation_start:
                excitation = excitation_start[idx]

            emission = None
            if idx < len(emissions) and emissions:
                emission = emissions[idx]
            elif idx < len(fixed_emissions) and fixed_emissions:
                emission = fixed_emissions[idx]
            elif idx < len(emission_start) and emission_start:
                emission = emission_start[idx]

            if excitation and " nm" in excitation:
                excitation = excitation.split(" nm")[0]
            if emission and " nm" in emission:
                emission = emission.split(" nm")[0]

            filter_data[label] = FilterSet(
                emission=emission,
                gain=gains[idx],
                excitation=excitation,
                mirror=mirror,
                optics=optics[idx] if optics else None,
                light_direction=(
                    LIGHT_DIRECTIONS[idx]
                    if device_control_data.is_polarization
                    else None
                ),
            )
        for measurement_label, aliases in label_aliases.items():
            for alias in aliases:
                filter_data[alias] = filter_data[measurement_label]

        return filter_data


def _validate_result_sections(result_sections: list[list[str]]) -> None:
    """Validates whether all the result sections dimensions are consistent."""
    first_section = result_sections[0]

    for section in result_sections[1:]:
        if not first_section[0] == section[0] and len(first_section) == len(section):
            msg = "All result tables should have the same dimensions."
            raise AllotropeConversionError(msg)


def get_results_section(reader: AgilentGen5Reader) -> list[str] | None:
    """Returns a valid Results Matrix from the reader sections if found.

    Checks for Results in the reader sections, if not found, creates the results matrix with all
    sections that are correctly formatted as a results table (excluding the Layout section). If
    no tables with results are found, returns None
    """
    if "Results" in reader.sections:
        return reader.sections["Results"]

    def is_results(section: list[str]) -> bool:
        return (
            len(section) > 2
            and section[1].startswith("\t1")
            and section[2].startswith("A\t")
        )

    result_sections = []
    for name, section in reader.sections.items():
        if name == "Layout":
            continue
        if is_results(section):
            result_sections.append(section[1:])

    if result_sections:
        _validate_result_sections(result_sections)
        return [
            "Results",
            result_sections[0][0],
            *[
                section[i + 1]
                for i in range(len(result_sections[0]) - 1)
                for section in result_sections
            ],
        ]

    return None


def get_concentrations(layout_lines: list[str] | None) -> dict[str, float | None]:
    """Extract concentration/dilution values from the Layout section.

    Returns a dictionary mapping well positions to their concentration/dilution values.
    """
    if not layout_lines:
        return {}

    # Create dataframe from tabular data and forward fill empty values in index
    data = read_csv(StringIO("\n".join(layout_lines[1:])), sep="\t")
    data = data.set_index(data.index.to_series().ffill(axis="index").values)

    concentrations = {}
    for row_name, row in data.iterrows():
        label = row.iloc[-1]
        if label == "Conc/Dil":
            for col_index, col in enumerate(row.iloc[:-1]):
                well_pos = f"{row_name}{col_index + 1}"
                # Convert to float if possible
                if not pd.isna(col):
                    concentration_value = try_float_or_none(col)
                    concentrations[well_pos] = concentration_value
                else:
                    concentrations[well_pos] = None

    return concentrations


def get_identifiers(layout_lines: list[str] | None) -> dict[str, str]:
    if not layout_lines:
        return {}
    # Create dataframe from tabular data and forward fill empty values in index
    data = read_csv(StringIO("\n".join(layout_lines[1:])), sep="\t")
    data = data.set_index(data.index.to_series().ffill(axis="index").values)

    identifiers = {}
    for row_name, row in data.iterrows():
        label = row.iloc[-1]
        for col_index, col in enumerate(row.iloc[:-1]):
            well_pos = f"{row_name}{col_index + 1}"
            # Prefer Name to Well ID
            if not pd.isna(col) and (
                label == "Name" or label == "Well ID" and well_pos not in identifiers
            ):
                identifiers[well_pos] = col
    return identifiers


def get_temperature(actual_temperature_lines: list[str] | None) -> float | None:
    if not actual_temperature_lines:
        return None
    if len(actual_temperature_lines) != 1:
        msg = f"Expected the Temperature section '{actual_temperature_lines}' to contain exactly 1 line."
        raise AllotropeConversionError(msg)

    return try_float(
        actual_temperature_lines[0].strip().split("\t")[-1], "Actual Temperature"
    )


def get_kinetic_measurements(
    kinetic_lines: list[str] | None,
) -> tuple[
    dict[str, list[float | None]], list[float], dict[str, list[ErrorDocument]]
] | None:
    if not kinetic_lines:
        return None
    data = (
        read_csv(StringIO("\n".join(kinetic_lines)), sep="\t", index_col=0)
        .dropna(axis="columns", how="all")
        .dropna(axis="index", how="all")
    )

    kinetic_measurements: defaultdict[str, list[float | None]] = defaultdict(
        list[float | None]
    )
    kinetic_elapsed_time: list[float] = data.index.map(
        lambda val: _convert_time_to_seconds(str(val))
    ).to_list()

    error_documents: dict[str, list[ErrorDocument]] = {}

    for col_name, column in data.items():
        well_values: list[float | None] = []
        for idx, value in enumerate(column):
            # Handle empty values
            if pd.isna(value):
                well_values.append(None)
                continue

            try:
                float_value = float(value)
                well_values.append(float_value)
            except (ValueError, TypeError):
                if value is not None:
                    str_value = (
                        str(value).strip()
                        if not isinstance(value, str)
                        else value.strip()
                    )
                    if str_value:  # Only create error for non-empty values
                        time_point = (
                            kinetic_elapsed_time[idx]
                            if idx < len(kinetic_elapsed_time)
                            else None
                        )

                        if str(col_name) not in error_documents:
                            error_documents[str(col_name)] = []

                        error_documents[str(col_name)].append(
                            ErrorDocument(
                                error=str_value,
                                error_feature=f"{time_point}s",
                            )
                        )
                # Use NEGATIVE_ZERO for non-numeric values
                well_values.append(NEGATIVE_ZERO)

        kinetic_measurements[str(col_name)] = well_values

    return dict(kinetic_measurements.items()), kinetic_elapsed_time, error_documents


@dataclass(frozen=True)
class MeasurementData:
    identifier: str
    value: float | None
    label: str


def create_results(
    result_lines: list[str],
    header_data: HeaderData,
    read_data: list[ReadData],
    sample_identifiers: dict[str, str],
    actual_temperature: float | None,
    concentration_values: dict[str, float | None] | None = None,
) -> tuple[list[MeasurementGroup], list[CalculatedDocument]]:
    if result_lines[0].strip() != "Results":
        msg = f"Expected the first line of the results section '{result_lines[0]}' to be 'Results'."
        raise AllotropeConversionError(msg)

    # Create dataframe from tabular data and forward fill empty values in index
    data = read_csv(StringIO("\n".join(result_lines[1:])), sep="\t")
    data = data.set_index(data.index.to_series().ffill(axis="index").values)

    well_to_measurements: defaultdict[str, list[MeasurementData]] = defaultdict(
        list[MeasurementData]
    )
    calculated_data: defaultdict[str, list[tuple[str, float]]] = defaultdict(
        list[tuple[str, float]]
    )
    measurement_labels = [
        label for r_data in read_data for label in r_data.measurement_labels
    ]
    error_documents_per_well: defaultdict[str, list[ErrorDocument]] = defaultdict(
        list[ErrorDocument]
    )
    for row_name, row in data.iterrows():
        label = str(row.iloc[-1])
        is_measurement = label in measurement_labels
        for col_index, value in enumerate(row.iloc[:-1]):
            well_pos = f"{row_name}{col_index + 1}"
            well_value = try_float_or_none(value)
            # skip empty values
            if isinstance(well_value, float) and math.isnan(well_value):
                continue

            # Report error documents for NaN values
            if well_value is None:
                error_documents_per_well[well_pos].append(
                    ErrorDocument(
                        error=value,
                        # TODO Add support for multiple read modes
                        error_feature=(
                            read_data[0].read_mode.lower() if is_measurement else label
                        ),
                    )
                )
            if is_measurement:

                well_to_measurements[well_pos].append(
                    MeasurementData(
                        random_uuid_str(),
                        NEGATIVE_ZERO if well_value is None else well_value,
                        label,
                    )
                )
            elif well_value is not None:
                calculated_data[well_pos].append((label, well_value))

    groups = [
        MeasurementGroup(
            measurement_time=header_data.datetime,
            plate_well_count=len(set(data.index.tolist()))
            * len(set(data.columns[1:].tolist())),
            measurements=[
                _create_measurement(
                    measurement,
                    well_position,
                    header_data,
                    get_read_data_from_measurement(measurement, read_data),
                    sample_identifiers.get(well_position),
                    actual_temperature,
                    error_documents=error_documents_per_well.get(well_position),
                    concentration_value=concentration_values.get(well_position)
                    if concentration_values
                    else None,
                )
                for measurement in measurements
            ],
        )
        for well_position, measurements in well_to_measurements.items()
    ]

    calculated_data_items = [
        CalculatedDocument(
            uuid=random_uuid_str(),
            data_sources=[
                DataSource(
                    reference=Referenceable(measurement.identifier),
                    feature=item.read_mode.value.lower(),
                )
                for measurement in _get_sources(
                    label, well_to_measurements[well_position]
                )
                for item in read_data
            ],
            unit=UNITLESS,
            name=label,
            value=value,
        )
        for well_position, well_calculated_data in calculated_data.items()
        for label, value in well_calculated_data
    ]

    return groups, calculated_data_items


def create_kinetic_results(
    result_lines: list[str],
    header_data: HeaderData,
    read_data: list[ReadData],
    sample_identifiers: dict[str, str],
    actual_temperature: float | None,
    kinetic_data: KineticData,
    kinetic_measurements: dict[str, list[float | None]],
    kinetic_elapsed_time: list[float],
    kinetic_errors: dict[str, list[ErrorDocument]] | None = None,
    concentration_values: dict[str, float | None] | None = None,
) -> tuple[list[MeasurementGroup], list[CalculatedDocument]]:
    if result_lines[0].strip() != "Results":
        msg = f"Expected the first line of the results section '{result_lines[0]}' to be 'Results'."
        raise AllotropeConversionError(msg)

    # Create dataframe from tabular data and forward fill empty values in index
    data = read_csv(StringIO("\n".join(result_lines[1:])), sep="\t")
    data = data.set_index(data.index.to_series().ffill(axis="index").values)

    calculated_data: defaultdict[str, list[tuple[str, float]]] = defaultdict(
        list[tuple[str, float]]
    )
    measurement_labels = [
        label for r_data in read_data for label in r_data.measurement_labels
    ]

    error_documents_per_well: defaultdict[str, list[ErrorDocument]] = defaultdict(list)

    if kinetic_errors:
        for well, errors in kinetic_errors.items():
            error_documents_per_well[well].extend(errors)

    for row_name, row in data.iterrows():
        label = row.iloc[-1]
        for col_index, value in enumerate(row.iloc[:-1]):
            well_pos = f"{row_name}{col_index + 1}"
            well_value = try_non_nan_float_or_none(value)
            # TODO: Report error documents for NaN values
            if not well_value:
                continue
            calculated_data[well_pos].append((label, well_value))

    groups = [
        MeasurementGroup(
            measurement_time=header_data.datetime,
            plate_well_count=len(set(data.index.tolist()))
            * len(set(data.columns[1:].tolist())),
            measurements=[
                _create_measurement(
                    measurement := MeasurementData(
                        random_uuid_str(), None, measurement_labels[0]
                    ),
                    well_position,
                    header_data,
                    get_read_data_from_measurement(measurement, read_data),
                    sample_identifiers.get(well_position),
                    actual_temperature,
                    kinetic_data,
                    kinetic_measurements[well_position],
                    kinetic_elapsed_time,
                    error_documents_per_well.get(well_position, []),
                    concentration_value=concentration_values.get(well_position)
                    if concentration_values
                    else None,
                )
            ],
        )
        for well_position in calculated_data.keys()
    ]

    groups_by_well_position = {
        group.measurements[0].location_identifier: group for group in groups
    }

    calculated_data_items = [
        CalculatedDocument(
            uuid=random_uuid_str(),
            data_sources=[
                DataSource(
                    reference=Referenceable(
                        groups_by_well_position[well_position]
                        .measurements[0]
                        .identifier
                    ),
                    # TODO: Add support for multiple kinetic sections
                    feature=DATA_SOURCE_FEATURE_VALUES[read_data[0].read_mode],
                )
            ],
            unit=UNITLESS,
            name=label,
            value=value,
        )
        for well_position, well_calculated_data in calculated_data.items()
        for label, value in well_calculated_data
    ]

    return groups, calculated_data_items


def get_read_data_from_measurement(
    measurement: MeasurementData, read_data_list: list[ReadData]
) -> ReadData:
    for read_data in read_data_list:
        if _is_label_in_measurement_labels(
            measurement.label, read_data.measurement_labels
        ):
            return read_data

    raise AllotropeConversionError(
        READ_DATA_MEASUREMENT_ERROR.format(measurement.label)
    )


def _get_sources(
    calculated_data_label: str, measurements: list[MeasurementData]
) -> list[MeasurementData]:
    # Pathlength is a special case, its sources are always determined
    # by the pathlength correction setting
    if calculated_data_label.split(":")[-1] == "Pathlength":
        pathlength_suffixes = ["[Test]", "[Ref]"]
        sources = [
            measurement
            for measurement in measurements
            if measurement.label.split(" ")[-1] in pathlength_suffixes
        ]
    else:
        sources = [
            measurement
            for measurement in measurements
            if measurement.label in calculated_data_label
        ]
    # if there are no matches in the measurement labels, use all measurements as source
    return sources or measurements


def create_metadata(header_data: HeaderData) -> Metadata:
    asm_file_identifier = Path(header_data.file_name).with_suffix(".json")
    return Metadata(
        device_identifier=NOT_APPLICABLE,
        model_number=header_data.model_number or NOT_APPLICABLE,
        equipment_serial_number=header_data.equipment_serial_number,
        software_name=DEFAULT_SOFTWARE_NAME,
        software_version=header_data.software_version,
        file_name=header_data.file_name,
        asm_file_identifier=asm_file_identifier.name,
        data_system_instance_id=NOT_APPLICABLE,
        unc_path=header_data.unc_path,
    )


def create_calculated_data_documents(
    results_section: list[str] | None,
    read_data: ReadData,
    measurements: list[Measurement],
) -> tuple[list[CalculatedDocument], dict[str, list[ErrorDocument]]]:
    calculated_data = []
    error_documents_by_well: defaultdict[str, list[ErrorDocument]] = defaultdict(list)
    if results_section:
        if results_section[0].strip() != "Results":
            return [], {}

        data = read_csv(StringIO("\n".join(results_section[1:])), sep="\t")

        calculated_data_by_well = defaultdict(list)
        for row_name, row in data.iterrows():
            label = str(row.iloc[-1])
            # Skip rows containing measurement data
            if label in read_data.measurement_labels:
                continue

            for col_index, value in enumerate(row.iloc[:-1]):
                well_pos = f"{row_name}{col_index + 1}"
                well_value = try_float_or_none(value)

                # Handle numeric values
                if well_value is not None and not math.isnan(well_value):
                    calculated_data_by_well[well_pos].append((label, well_value))
                    continue

                # Handle empty cells
                if pd.isna(value) or value is None or str(value).strip() == "":
                    continue

                # Handle non-numeric error values
                error_documents_by_well[well_pos].append(
                    ErrorDocument(
                        error=str(value).strip(),
                        error_feature=label,
                    )
                )
                calculated_data_by_well[well_pos].append((label, NEGATIVE_ZERO))

        well_to_measurement_id = {
            measurement.location_identifier: measurement.identifier
            for measurement in measurements
        }

        for well_position, well_calculated_data in calculated_data_by_well.items():
            for label, value in well_calculated_data:
                calculated_data.append(
                    CalculatedDocument(
                        uuid=random_uuid_str(),
                        data_sources=[
                            DataSource(
                                reference=Referenceable(
                                    well_to_measurement_id[well_position]
                                ),
                                feature=read_data.read_mode.value.lower(),
                            )
                        ],
                        unit=UNITLESS,
                        name=label,
                        value=value,
                    )
                )
    return calculated_data, error_documents_by_well


def create_spectrum_results(
    header_data: HeaderData,
    read_data_list: list[ReadData],
    wavelengths_sections: list[str] | None,
    sample_identifiers: dict[str, str],
    actual_temperature: float | None,
    results_section: list[str] | None = None,
    concentration_values: dict[str, float | None] | None = None,
) -> tuple[list[MeasurementGroup], list[CalculatedDocument]]:
    if not wavelengths_sections:
        return [], []

    data = read_csv(StringIO("\n".join(wavelengths_sections)), sep="\t")

    try:
        wavelengths = data["Wavelength"].astype(float).tolist()
    except (ValueError, KeyError):
        return [], []

    wells_data = {}
    error_documents_by_well = {}

    for column in data.columns:
        if column == "Wavelength":
            continue

        well_values = []
        errors = []
        for idx, value in enumerate(data[column]):
            try:
                float_value = float(value)
                if math.isnan(float_value):
                    continue
                well_values.append(float_value)
            except (ValueError, TypeError):
                original_value = str(value).strip()
                if original_value:
                    wavelength = wavelengths[idx] if idx < len(wavelengths) else None
                    errors.append(
                        ErrorDocument(
                            error=original_value,
                            error_feature=f"{wavelength}nm",
                        )
                    )
                well_values.append(NEGATIVE_ZERO)

        # Skip empty wells
        if not well_values:
            continue

        wells_data[column] = well_values
        if errors:
            error_documents_by_well[column] = errors

    if not wells_data:
        return [], []

    read_data = read_data_list[0]
    if not read_data:
        return [], []

    measurements = []
    if read_data.read_mode == ReadMode.ABSORBANCE:
        measurement_type = MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_SPECTRUM
    elif read_data.read_mode == ReadMode.FLUORESCENCE and read_data.is_emission:
        measurement_type = MeasurementType.EMISSION_FLUORESCENCE_CUBE_SPECTRUM
    elif read_data.read_mode == ReadMode.FLUORESCENCE and read_data.is_excitation:
        measurement_type = MeasurementType.EXCITATION_FLUORESCENCE_CUBE_SPECTRUM
    elif read_data.read_mode == ReadMode.FLUORESCENCE:
        # Default to emission if not specified
        measurement_type = MeasurementType.EMISSION_FLUORESCENCE_CUBE_SPECTRUM
    elif read_data.read_mode == ReadMode.LUMINESCENCE and read_data.is_emission:
        measurement_type = MeasurementType.EMISSION_LUMINESCENCE_CUBE_SPECTRUM
    elif read_data.read_mode == ReadMode.LUMINESCENCE and read_data.is_excitation:
        measurement_type = MeasurementType.EXCITATION_LUMINESCENCE_CUBE_SPECTRUM
    elif read_data.read_mode == ReadMode.LUMINESCENCE:
        # Default to emission if not specified
        measurement_type = MeasurementType.EMISSION_LUMINESCENCE_CUBE_SPECTRUM
    else:
        msg = f"Unsupported read mode: {read_data.read_mode}"
        raise AllotropeConversionError(msg)

    # Extract wavelength settings from filter sets
    filter_set = None
    if read_data.filter_sets:
        filter_set = next(iter(read_data.filter_sets.values()))

    detector_wavelength_setting = (
        filter_set.detector_wavelength_setting
        if filter_set and read_data.is_excitation
        else None
    )
    detector_bandwidth_setting = (
        filter_set.detector_bandwidth_setting if filter_set else None
    )
    excitation_wavelength_setting = (
        filter_set.excitation_wavelength_setting
        if filter_set and read_data.is_emission
        else None
    )
    excitation_bandwidth_setting = (
        filter_set.excitation_bandwidth_setting if filter_set else None
    )

    # Special case for luminescence spectrum
    if read_data.read_mode == ReadMode.LUMINESCENCE:
        excitation_wavelength_setting = 480.0
        excitation_bandwidth_setting = 20.0

    for well_position, well_absorbance_data in wells_data.items():
        if measurement_type == MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_SPECTRUM:
            label = "absorbance-spectrum"
        elif measurement_type in (
            MeasurementType.EMISSION_FLUORESCENCE_CUBE_SPECTRUM,
            MeasurementType.EXCITATION_FLUORESCENCE_CUBE_SPECTRUM,
        ):
            label = "fluorescence-spectrum"
        elif measurement_type in (
            MeasurementType.EMISSION_LUMINESCENCE_CUBE_SPECTRUM,
            MeasurementType.EXCITATION_LUMINESCENCE_CUBE_SPECTRUM,
        ):
            label = "luminescence-spectrum"
        else:
            label = "spectrum"

        spectrum_data_cube = DataCube(
            label=label,
            structure_dimensions=[
                DataCubeComponent(
                    concept="wavelength",
                    type_=FieldComponentDatatype.double,
                    unit=Nanometer.unit,
                )
            ],
            structure_measures=[
                DataCubeComponent(
                    concept="absorbance",
                    type_=FieldComponentDatatype.double,
                    unit=MilliAbsorbanceUnit.unit,
                )
            ],
            dimensions=[wavelengths],
            measures=[well_absorbance_data],
        )

        measurement = Measurement(
            type_=measurement_type,
            device_type=DEVICE_TYPE,
            identifier=random_uuid_str(),
            sample_identifier=sample_identifiers.get(well_position)
            or f"{header_data.well_plate_identifier} {well_position}",
            location_identifier=well_position,
            well_plate_identifier=header_data.well_plate_identifier,
            detection_type=read_data.read_mode.value,
            detector_wavelength_setting=detector_wavelength_setting,
            detector_bandwidth_setting=detector_bandwidth_setting,
            excitation_wavelength_setting=excitation_wavelength_setting,
            excitation_bandwidth_setting=excitation_bandwidth_setting,
            compartment_temperature=actual_temperature,
            spectrum_data_cube=spectrum_data_cube,
            number_of_averages=read_data.number_of_averages,
            detector_carriage_speed=read_data.detector_carriage_speed,
            detector_distance_setting=read_data.detector_distance,
            scan_position_setting=filter_set.scan_position_setting
            if filter_set
            else None,
            detector_gain_setting=filter_set.gain if filter_set else None,
            error_document=error_documents_by_well.get(well_position),
            sample_custom_info={
                "Conc/Dil": concentration_values.get(well_position)
                if concentration_values
                else None,
            },
            analytical_method_identifier=header_data.protocol_file_path
            if header_data.protocol_file_path
            else None,
            experimental_data_identifier=header_data.experiment_file_path
            if header_data.experiment_file_path
            else None,
        )

        measurements.append(measurement)

    calculated_data, calculated_data_errors = create_calculated_data_documents(
        results_section, read_data_list[0], measurements
    )

    # Add calculated data errors to measurement error documents
    for well_position, errors in calculated_data_errors.items():
        for measurement in measurements:
            if measurement.location_identifier == well_position:
                if measurement.error_document:
                    measurement.error_document.extend(errors)
                else:
                    measurement.error_document = errors

    measurement_groups = [
        MeasurementGroup(
            measurement_time=header_data.datetime,
            plate_well_count=header_data.plate_well_count,
            measurements=[measurement],
        )
        for measurement in measurements
    ]

    return measurement_groups, calculated_data


def _is_label_in_measurement_labels(label: str, measurement_labels: set[str]) -> bool:
    if not measurement_labels:
        return False
    if label in measurement_labels:
        return True
    # TODO Improve this logic to support multiple kinetic sections
    match = re.search(r"\[(\d+)]", label)
    if match and match.group()[1:-1] in measurement_labels:
        return True
    return False


def _create_measurement(
    measurement: MeasurementData,
    well_position: str,
    header_data: HeaderData,
    read_data: ReadData,
    sample_identifier: str | None,
    actual_temperature: float | None,
    kinetic_data: KineticData | None = None,
    kinetic_measurements: list[float | None] | None = None,
    kinetic_elapsed_time: list[float] | None = None,
    error_documents: list[ErrorDocument] | None = None,
    concentration_value: float | None = None,
) -> Measurement:
    if read_data.read_mode == ReadMode.ABSORBANCE and not kinetic_data:
        measurement_type = MeasurementType.ULTRAVIOLET_ABSORBANCE
    elif read_data.read_mode == ReadMode.FLUORESCENCE and not kinetic_data:
        measurement_type = MeasurementType.FLUORESCENCE
    elif read_data.read_mode == ReadMode.LUMINESCENCE and not kinetic_data:
        measurement_type = MeasurementType.LUMINESCENCE
    elif read_data.read_mode == ReadMode.ABSORBANCE and kinetic_data:
        measurement_type = MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_DETECTOR
    elif read_data.read_mode == ReadMode.FLUORESCENCE and kinetic_data:
        measurement_type = MeasurementType.FLUORESCENCE_CUBE_DETECTOR
    elif read_data.read_mode == ReadMode.LUMINESCENCE and kinetic_data:
        measurement_type = MeasurementType.LUMINESCENCE_CUBE_DETECTOR

    if measurement_type in [
        MeasurementType.ULTRAVIOLET_ABSORBANCE,
        MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_DETECTOR,
    ]:
        filter_data = None
        detector_wavelength_setting = (
            float(measurement.label.split(":")[-1].split(" ")[0])
        ) or None
    else:
        filter_data = read_data.filter_sets[measurement.label]
        detector_wavelength_setting = filter_data.detector_wavelength_setting

    return Measurement(
        type_=measurement_type,
        device_type=DEVICE_TYPE,
        identifier=measurement.identifier,
        sample_identifier=sample_identifier
        or f"{header_data.well_plate_identifier} {well_position}",
        location_identifier=well_position,
        well_plate_identifier=header_data.well_plate_identifier,
        detection_type=read_data.read_mode.value,
        detector_wavelength_setting=detector_wavelength_setting,
        detector_bandwidth_setting=(
            filter_data.detector_bandwidth_setting if filter_data else None
        ),
        excitation_wavelength_setting=(
            filter_data.excitation_wavelength_setting if filter_data else None
        ),
        excitation_bandwidth_setting=(
            filter_data.excitation_bandwidth_setting if filter_data else None
        ),
        wavelength_filter_cutoff_setting=(
            filter_data.wavelength_filter_cutoff_setting if filter_data else None
        ),
        detector_distance_setting=read_data.detector_distance,
        scan_position_setting=(
            filter_data.scan_position_setting if filter_data else None
        ),
        detector_gain_setting=filter_data.gain if filter_data else None,
        number_of_averages=read_data.number_of_averages,
        detector_carriage_speed=read_data.detector_carriage_speed,
        absorbance=(
            measurement.value
            if measurement_type == MeasurementType.ULTRAVIOLET_ABSORBANCE
            and not kinetic_data
            else None
        ),
        fluorescence=(
            measurement.value
            if measurement_type == MeasurementType.FLUORESCENCE and not kinetic_data
            else None
        ),
        luminescence=(
            measurement.value
            if measurement_type == MeasurementType.LUMINESCENCE and not kinetic_data
            else None
        ),
        compartment_temperature=actual_temperature,
        total_measurement_time_setting=(
            _convert_time_to_seconds(kinetic_data.run_time) if kinetic_data else None
        ),
        read_interval_setting=(
            _convert_time_to_seconds(kinetic_data.interval) if kinetic_data else None
        ),
        number_of_scans_setting=kinetic_data.reads if kinetic_data else None,
        profile_data_cube=(
            DataCube(
                label=str(detector_wavelength_setting),
                structure_dimensions=[
                    DataCubeComponent(
                        concept=ELAPSED_TIME,
                        type_=FieldComponentDatatype.double,
                        unit=SECONDS,
                    )
                ],
                structure_measures=[
                    DataCubeComponent(
                        concept=read_data.read_mode.lower(),
                        type_=FieldComponentDatatype.double,
                        unit=READ_MODE_UNITS.get(read_data.read_mode, UNITLESS),
                    )
                ],
                dimensions=[kinetic_elapsed_time],
                measures=[kinetic_measurements],
            )
            if kinetic_elapsed_time and kinetic_measurements
            else None
        ),
        error_document=error_documents,
        device_control_custom_info={
            "Reading Type": header_data.additional_data.pop("Reading Type", None),
            "Direction of emitted light": (
                filter_data.light_direction if filter_data else None
            ),
        },
        sample_custom_info={
            "Plate Number": header_data.additional_data.pop("Plate Number", None),
            "Conc/Dil": concentration_value,
        },
        measurement_custom_info=header_data.additional_data,
        analytical_method_identifier=header_data.protocol_file_path
        if header_data.protocol_file_path
        else None,
        experimental_data_identifier=header_data.experiment_file_path
        if header_data.experiment_file_path
        else None,
    )


def _convert_time_to_seconds(time_str: str | None) -> float:
    if not time_str:
        return 0.0
    try:
        hours, minutes, seconds = map(float, time_str.split(":"))
        return hours * 3600 + minutes * 60 + seconds

    except ValueError:
        msg = f"Invalid time string: '{time_str}'."
        raise AllotropeConversionError(msg) from None
