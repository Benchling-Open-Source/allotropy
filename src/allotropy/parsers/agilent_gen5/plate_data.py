from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import StringIO
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)
from allotropy.parsers.agilent_gen5.constants import (
    ReadMode,
    ReadType,
    READTYPE_TO_DIMENSIONS,
)
from allotropy.parsers.agilent_gen5.data_point import DataPoint

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


class PlateData:
    measurements: defaultdict[str, list]
    processed_datas: defaultdict[str, list]
    temperatures: list
    kinetic_times: Optional[list[int]]
    measurement_docs: list
    wells: list
    layout: dict
    concentrations: dict
    read_names: list
    datetime: Optional[str]
    experiment_file_path: Optional[str]
    protocol_file_path: Optional[str]
    read_type: ReadType
    plate_barcode: str
    statistics_doc: list
    actual_temperature: Optional[float]

    def __init__(
        self,
        read_mode: ReadMode,
        data_point_cls: type[DataPoint],
        software_version_chunk: str,
        file_paths_chunk: str,
        all_data_chunk: str,
    ):
        self.measurements = defaultdict(list)
        self.processed_datas = defaultdict(list)
        self.temperatures = []
        self.kinetic_times = None

        self.measurement_docs = []
        self.wells = []
        self.layout = {}
        self.concentrations = {}
        self.read_names = []
        self.datetime = None
        self.experiment_file_path = None
        self.protocol_file_path = None
        self.statistics_doc = []
        self.actual_temperature = None

        self.software_version = software_version_chunk.split("\t")[1]

        file_paths = file_paths_chunk.split("\n")
        self.experiment_file_path = f"{file_paths[0]}\t".split("\t")[1]
        self.protocol_file_path = f"{file_paths[1]}\t".split("\t")[1]

        all_data_sections = all_data_chunk.split("\n\n")

        is_kinetic_data = False
        # kinetic_data_label = None
        is_blank_kinetic_data = False
        blank_kinetic_data_label = None

        for data_section in all_data_sections:
            if data_section.startswith("Plate Number"):
                metadata_dict = PlateData._parse_metadata(data_section)
                self.datetime = datetime.strptime(  # noqa: DTZ007
                    f"{metadata_dict['Date']} {metadata_dict['Time']}",
                    GEN5_DATETIME_FORMAT,
                ).isoformat()
                self.plate_barcode = metadata_dict["Plate Number"]
            elif data_section.startswith("Plate Type"):
                self.read_type = PlateData.get_read_type(data_section)
                procedure_chunks = PlateData._parse_procedure_chunks(data_section)
                for procedure_chunk in procedure_chunks:
                    PlateData._parse_procedure_chunk(
                        procedure_chunk,
                        read_mode,
                        self.read_names,
                    )
            elif data_section.startswith("Layout"):
                PlateData._parse_layout(
                    data_section,
                    self.layout,
                    self.concentrations,
                )
            elif data_section.startswith("Actual Temperature"):
                self.actual_temperature = PlateData._parse_actual_temperature(
                    data_section
                )
            elif data_section.startswith("Results"):
                PlateData._parse_results(
                    data_section,
                    self.wells,
                    read_mode,
                    self.read_names,
                    self.processed_datas,
                    self.measurements,
                    data_point_cls,
                    self.read_type,
                    self.plate_barcode,
                    self.layout,
                    self.concentrations,
                    self.actual_temperature,
                    self.measurement_docs,
                )
            elif data_section.startswith("Curve Name"):
                self.statistics_doc = PlateData._parse_stdcurve(
                    data_section,
                    self.plate_barcode,
                    self.wells,
                )
            elif is_kinetic_data:
                self.kinetic_times, self.temperatures = PlateData._parse_kinetic_data(
                    data_section,
                    self.wells,
                    self.measurements,
                )
                is_kinetic_data = False
            elif is_blank_kinetic_data:
                PlateData._parse_blank_kinetic_data(
                    data_section,
                    blank_kinetic_data_label,
                    self.processed_datas,
                    self.read_type,
                    read_mode,
                    data_point_cls,
                    self.kinetic_times,
                )
                is_blank_kinetic_data = False
            elif len(data_section.split("\n")) == 1 and any(
                read_name in data_section for read_name in self.read_names
            ):
                if data_section.startswith("Blank"):
                    is_blank_kinetic_data = True
                    blank_kinetic_data_label = data_section.strip()
                else:
                    is_kinetic_data = True
                    # kinetic_data_label = data_section.strip()

    @staticmethod
    def create(
        cls: type[PlateData],
        software_version_chunk: str,
        file_paths_chunk: str,
        all_data_chunk: str,
    ) -> PlateData:
        return cls(
            read_mode=cls.get_read_mode(),
            data_point_cls=cls.get_data_point_cls(),
            software_version_chunk=software_version_chunk,
            file_paths_chunk=file_paths_chunk,
            all_data_chunk=all_data_chunk,
        )

    @staticmethod
    def get_read_mode() -> ReadMode:
        raise NotImplementedError

    @staticmethod
    def get_data_point_cls() -> type[DataPoint]:
        raise NotImplementedError

    @staticmethod
    def _parse_metadata(metadata: str) -> dict:
        metadata_dict: dict = {}
        metadata_lines = metadata.splitlines()
        for metadata_line in metadata_lines:
            line_split = metadata_line.split("\t")
            if line_split[0] not in METADATA_PREFIXES:
                msg = f"Unrecognized metadata {line_split[0]}"
                raise AllotropeConversionError(msg)
            metadata_dict[line_split[0]] = line_split[1]
        # TODO put more metadata in the right spots
        return metadata_dict

    @staticmethod
    def get_read_type(procedure_details: str) -> ReadType:
        # TODO parse the rest of the procedure details
        if ReadType.KINETIC.value in procedure_details:
            return ReadType.KINETIC
        elif ReadType.AREASCAN.value in procedure_details:
            return ReadType.AREASCAN
        elif ReadType.SPECTRAL.value in procedure_details:
            return ReadType.SPECTRAL

        # check for this last, because other modes still contain the word "Endpoint"
        return ReadType.ENDPOINT

    @staticmethod
    def _parse_procedure_chunk(
        procedure_chunk: list[str],
        read_mode: ReadMode,
        read_names: list,
    ) -> None:
        # if no user-defined name is specified for protocols,
        # e.g. it just says "Absorbance Endpoint",
        # Gen5 defaults to using the wavelength as the name
        use_wavelength_names = False
        read_line_length = 2
        wavelength_line_length = 2
        for line in procedure_chunk:
            split_line = line.strip().split("\t")
            if split_line[0] == "Read":
                if len(split_line) != read_line_length:
                    msg = f"Unrecognized Read data {split_line}"
                    raise AllotropeConversionError(msg)
                if split_line[-1] == f"{read_mode.title()} Endpoint":
                    use_wavelength_names = True
                else:
                    read_names.append(split_line[-1])
            elif split_line[0].startswith("Wavelengths"):
                if use_wavelength_names:
                    split_line_colon = split_line[0].split(":  ")
                    if len(split_line_colon) != wavelength_line_length:
                        msg = f"Unrecognized Wavelengths data {split_line}"
                        raise AllotropeConversionError(msg)
                    read_names.extend(split_line_colon[-1].split(", "))

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
    def _parse_layout(
        layout_str: str,
        layout: dict,
        concentrations: dict,
    ) -> None:
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

    @staticmethod
    def _parse_actual_temperature(actual_temperature: str) -> float:
        if len(actual_temperature.split("\n")) != 1:
            msg = f"Unrecognized temperature data {actual_temperature}"
            raise AllotropeConversionError(msg)
        return float(actual_temperature.strip().split("\t")[-1])

    @staticmethod
    def _parse_results(
        results: str,
        wells: list,
        read_mode: ReadMode,
        read_names: list,
        processed_datas: defaultdict[str, list],
        measurements: defaultdict[str, list],
        data_point_cls: type[DataPoint],
        read_type: ReadType,
        plate_barcode: str,
        layout: dict,
        concentrations: dict,
        actual_temperature: Optional[float],
        measurement_docs: list,
    ) -> None:
        result_lines = results.splitlines()
        if result_lines[0].strip() != "Results":
            msg = f"Unrecognized results data {result_lines[0]}"
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
                if well_pos not in wells:
                    wells.append(well_pos)
                well_value: Union[str, float] = try_float(values[col_num])
                if PlateData._is_processed_data_label(
                    label,
                    read_mode,
                    read_names,
                ):
                    processed_datas[well_pos].append([label, well_value])
                else:
                    label_only = label.split(":")[-1]
                    measurements[well_pos].append([label_only, well_value])

        for well_pos in wells:
            datapoint = data_point_cls(
                read_type,
                measurements[well_pos],
                well_pos,
                plate_barcode,
                layout.get(well_pos),
                concentrations.get(well_pos),
                processed_datas[well_pos],
                actual_temperature,
            )
            measurement_docs.append(datapoint.to_measurement_doc())

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

    @staticmethod
    def _parse_stdcurve(
        stdcurve: str,
        plate_barcode: str,
        wells: list,
    ) -> list:
        lines = stdcurve.splitlines()
        num_lines = 2
        if len(lines) != num_lines:
            msg = f"Unrecognized std curve data {lines}"
            raise AllotropeConversionError(msg)
        keys = lines[0].split("\t")
        values = lines[1].split("\t")
        return [
            {
                "statistical feature": key,
                "feature": try_float(value),
                "group": f"{plate_barcode} {wells[0]}-{wells[-1]}",
            }
            for key, value in zip(keys, values)
        ]

    @staticmethod
    def _parse_kinetic_data(
        kinetic_data: str,
        wells: list,
        measurements: defaultdict[str, list],
    ) -> tuple[list[int], list]:
        kinetic_data_io = StringIO(kinetic_data)
        df = pd.read_table(kinetic_data_io)
        df_columns = kinetic_data.split("\n")[0].split("\t")
        df = df[
            df["A1"].notna()
        ]  # drop incomplete rows, particularly rows only with "0:00:00"

        kinetic_times = [PlateData._hhmmss_to_sec(hhmmss) for hhmmss in df["Time"]]
        temperatures = df[df_columns[1]].replace(np.nan, None).tolist()
        has_temperatures = any(temp is not None for temp in temperatures)
        for well_pos in df_columns[
            2:
        ]:  # first column is Time, second column is T∞ READ_NAME with no values
            wells.append(well_pos)
            values = df[well_pos].tolist()
            if has_temperatures:
                measurements[well_pos].extend(
                    list(zip(kinetic_times, values, temperatures))
                )
            else:
                measurements[well_pos].extend(list(zip(kinetic_times, values)))

        return kinetic_times, temperatures

    @staticmethod
    def _parse_blank_kinetic_data(
        blank_kinetic_data: str,
        blank_kinetic_data_label: Optional[str],
        processed_datas: defaultdict[str, list],
        read_type: ReadType,
        read_mode: ReadMode,
        data_point_cls: type[DataPoint],
        kinetic_times: Optional[list[int]],
    ) -> None:
        blank_kinetic_data_io = StringIO(blank_kinetic_data)
        df = pd.read_table(blank_kinetic_data_io)
        df.dropna(axis=0)  # drop incomplete rows
        df_columns = blank_kinetic_data.split("\n")[0].split("\t")

        for well_pos in df_columns[1:]:  # first column is Time
            measures = df[well_pos].tolist()
            processed_datas[well_pos].append(
                [
                    blank_kinetic_data_label,
                    PlateData._blank_data_cube(
                        measures,
                        read_type,
                        read_mode,
                        data_point_cls,
                        kinetic_times,
                    ),
                ]
            )

    @staticmethod
    def _blank_data_cube(
        measures: list[float],
        read_type: ReadType,
        read_mode: ReadMode,
        data_point_cls: type[DataPoint],
        kinetic_times: Optional[list[int]],
    ) -> TDatacube:
        structure_dimensions = READTYPE_TO_DIMENSIONS[read_type]
        structure_measures = [("double", read_mode.lower(), data_point_cls.unit)]
        return TDatacube(
            label=f"{read_type.value.lower()} data",
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
            data=TDatacubeData([kinetic_times], [measures]),  # type: ignore[list-item]
        )

    @staticmethod
    def _hhmmss_to_sec(hhmmss: str) -> int:
        # convert to seconds, as specified by Allotrope
        hours, minutes, seconds = tuple(int(num) for num in hhmmss.split(":"))
        return (3600 * hours) + (60 * minutes) + seconds

    def to_allotrope(self, measurement_docs: list) -> Any:
        raise NotImplementedError
