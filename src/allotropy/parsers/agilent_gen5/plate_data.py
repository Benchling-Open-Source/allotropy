# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Union

from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.agilent_gen5.absorbance_data_point import AbsorbanceDataPoint
from allotropy.parsers.agilent_gen5.constants import (
    EMISSION_KEY,
    EXCITATION_KEY,
    GAIN_KEY,
    MEASUREMENTS_DATA_POINT_KEY,
    MIRROR_KEY,
    OPTICS_KEY,
    READ_HEIGHT_KEY,
    READ_SPEED_KEY,
    ReadMode,
    ReadType,
    UNSUPORTED_READ_TYPE_ERROR,
)
from allotropy.parsers.agilent_gen5.data_point import DataPoint
from allotropy.parsers.agilent_gen5.fluorescence_data_point import FluorescenceDataPoint
from allotropy.parsers.agilent_gen5.luminescence_data_point import LuminescenceDataPoint
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import assert_not_none, try_float, try_float_or_none

METADATA_PREFIXES = frozenset(
    {
        "Plate Number",
        "Date",
        "Time",
        "Reader Type:",
        "Reader Serial Number:",
        "Reading Type",
    }
)
GEN5_DATETIME_FORMAT = "%m/%d/%Y %I:%M:%S %p"


def try_float_or_value(value: str) -> Union[str, float]:
    try:
        return float(value)
    except ValueError:
        return value


def read_data_section(reader: LinesReader) -> str:
    data_section = "\n".join(
        [
            reader.pop() or "",
            *reader.pop_until_empty(),
        ]
    )
    reader.drop_empty()
    return data_section


def hhmmss_to_sec(hhmmss: str) -> int:
    # convert to seconds, as specified by Allotrope
    hours, minutes, seconds = tuple(int(num) for num in hhmmss.split(":"))
    return (3600 * hours) + (60 * minutes) + seconds


@dataclass(frozen=True)
class FilePaths:
    experiment_file_path: str
    protocol_file_path: str

    @staticmethod
    def create(reader: LinesReader) -> FilePaths:
        assert_not_none(
            reader.drop_until("^Experiment File Path"),
            "Experiment File Path",
        )
        file_paths = reader.pop_until_empty()
        return FilePaths(
            experiment_file_path=f"{next(file_paths)}\t".split("\t")[1],
            protocol_file_path=f"{next(file_paths)}\t".split("\t")[1],
        )


@dataclass(frozen=True)
class HeaderData:
    datetime: str
    well_plate_identifier: str
    model_number: str
    equipment_serial_number: str

    @classmethod
    def create(cls, reader: LinesReader) -> HeaderData:
        assert_not_none(reader.drop_until("^Plate Number"), "Plate Number")
        metadata_dict = cls._parse_metadata(reader)
        datetime_ = cls._parse_datetime(metadata_dict["Date"], metadata_dict["Time"])

        return HeaderData(
            datetime=datetime_,
            well_plate_identifier=metadata_dict["Plate Number"],
            model_number=metadata_dict["Reader Type:"],
            equipment_serial_number=metadata_dict["Reader Serial Number:"],
        )

    @classmethod
    def _parse_metadata(cls, reader: LinesReader) -> dict:
        metadata_dict: dict = {}
        for metadata_line in reader.pop_until_empty():
            line_split = metadata_line.split("\t")
            if line_split[0] not in METADATA_PREFIXES:
                msg = msg_for_error_on_unrecognized_value(
                    "metadata key", line_split[0], METADATA_PREFIXES
                )
                raise AllotropeConversionError(msg)
            metadata_dict[line_split[0]] = line_split[1]
        return metadata_dict

    @classmethod
    def _parse_datetime(cls, date_: str, time_: str) -> str:
        return f"{date_} {time_}"


