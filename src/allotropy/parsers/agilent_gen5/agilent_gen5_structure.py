from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
import re

import pandas as pd

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    CalculatedDataItem,
    DataSource,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    AllotropyParserError,
)
from allotropy.parsers.agilent_gen5.constants import (
    ALPHALISA_FLUORESCENCE_FOUND,
    DEFAULT_SOFTWARE_NAME,
    DEVICE_TYPE,
    EMISSION_KEY,
    EXCITATION_KEY,
    FILENAME_REGEX,
    GAIN_KEY,
    MEASUREMENTS_DATA_POINT_KEY,
    MIRROR_KEY,
    NAN_EMISSION_EXCITATION,
    OPTICS_KEY,
    PATHLENGTH_CORRECTION_KEY,
    READ_DATA_MEASUREMENT_ERROR,
    READ_HEIGHT_KEY,
    READ_SPEED_KEY,
    ReadMode,
    ReadType,
    UNSUPPORTED_READ_MODE_ERROR,
    UNSUPPORTED_READ_TYPE_ERROR,
    WAVELENGTHS_KEY,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import SectionLinesReader
from allotropy.parsers.utils.pandas import read_csv, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float,
    try_float_or_nan,
    try_float_or_none,
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
    file_name: str

    @classmethod
    def create(cls, data: SeriesData, file_name: str) -> HeaderData:
        matches = re.match(FILENAME_REGEX, file_name)
        plate_identifier = matches.groupdict()["plate_identifier"] if matches else None
        return HeaderData(
            software_version=data[str, "Software Version"],
            experiment_file_path=data.get(str, "Experiment File Path:"),
            file_name=file_name,
            protocol_file_path=data.get(str, "Protocol File Path:"),
            datetime=f'{data[str, "Date"]} {data[str, "Time"]}',
            well_plate_identifier=plate_identifier or data.get(str, "Plate Number"),
            model_number=data.get(str, "Reader Type:"),
            equipment_serial_number=data.get(str, "Reader Serial Number:"),
        )


@dataclass(frozen=True)
class FilterSet:
    gain: str
    emission: str | None = None
    excitation: str | None = None
    mirror: str | None = None
    optics: str | None = None

    @property
    def detector_wavelength_setting(self) -> JsonFloat | None:
        if not self.emission:
            return None
        return try_float_or_nan(self.emission.split("/")[0])

    @property
    def detector_bandwidth_setting(self) -> JsonFloat | None:
        if not self.emission:
            return None
        try:
            return try_float_or_nan(self.emission.split("/")[1])
        except IndexError:
            return None

    @property
    def excitation_wavelength_setting(self) -> JsonFloat | None:
        if self.excitation:
            return try_float_or_nan(self.excitation.split("/")[0])
        return None

    @property
    def excitation_bandwidth_setting(self) -> JsonFloat | None:
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

    LIST_KEYS = frozenset(
        {
            EMISSION_KEY,
            EXCITATION_KEY,
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
            if strp_line.startswith("Read\t"):
                device_control_data.step_label = cls._get_step_label(line, read_mode)
                continue

            elif strp_line.startswith(WAVELENGTHS_KEY):
                wavelengths = strp_line.split(":  ")
                device_control_data.add(WAVELENGTHS_KEY, wavelengths[1].split(", "))
                continue

            line_data: list[str] = strp_line.split(",  ")
            for read_datum in line_data:
                splitted_datum = read_datum.split(": ")
                if len(splitted_datum) != 2:  # noqa: PLR2004
                    continue
                device_control_data.add(splitted_datum[0], splitted_datum[1])

        return device_control_data

    @classmethod
    def _get_step_label(cls, read_line: str, read_mode: str) -> str | None:
        split_line = read_line.strip().split("\t")
        if len(split_line) != 2:  # noqa: PLR2004
            msg = (
                f"Expected the Read data line {split_line} to contain exactly 2 values."
            )
            raise AllotropeConversionError(msg)
        if split_line[1] != f"{read_mode.title()} Endpoint":
            return split_line[1]

        return None


@dataclass(frozen=True)
class ReadData:
    read_mode: ReadMode
    measurement_labels: set[str]
    pathlength_correction: str | None
    step_label: str | None
    number_of_averages: float | None
    detector_distance: float | None
    detector_carriage_speed: str | None
    filter_sets: dict[str, FilterSet]

    @classmethod
    def create(cls, lines: list[str]) -> list[ReadData]:
        procedure_details = "\n".join(lines)
        read_type = cls.get_read_type(procedure_details)
        if read_type != ReadType.ENDPOINT:
            raise AllotropeConversionError(UNSUPPORTED_READ_TYPE_ERROR)

        read_modes = cls.get_read_modes(procedure_details)
        read_sections = list(SectionLinesReader(lines).iter_sections("^Read\t"))
        if len(read_modes) != len(read_sections):
            msg = "Expected the number of read modes to match the number of read sections."
            raise AllotropeConversionError(msg)

        read_data_list: list[ReadData] = []
        for read_mode, read_section in zip(read_modes, read_sections, strict=True):
            device_control_data = DeviceControlData.create(
                read_section.lines, read_mode
            )
            measurement_labels, label_aliases = cls._get_measurement_labels(
                device_control_data, read_mode
            )
            all_labels = {
                alias for aliases in label_aliases.values() for alias in aliases
            }
            number_of_averages = device_control_data.get(MEASUREMENTS_DATA_POINT_KEY)
            read_height = device_control_data.get(READ_HEIGHT_KEY) or ""
            read_data_list.append(
                ReadData(
                    read_mode=read_mode,
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
                )
            )
        return read_data_list

    @staticmethod
    def get_read_modes(procedure_details: str) -> list[ReadMode]:
        read_modes = []
        for read_mode in ReadMode:
            # Construct the regex pattern for the current read mode
            pattern = fr"\t{re.escape(read_mode.value)} Endpoint"
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
        if ReadType.KINETIC.value in procedure_details:
            return ReadType.KINETIC
        elif ReadType.AREASCAN.value in procedure_details:
            return ReadType.AREASCAN
        elif ReadType.SPECTRAL.value in procedure_details:
            return ReadType.SPECTRAL
        # check for this last, because other modes still contain the word "Endpoint"
        elif ReadType.ENDPOINT.value in procedure_details:
            return ReadType.ENDPOINT

        msg = f"Read type not found; expected to find one of {sorted(ReadType._member_names_)}."
        raise AllotropeConversionError(msg)

    @classmethod
    def _get_measurement_labels(
        cls, device_control_data: DeviceControlData, read_mode: str
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

        if read_mode == ReadMode.FLUORESCENCE:
            excitations: list[str] = device_control_data.get_list(EXCITATION_KEY)
            emissions: list[str] = device_control_data.get_list(EMISSION_KEY)
            measurement_labels = [
                f"{label_prefix}{excitation},{emission}"
                for excitation, emission in zip(excitations, emissions, strict=True)
            ]
            label_aliases = {
                f"{label_prefix}{excitation},{emission}": {
                    f"{label_prefix}{excitation.split('/')[0]},{emission.split('/')[0]}"
                }
                for excitation, emission in zip(excitations, emissions, strict=True)
            }
            if not measurement_labels:
                measurement_labels = ["Alpha"]

        if read_mode == ReadMode.LUMINESCENCE:
            emissions = device_control_data.get_list(EMISSION_KEY)
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
        mirrors = device_control_data.get_list(MIRROR_KEY)
        optics = device_control_data.get_list(OPTICS_KEY)
        gains = device_control_data.get_list(GAIN_KEY)

        if len(measurement_labels) != len(gains):
            msg = f"Expected the number measurement labels: {measurement_labels} to match the number of gains: {gains}."
            raise AllotropeConversionError(msg)

        for idx, label in enumerate(measurement_labels):
            mirror = None
            if mirrors and read_mode == ReadMode.FLUORESCENCE:
                mirror = mirrors[idx]
            filter_data[label] = FilterSet(
                emission=emissions[idx] if emissions else None,
                gain=gains[idx],
                excitation=excitations[idx] if excitations else None,
                mirror=mirror,
                optics=optics[idx] if optics else None,
            )
        for measurement_label, aliases in label_aliases.items():
            for alias in aliases:
                filter_data[alias] = filter_data[measurement_label]

        return filter_data


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


@dataclass(frozen=True)
class MeasurementData:
    identifier: str
    value: JsonFloat
    label: str


def create_results(
    result_lines: list[str],
    header_data: HeaderData,
    read_data: list[ReadData],
    sample_identifiers: dict[str, str],
    actual_temperature: float | None,
) -> tuple[list[MeasurementGroup], list[CalculatedDataItem]]:
    if result_lines[0].strip() != "Results":
        msg = f"Expected the first line of the results section '{result_lines[0]}' to be 'Results'."
        raise AllotropeConversionError(msg)

    # Create dataframe from tabular data and forward fill empty values in index
    data = read_csv(StringIO("\n".join(result_lines[1:])), sep="\t")
    data = data.set_index(data.index.to_series().ffill(axis="index").values)

    well_to_measurements: defaultdict[str, list[MeasurementData]] = defaultdict(
        list[MeasurementData]
    )
    calculated_data: defaultdict[str, list[tuple[str, JsonFloat]]] = defaultdict(
        list[tuple[str, JsonFloat]]
    )
    measurement_labels = [
        label for r_data in read_data for label in r_data.measurement_labels
    ]
    for row_name, row in data.iterrows():
        label = row.iloc[-1]
        for col_index, value in enumerate(row.iloc[:-1]):
            well_pos = f"{row_name}{col_index + 1}"
            well_value = try_float_or_nan(value)

            if label in measurement_labels:
                well_to_measurements[well_pos].append(
                    MeasurementData(random_uuid_str(), well_value, label)
                )
            else:
                calculated_data[well_pos].append((label, well_value))

    groups = [
        MeasurementGroup(
            measurement_time=header_data.datetime,
            plate_well_count=len(well_to_measurements),
            analytical_method_identifier=header_data.protocol_file_path,
            experimental_data_identifier=header_data.experiment_file_path,
            measurements=[
                _create_measurement(
                    measurement,
                    well_position,
                    header_data,
                    get_read_data_from_measurement(measurement, read_data),
                    sample_identifiers.get(well_position),
                    actual_temperature,
                )
                for measurement in measurements
            ],
        )
        for well_position, measurements in well_to_measurements.items()
    ]

    calculated_data_items = [
        CalculatedDataItem(
            identifier=random_uuid_str(),
            data_sources=[
                DataSource(
                    identifier=measurement.identifier,
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


def get_read_data_from_measurement(
    measurement: MeasurementData, read_data_list: list[ReadData]
) -> ReadData:
    for read_data in read_data_list:
        if measurement.label in read_data.measurement_labels:
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
    return Metadata(
        device_identifier=NOT_APPLICABLE,
        model_number=header_data.model_number or NOT_APPLICABLE,
        equipment_serial_number=header_data.equipment_serial_number,
        software_name=DEFAULT_SOFTWARE_NAME,
        software_version=header_data.software_version,
        file_name=header_data.file_name,
    )


def _create_measurement(
    measurement: MeasurementData,
    well_position: str,
    header_data: HeaderData,
    read_data: ReadData,
    sample_identifier: str | None,
    actual_temperature: float | None,
) -> Measurement:
    # TODO(switch-statement): use switch statement once Benchling can use 3.10 syntax
    if read_data.read_mode == ReadMode.ABSORBANCE:
        measurement_type = MeasurementType.ULTRAVIOLET_ABSORBANCE
    elif read_data.read_mode == ReadMode.FLUORESCENCE:
        measurement_type = MeasurementType.FLUORESCENCE
    elif read_data.read_mode == ReadMode.LUMINESCENCE:
        measurement_type = MeasurementType.LUMINESCENCE

    detector_wavelength_setting: JsonFloat | None = None
    if measurement_type is MeasurementType.ULTRAVIOLET_ABSORBANCE:
        filter_data = None
        detector_wavelength_setting = float(
            measurement.label.split(":")[-1].split(" ")[0]
        )
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
        detector_bandwidth_setting=filter_data.detector_bandwidth_setting
        if filter_data
        else None,
        excitation_wavelength_setting=filter_data.excitation_wavelength_setting
        if filter_data
        else None,
        excitation_bandwidth_setting=filter_data.excitation_bandwidth_setting
        if filter_data
        else None,
        wavelength_filter_cutoff_setting=filter_data.wavelength_filter_cutoff_setting
        if filter_data
        else None,
        detector_distance_setting=read_data.detector_distance,
        scan_position_setting=filter_data.scan_position_setting
        if filter_data
        else None,
        detector_gain_setting=filter_data.gain if filter_data else None,
        number_of_averages=read_data.number_of_averages,
        detector_carriage_speed=read_data.detector_carriage_speed,
        absorbance=measurement.value
        if measurement_type == MeasurementType.ULTRAVIOLET_ABSORBANCE
        else None,
        fluorescence=measurement.value
        if measurement_type == MeasurementType.FLUORESCENCE
        else None,
        luminescence=measurement.value
        if measurement_type == MeasurementType.LUMINESCENCE
        else None,
        compartment_temperature=actual_temperature,
    )
