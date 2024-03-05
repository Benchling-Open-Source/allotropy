# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
from typing import Optional, Union

import numpy as np
import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.agilent_gen5.absorbance_data_point import AbsorbanceDataPoint
from allotropy.parsers.agilent_gen5.constants import (
    ReadMode,
    ReadType,
    READTYPE_TO_DIMENSIONS,
)
from allotropy.parsers.agilent_gen5.data_point import DataPoint
from allotropy.parsers.agilent_gen5.fluorescence_data_point import FluorescenceDataPoint
from allotropy.parsers.agilent_gen5.luminescence_data_point import LuminescenceDataPoint
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import assert_not_none

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


def try_float(value: str) -> Union[str, float]:
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

    @classmethod
    def create(cls, reader: LinesReader) -> ReadData:
        assert_not_none(reader.drop_until("^Procedure Details"), "Procedure Details")
        reader.pop()
        reader.drop_empty()
        procedure_details = read_data_section(reader)

        read_mode = cls.get_read_mode(procedure_details)
        read_type = cls.get_read_type(procedure_details)
        read_names: list = []
        procedure_chunks = cls._parse_procedure_chunks(procedure_details)
        for procedure_chunk in procedure_chunks:
            read_names.extend(cls._parse_procedure_chunk(procedure_chunk, read_mode))

        return ReadData(
            read_mode=read_mode,
            read_type=read_type,
            read_names=read_names,
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
        # TODO parse the rest of the procedure details

        # TODO: only Endpoint measurements are supported
        # this should raise for any other read type.
        if ReadType.KINETIC.value in procedure_details:
            return ReadType.KINETIC
        elif ReadType.AREASCAN.value in procedure_details:
            return ReadType.AREASCAN
        elif ReadType.SPECTRAL.value in procedure_details:
            return ReadType.SPECTRAL

        # check for this last, because other modes still contain the word "Endpoint"
        return ReadType.ENDPOINT

    @staticmethod
    def _parse_procedure_chunks(procedure_details: str) -> list[list[str]]:
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

    @staticmethod
    def _parse_procedure_chunk(
        procedure_chunk: list[str],
        read_mode: ReadMode,
    ) -> list[str]:
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
                well_value: Union[str, float] = try_float(values[col_num])
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
                    plate_barcode=header_data.well_plate_identifier,
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
class CurveName:
    statistics_doc: list

    @staticmethod
    def create_default() -> CurveName:
        return CurveName(statistics_doc=[])

    @staticmethod
    def create(
        stdcurve: str,
        header_data: HeaderData,
        results: Results,
    ) -> CurveName:
        lines = stdcurve.splitlines()
        num_lines = 2
        if len(lines) != num_lines:
            msg = f"Expected the std curve data '{lines}' to contain exactly {num_lines} lines."
            raise AllotropeConversionError(msg)
        keys = lines[0].split("\t")
        values = lines[1].split("\t")
        return CurveName(
            statistics_doc=[
                {
                    "statistical feature": key,
                    "feature": try_float(value),
                    "group": f"{header_data.well_plate_identifier} {results.wells[0]}-{results.wells[-1]}",
                }
                for key, value in zip(keys, values)
            ]
        )


# TODO: this class will probably be removed since kinetic is not supported at this point by allotropy
@dataclass(frozen=True)
class KineticData:
    temperatures: list
    kinetic_times: list[int]

    @staticmethod
    def create_default() -> KineticData:
        return KineticData(
            temperatures=[],
            kinetic_times=[],
        )

    @staticmethod
    def create(
        reader: LinesReader,
        results: Results,
    ) -> KineticData:
        kinetic_data = read_data_section(reader)

        kinetic_data_io = StringIO(kinetic_data)
        df = pd.read_table(kinetic_data_io)
        df_columns = kinetic_data.split("\n")[0].split("\t")
        df = df[
            df["A1"].notna()
        ]  # drop incomplete rows, particularly rows only with "0:00:00"

        kinetic_times = [hhmmss_to_sec(hhmmss) for hhmmss in df["Time"]]
        temperatures = df[df_columns[1]].replace(np.nan, None).tolist()
        has_temperatures = any(temp is not None for temp in temperatures)
        for well_pos in df_columns[
            2:
        ]:  # first column is Time, second column is T∞ READ_NAME with no values
            results.wells.append(well_pos)
            values = df[well_pos].tolist()
            if has_temperatures:
                results.measurements[well_pos].extend(
                    list(zip(kinetic_times, values, temperatures))
                )
            else:
                results.measurements[well_pos].extend(list(zip(kinetic_times, values)))

        return KineticData(
            temperatures=temperatures,
            kinetic_times=kinetic_times,
        )

    def parse_blank_kinetic_data(
        self,
        reader: LinesReader,
        blank_kinetic_data_label: str,
        results: Results,
        read_data: ReadData,
    ) -> None:
        blank_kinetic_data = read_data_section(reader)

        blank_kinetic_data_io = StringIO(blank_kinetic_data)
        df = pd.read_table(blank_kinetic_data_io)
        df.dropna(axis=0)  # drop incomplete rows
        df_columns = blank_kinetic_data.split("\n")[0].split("\t")

        for well_pos in df_columns[1:]:  # first column is Time
            measures = df[well_pos].tolist()
            results.processed_datas[well_pos].append(
                [
                    blank_kinetic_data_label,
                    self._blank_data_cube(
                        measures,
                        read_data,
                    ),
                ]
            )

    def _blank_data_cube(
        self,
        measures: list[float],
        read_data: ReadData,
    ) -> TDatacube:
        structure_dimensions = READTYPE_TO_DIMENSIONS[read_data.read_type]
        structure_measures = [
            (
                "double",
                read_data.read_mode.lower(),
                read_data.data_point_cls.unit,
            )
        ]
        return TDatacube(
            label=f"{read_data.read_type.value.lower()} data",
            cube_structure=TDatacubeStructure(
                [
                    TDatacubeComponent(FieldComponentDatatype(data_type), concept, unit)
                    for data_type, concept, unit in structure_dimensions
                ],
                [
                    TDatacubeComponent(FieldComponentDatatype(data_type), concept, unit)
                    for data_type, concept, unit in structure_measures
                ],
            ),
            data=TDatacubeData([self.kinetic_times], [measures]),  # type: ignore[list-item]
        )


@dataclass(frozen=True)
class PlateData:
    file_paths: FilePaths
    header_data: HeaderData
    read_data: ReadData
    results: Results
    curve_name: CurveName
    kinetic_data: KineticData

    @staticmethod
    def create(reader: LinesReader) -> PlateData:
        file_paths = FilePaths.create(reader)
        header_data = HeaderData.create(reader)
        read_data = ReadData.create(reader)
        layout_data = LayoutData.create_default()
        actual_temperature = ActualTemperature.create_default()
        results = Results.create()
        curve_name = CurveName.create_default()
        kinetic_data = KineticData.create_default()

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
            elif data_section.startswith("Curve Name"):
                curve_name = CurveName.create(
                    data_section,
                    header_data,
                    results,
                )
            elif len(data_section.split("\n")) == 1 and any(
                read_name in data_section for read_name in read_data.read_names
            ):
                if data_section.startswith("Blank"):
                    kinetic_data.parse_blank_kinetic_data(
                        reader,
                        data_section.strip(),
                        results,
                        read_data,
                    )
                else:
                    kinetic_data = KineticData.create(reader, results)

        return PlateData(
            file_paths=file_paths,
            header_data=header_data,
            read_data=read_data,
            results=results,
            curve_name=curve_name,
            kinetic_data=kinetic_data,
        )