@dataclass(frozen=True)
class ReadData:
    read_mode: ReadMode
    read_type: ReadType
    read_names: list[str]
    wavelengths: list[float]
    step_label: Optional[str]
    number_of_averages: Optional[float]
    emissions: Optional[list[str]]
    optics: Optional[list[str]]
    gains: Optional[list[float]]
    detector_distance: Optional[float]
    detector_carriage_speed: Optional[str]
    excitations: Optional[list[str]]
    wavelength_filter_cut_offs: Optional[list[float]]
    scan_positions: Optional[list[str]]

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
        read_names = []
        procedure_chunks = cls._get_procedure_chunks(procedure_details)

        for procedure_chunk in procedure_chunks:
            read_names.extend(cls._parse_procedure_chunk(procedure_chunk, read_mode))

        device_control_data = cls._get_device_control_data(procedure_details, read_mode)

        wavelengths = [
            try_float(wavelength, "Wavelength")
            for wavelength in device_control_data.get("Wavelengths", [])
        ]
        gains = [
            try_float(gain, "Gain") for gain in device_control_data.get(GAIN_KEY, [])
        ]
        number_of_averages = device_control_data.get(MEASUREMENTS_DATA_POINT_KEY)
        read_height = device_control_data.get(READ_HEIGHT_KEY, "")

        mirrors = device_control_data.get(MIRROR_KEY, [])
        optics = device_control_data.get(OPTICS_KEY, [])
        scan_positions = []
        wavelength_filter_cut_offs = []
        if mirrors and read_mode == ReadMode.FLUORESCENCE:
            for mirror in mirrors:
                position, cutoff, *_ = mirror.split(" ")
                scan_positions.append(position)
                wavelength_filter_cut_offs.append(try_float(cutoff, "Cutoff"))
        elif optics and read_mode == ReadMode.FLUORESCENCE:
            scan_positions = optics

        return ReadData(
            read_mode=read_mode,
            # TODO: Remove read_type
            read_type=read_type,
            read_names=read_names,
            step_label=device_control_data.get("Step Label"),
            # Absorbance attributes
            wavelengths=wavelengths,
            detector_carriage_speed=device_control_data.get(READ_SPEED_KEY),
            number_of_averages=try_float_or_none(number_of_averages),
            # Luminescence attributes
            emissions=device_control_data.get(EMISSION_KEY),
            optics=device_control_data.get(OPTICS_KEY),
            gains=gains,
            detector_distance=(try_float_or_none(read_height.split(" ")[0])),
            # Fluorescence attributes
            excitations=device_control_data.get(EXCITATION_KEY),
            wavelength_filter_cut_offs=wavelength_filter_cut_offs,
            scan_positions=scan_positions,
        )

    @property
    def data_point_cls(self) -> type[DataPoint]:
        if self.read_mode == ReadMode.ABSORBANCE:
            return AbsorbanceDataPoint
        elif self.read_mode == ReadMode.FLUORESCENCE:
            return FluorescenceDataPoint
        elif self.read_mode == ReadMode.LUMINESCENCE:
            return LuminescenceDataPoint

        msg = msg_for_error_on_unrecognized_value(
            "read mode", self.read_mode, ReadMode._member_names_
        )
        raise AllotropeConversionError(msg)

    @staticmethod
    def get_read_mode(procedure_details: str) -> ReadMode:
        if ReadMode.ABSORBANCE.value in procedure_details:
            return ReadMode.ABSORBANCE
        elif ReadMode.FLUORESCENCE.value in procedure_details:
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
        return ReadType.ENDPOINT

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
                "Wavelengths",
            }
        )
        read_data_dict: dict = {label: [] for label in list_keys}
        read_lines: list[str] = procedure_details.splitlines()
        datum_len = 2

        for line in read_lines:
            strp_line = str(line.strip())
            if strp_line.startswith("Read\t"):
                read_data_dict["Step Label"] = cls._get_step_label(line, read_mode)
                continue

            elif strp_line.startswith("Wavelengths"):
                wavelengths = strp_line.split(":  ")
                read_data_dict["Wavelengths"].extend(wavelengths[1].split(", "))
                continue

            elif strp_line.startswith("Pathlength Correction"):
                corrections = strp_line.split(": ")
                read_data_dict["Wavelengths"].extend(corrections[1].split("/"))
                continue

            line_data: list[str] = strp_line.split(",  ")
            for read_datum in line_data:
                splitted_datum = read_datum.split(": ")
                if len(splitted_datum) != datum_len:
                    continue
                if splitted_datum[0] in list_keys:
                    read_data_dict[splitted_datum[0]].append(splitted_datum[1])
                else:
                    read_data_dict[splitted_datum[0]] = splitted_datum[1]

        return read_data_dict

    @staticmethod
    def _get_procedure_chunks(procedure_details: str) -> list[list[str]]:
        procedure_chunks = []
        current_chunk: list[str] = []
        procedure_lines = procedure_details.splitlines()
        for procedure_line in procedure_lines:
            if procedure_line[0] != "\t":
                procedure_chunks.append(current_chunk)
                current_chunk = []
            current_chunk.append(procedure_line)
        del procedure_chunks[0]
        procedure_chunks.append(current_chunk)

        return procedure_chunks

    @classmethod
    def _get_step_label(cls, read_line: str, read_mode: str) -> Optional[str]:
        read_data_len = 2
        split_line = read_line.split("\t")
        if len(split_line) != read_data_len:
            msg = (
                f"Expected the Read data line {split_line} to contain exactly 2 values."
            )
            raise AllotropeConversionError(msg)
        if split_line[1] != f"{read_mode.title()} Endpoint":
            return split_line[1]

        return None

    @staticmethod
    def _parse_procedure_chunk(
        procedure_chunk: list[str],
        read_mode: ReadMode,
    ) -> list[str]:
        # TODO: remove when using wavelenghts and bandwiths along with stepLabels

        # if no user-defined name is specified for protocols,
        # e.g. it just says "Absorbance Endpoint",
        # Gen5 defaults to using the wavelength as the name
        read_names = []
        use_wavelength_names = False
        read_line_length = 2
        wavelength_line_length = 2

        for line in procedure_chunk:
            split_line = line.strip().split("\t")
            if split_line[0] == "Read":
                if len(split_line) != read_line_length:
                    msg = f"Expected the Read data line {split_line} to contain exactly {read_line_length} values."
                    raise AllotropeConversionError(msg)
                if split_line[-1] == f"{read_mode.title()} Endpoint":
                    use_wavelength_names = True
                else:
                    read_names.append(split_line[-1])
            elif split_line[0].startswith("Wavelengths"):
                if use_wavelength_names:
                    split_line_colon = split_line[0].split(":  ")
                    if len(split_line_colon) != wavelength_line_length:
                        msg = f"Expected the Wavelengths data line {split_line} to contain exactly {wavelength_line_length} values."
                        raise AllotropeConversionError(msg)
                    read_names.extend(split_line_colon[-1].split(", "))
        return read_names


