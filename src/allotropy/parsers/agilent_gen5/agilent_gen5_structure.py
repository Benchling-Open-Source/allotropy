# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.agilent_gen5.constants import (
    EMISSION_KEY,
    EXCITATION_KEY,
    FILENAME_REGEX,
    GAIN_KEY,
    HEADER_PREFIXES,
    MEASUREMENTS_DATA_POINT_KEY,
    MIRROR_KEY,
    OPTICS_KEY,
    PATHLENGTH_CORRECTION_KEY,
    READ_HEIGHT_KEY,
    READ_SPEED_KEY,
    ReadMode,
    ReadType,
    UNSUPORTED_READ_TYPE_ERROR,
    WAVELENGTHS_KEY,
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
    def _get_identifier_from_filename_or_none(cls, file_name: str) -> str | None:
        matches = re.match(FILENAME_REGEX, file_name)
        if not matches:
            return None

        matches_dict = matches.groupdict()
        return matches_dict["plate_identifier"]


@dataclass(frozen=True)
class FilterSet:
    gain: str
    emission: str | None = None
    excitation: str | None = None
    mirror: str | None = None
    optics: str | None = None

    @property
    def detector_wavelength_setting(self) -> float | None:
        if self.emission == "Full light" or not self.emission:
            return None
        return try_float(self.emission.split("/")[0], "Detector wavelength")

    @property
    def detector_bandwidth_setting(self) -> float | None:
        if not self.emission or self.emission == "Full light":
            return None
        try:
            return try_float(self.emission.split("/")[1], "Detector bandwith")
        except IndexError:
            return None

    @property
    def excitation_wavelength_setting(self) -> float | None:
        if self.excitation:
            return try_float(self.excitation.split("/")[0], "Excitation wavelength")
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


@dataclass(frozen=True)
class ReadData:
    read_mode: ReadMode
    measurement_labels: list[str]
    pathlength_correction: str | None
    step_label: str | None
    number_of_averages: float | None
    detector_distance: float | None
    detector_carriage_speed: str | None
    filter_sets: dict[str, FilterSet]

    @classmethod
    def create(cls, reader: LinesReader) -> ReadData:
        assert_not_none(reader.drop_until("^Procedure Details"), "Procedure Details")
        reader.pop()
        reader.drop_empty()
        procedure_details = read_data_section(reader)

        read_type = cls.get_read_type(procedure_details)
        if read_type != ReadType.ENDPOINT:
            raise AllotropeConversionError(UNSUPORTED_READ_TYPE_ERROR)

        read_mode = cls.get_read_mode(procedure_details)
        device_control_data = cls._get_device_control_data(procedure_details, read_mode)
        measurement_labels = cls._get_measurement_labels(device_control_data, read_mode)

        number_of_averages = device_control_data.get(MEASUREMENTS_DATA_POINT_KEY)
        read_height = device_control_data.get(READ_HEIGHT_KEY, "")

        return ReadData(
            read_mode=read_mode,
            step_label=device_control_data.get("Step Label"),
            measurement_labels=measurement_labels,
            detector_carriage_speed=device_control_data.get(READ_SPEED_KEY),
            # Absorbance attributes
            pathlength_correction=device_control_data.get(PATHLENGTH_CORRECTION_KEY),
            number_of_averages=try_float_or_none(number_of_averages),
            # Luminescence attributes
            detector_distance=try_float_or_none(read_height.split(" ")[0]),
            # Fluorescence attributes
            filter_sets=cls._get_filter_sets(
                measurement_labels, device_control_data, read_mode
            ),
        )

    @staticmethod
    def get_read_mode(procedure_details: str) -> ReadMode:
        if ReadMode.ABSORBANCE.value in procedure_details:
            return ReadMode.ABSORBANCE
        elif (
            ReadMode.FLUORESCENCE.value in procedure_details
            or ReadMode.ALPHALISA.value in procedure_details
        ):
            return ReadMode.FLUORESCENCE
        elif ReadMode.LUMINESCENCE.value in procedure_details:
            return ReadMode.LUMINESCENCE

        msg = f"Read mode not found; expected to find one of {sorted(ReadMode._member_names_)}."
        raise AllotropeConversionError(msg)

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
    def _get_measurement_labels(cls, device_control_data: dict, read_mode: str) -> list:
        step_label = device_control_data.get("Step Label")
        label_prefix = f"{step_label}:" if step_label else ""
        measurement_labels = []

        if read_mode == ReadMode.ABSORBANCE:
            measurement_labels = cls._get_absorbance_measurement_labels(
                label_prefix, device_control_data
            )

        if read_mode == ReadMode.FLUORESCENCE:
            excitations = device_control_data.get(EXCITATION_KEY, [])
            emissions = device_control_data.get(EMISSION_KEY, [])
            measurement_labels = [
                f"{label_prefix}{excitation},{emission}"
                for excitation, emission in zip(excitations, emissions)
            ]
            if not measurement_labels:
                measurement_labels = ["Alpha"]

        if read_mode == ReadMode.LUMINESCENCE:
            emissions = device_control_data.get(EMISSION_KEY)
            for emission in emissions:
                label = "Lum" if emission == "Full light" else emission
                measurement_labels.append(f"{label_prefix}{label}")

        return measurement_labels

    @classmethod
    def _get_absorbance_measurement_labels(
        cls, label_prefix: str | None, device_control_data: dict
    ) -> list:
        wavelengths = device_control_data.get(WAVELENGTHS_KEY, [])
        pathlength_correction = device_control_data.get(PATHLENGTH_CORRECTION_KEY)
        measurement_labels = []

        for wavelenght in wavelengths:
            label = f"{label_prefix}{wavelenght}"
            measurement_labels.append(label)

        if pathlength_correction:
            test, ref = pathlength_correction.split(" / ")
            test_label = f"{label_prefix}{test} [Test]"
            ref_label = f"{label_prefix}{ref} [Ref]"
            measurement_labels.extend([test_label, ref_label])

        return measurement_labels

    @classmethod
    def _get_device_control_data(
        cls, procedure_details: str, read_mode: ReadMode
    ) -> dict:
        list_keys = frozenset(
            {
                EMISSION_KEY,
                EXCITATION_KEY,
                OPTICS_KEY,
                GAIN_KEY,
                MIRROR_KEY,
                WAVELENGTHS_KEY,
            }
        )
        read_data_dict: dict = {label: [] for label in list_keys}
        read_lines: list[str] = procedure_details.splitlines()

        for line in read_lines:
            strp_line = str(line.strip())
            if strp_line.startswith("Read\t"):
                read_data_dict["Step Label"] = cls._get_step_label(line, read_mode)
                continue

            elif strp_line.startswith(WAVELENGTHS_KEY):
                wavelengths = strp_line.split(":  ")
                read_data_dict[WAVELENGTHS_KEY].extend(wavelengths[1].split(", "))
                continue

            line_data: list[str] = strp_line.split(",  ")
            for read_datum in line_data:
                splitted_datum = read_datum.split(": ")
                if len(splitted_datum) != 2:  # noqa: PLR2004
                    continue
                if splitted_datum[0] in list_keys:
                    read_data_dict[splitted_datum[0]].append(splitted_datum[1])
                else:
                    read_data_dict[splitted_datum[0]] = splitted_datum[1]

        return read_data_dict

    @classmethod
    def _get_step_label(cls, read_line: str, read_mode: str) -> str | None:
        split_line = read_line.split("\t")
        if len(split_line) != 2:  # noqa: PLR2004
            msg = (
                f"Expected the Read data line {split_line} to contain exactly 2 values."
            )
            raise AllotropeConversionError(msg)
        if split_line[1] != f"{read_mode.title()} Endpoint":
            return split_line[1]

        return None

    @classmethod
    def _get_filter_sets(
        cls,
        measurement_labels: list[str],
        device_control_data: dict,
        read_mode: ReadMode,
    ) -> dict[str, FilterSet]:
        filter_data: dict[str, FilterSet] = {}
        if read_mode == ReadMode.ABSORBANCE:
            return filter_data

        emissions = device_control_data.get(EMISSION_KEY, [])
        excitations = device_control_data.get(EXCITATION_KEY, [])
        mirrors = device_control_data.get(MIRROR_KEY, [])
        optics = device_control_data.get(OPTICS_KEY, [])
        gains = device_control_data.get(GAIN_KEY, [])

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
        return filter_data


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
    value: float | None = None

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
class DataSource:
    identifier: str
    feature: ReadMode