@dataclass(frozen=True)
class LayoutData:
    layout: dict
    concentrations: dict

    @staticmethod
    def create_default() -> LayoutData:
        return LayoutData(
            layout={},
            concentrations={},
        )

    @staticmethod
    def create(layout_str: str) -> LayoutData:
        layout = {}
        concentrations = {}

        layout_lines = layout_str.splitlines()
        # first line is "Layout", second line is column numbers
        current_row = "A"
        for i in range(2, len(layout_lines)):
            split_line = layout_lines[i].split("\t")
            if split_line[0]:
                current_row = split_line[0]
            label = split_line[-1]
            for j in range(1, len(split_line) - 1):
                well_loc = f"{current_row}{j}"
                if label == "Well ID":
                    layout[well_loc] = split_line[j]
                elif label == "Conc/Dil" and split_line[j]:
                    concentrations[well_loc] = float(split_line[j])

        return LayoutData(
            layout=layout,
            concentrations=concentrations,
        )


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
            value=float(actual_temperature.strip().split("\t")[-1]),
        )


@dataclass(frozen=True)
class Results:
    measurements: defaultdict[str, list]
    processed_datas: defaultdict[str, list]
    wells: list
    measurement_docs: list

    @staticmethod
    def create() -> Results:
        return Results(
            measurements=defaultdict(list),
            processed_datas=defaultdict(list),
            wells=[],
            measurement_docs=[],
        )

    def parse_results(
        self,
        results: str,
        read_data: ReadData,
        header_data: HeaderData,
        layout_data: LayoutData,
        actual_temperature: ActualTemperature,
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
                well_value: Union[str, float] = try_float_or_value(values[col_num])
                if Results._is_processed_data_label(
                    label,
                    read_data.read_mode,
                    read_data.read_names,
                ):
                    self.processed_datas[well_pos].append([label, well_value])
                else:
                    label_only = label.split(":")[-1]
                    self.measurements[well_pos].append([label_only, well_value])

        for well_pos in self.wells:
            self.measurement_docs.append(
                read_data.data_point_cls(
                    read_type=read_data.read_type,
                    measurements=self.measurements[well_pos],
                    well_location=well_pos,
                    well_plate_identifier=header_data.well_plate_identifier,
                    sample_identifier=layout_data.layout.get(well_pos),
                    concentration=layout_data.concentrations.get(well_pos),
                    processed_data=self.processed_datas[well_pos],
                    temperature=actual_temperature.value,
                ).to_measurement_doc()
            )

    @staticmethod
    def _is_processed_data_label(
        label: str,
        read_mode: ReadMode,
        read_names: list,
    ) -> bool:
        if read_mode == ReadMode.LUMINESCENCE:
            return not any(
                (label.startswith(read_name) and label.split(":")[-1] == "Lum")
                for read_name in read_names
            )
        else:
            return not any(
                (label.startswith(read_name) and label.split(":")[-1][0].isdigit())
                for read_name in read_names
            )


@dataclass(frozen=True)
class PlateData:
    file_paths: FilePaths
    header_data: HeaderData
    read_data: ReadData
    results: Results

    @staticmethod
    def create(reader: LinesReader) -> PlateData:
        file_paths = FilePaths.create(reader)
        header_data = HeaderData.create(reader)
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
                    header_data,
                    layout_data,
                    actual_temperature,
                )

        return PlateData(
            file_paths=file_paths,
            header_data=header_data,
            read_data=read_data,
            results=results,
        )