@dataclass(frozen=True)
class CalculatedDatum:
    identifier: str
    data_sources: list[DataSource]
    name: str
    result: JsonFloat


@dataclass(frozen=True)
class Results:
    measurements: defaultdict[str, list[Measurement]]
    calculated_data: list[CalculatedDatum]
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
        read_data: ReadData,
    ) -> None:
        result_lines = results.splitlines()
        calculated_data: defaultdict[str, list] = defaultdict(list)
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

                if label in read_data.measurement_labels:
                    self.measurements[well_pos].append(
                        Measurement(random_uuid_str(), well_value, label)
                    )
                else:
                    calculated_data[well_pos].append([label, well_value])

        for well in self.wells:
            measurements = self.measurements[well]
            for label, value in calculated_data[well]:
                sources = self._get_sources_for_calculated_data(measurements, label)
                self.calculated_data.append(
                    CalculatedDatum(
                        identifier=random_uuid_str(),
                        data_sources=[
                            DataSource(
                                identifier=measurement.identifier,
                                feature=read_data.read_mode,
                            )
                            for measurement in sources
                        ],
                        name=label,
                        result=value,
                    )
                )

    def _get_sources_for_calculated_data(
        self, measurements: list[Measurement], calculated_data_label: str
    ) -> list[Measurement]:

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


@dataclass(frozen=True)
class PlateData:
    header_data: HeaderData
    read_data: ReadData
    layout_data: LayoutData
    results: Results
    compartment_temperature: float | None

    @staticmethod
    def create(reader: LinesReader, file_name: str) -> PlateData:
        header_data = HeaderData.create(reader, file_name)
        read_data = ReadData.create(reader)
        layout_data = LayoutData.create_default()
        actual_temperature = ActualTemperature.create_default()
        results = Results.create()

        while reader.current_line_exists():
            data_section = read_data_section(reader)
            if data_section.startswith("Layout"):
                layout_data = LayoutData.create(data_section)
            elif data_section.startswith("Actual Temperature"):
                actual_temperature = ActualTemperature.create(data_section)
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
            compartment_temperature=actual_temperature.value,
        )
