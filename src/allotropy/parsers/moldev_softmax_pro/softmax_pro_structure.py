from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Optional
import uuid

import pandas as pd

from allotropy.allotrope.models.fluorescence_benchling_2023_09_fluorescence import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentFluorescence,
    DeviceControlDocumentItem as DeviceControlDocumentItemFluorescence,
    MeasurementAggregateDocument as MeasurementAggregateDocumentFluorescence,
    MeasurementDocumentItem as MeasurementDocumentItemFluorescence,
    Model as ModelFluorescence,
)
from allotropy.allotrope.models.luminescence_benchling_2023_09_luminescence import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentLuminescence,
    DeviceControlDocumentItem as DeviceControlDocumentItemLuminescence,
    MeasurementAggregateDocument as MeasurementAggregateDocumentLuminescence,
    MeasurementDocumentItem as MeasurementDocumentItemLuminescence,
    Model as ModelLuminescence,
)
from allotropy.allotrope.models.shared.components.plate_reader import (
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueNanometer,
    TQuantityValueNumber,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)
from allotropy.allotrope.models.ultraviolet_absorbance_benchling_2023_09_ultraviolet_absorbance import (
    DeviceControlAggregateDocument as DeviceControlAggregateDocumentAbsorbance,
    DeviceControlDocumentItem as DeviceControlDocumentItemAbsorbance,
    MeasurementAggregateDocument as MeasurementAggregateDocumentAbsorbance,
    MeasurementDocumentItem as MeasurementDocumentItemAbsorbance,
    Model as ModelAbsorbance,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.lines_reader import CsvReader, ListCsvReader
from allotropy.parsers.utils.values import (
    assert_not_none,
    natural_sort_key,
    PrimitiveValue,
    try_int,
    try_int_or_none,
    value_or_none,
)

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"
EXPORT_VERSION = "1.3"
START_LETTER_CODE = ord("A")


def split_wavelengths(
    values: Optional[str], delimiter: str = " "
) -> Optional[list[int]]:
    if values is None:
        return None
    return [int(value) for value in values.split(delimiter)]


def get_well_coordinates(row_number: int, column_number: str) -> str:
    row_letters = ""
    while row_number > 0:
        row_number, remainder = divmod(row_number - 1, 26)
        row_letters = chr(START_LETTER_CODE + remainder) + row_letters
    return row_letters + str(column_number)


class ReadType(Enum):
    ENDPOINT = "Endpoint"
    KINETIC = "Kinetic"
    SPECTRUM = "Spectrum"
    WELL_SCAN = "Well Scan"


class ExportFormat(Enum):
    TIME_FORMAT = "TimeFormat"
    PLATE_FORMAT = "PlateFormat"


class DataType(Enum):
    RAW = "Raw"
    REDUCED = "Reduced"


@dataclass(frozen=True)
class Block:
    block_type: str
    raw_lines: list[str]

    @staticmethod
    def create(lines_reader: CsvReader) -> Block:
        block_cls_by_type: dict[str, type[Block]] = {
            "Group": GroupBlock,
            "Note": NoteBlock,
            "Plate": PlateBlock,
        }

        for key, cls in block_cls_by_type.items():
            if lines_reader.match(f"^{key}"):
                return cls.create(lines_reader)

        error = f"Expected block '{lines_reader.get()}' to start with one of {sorted(block_cls_by_type.keys())}."
        raise AllotropeConversionError(error)


@dataclass(frozen=True)
class GroupBlock(Block):
    block_type: str
    name: str
    group_data: list[str]

    @staticmethod
    def create(lines_reader: CsvReader) -> GroupBlock:
        return GroupBlock(
            block_type="Group",
            raw_lines=lines_reader.lines,
            name=(lines_reader.pop() or "").removeprefix("Group: "),
            group_data=list(lines_reader.pop_until("Group Column")),
        )


# TODO do we need to do anything with these?
@dataclass(frozen=True)
class NoteBlock(Block):
    @staticmethod
    def create(lines_reader: CsvReader) -> NoteBlock:
        return NoteBlock(block_type="Note", raw_lines=lines_reader.lines)


@dataclass
class WellData:
    values: list[Optional[float]]
    dimensions: list[Optional[PrimitiveValue]]
    wavelengths: list[Optional[int]]
    temperature: Optional[str]
    processed_data: list[float]

    @staticmethod
    def create() -> WellData:
        return WellData(
            values=[],
            dimensions=[],
            wavelengths=[],
            temperature=None,
            processed_data=[],
        )

    def add_value(
        self,
        value: float,
        dimension: Optional[PrimitiveValue],
        temperature: Optional[str],
        wavelength: Optional[int],
    ) -> None:
        self.values.append(value)
        self.dimensions.append(dimension)
        self.wavelengths.append(wavelength)
        if temperature is not None:
            if self.temperature is not None and temperature != self.temperature:
                error = f"Expected all measurements to have the same temperature, but two have differing values of {self.temperature} and {temperature}."
                raise AllotropeConversionError(error)
            self.temperature = temperature

    @property
    def is_empty(self) -> bool:
        return not self.dimensions or not self.values


@dataclass
class PlateHeader:
    name: str
    export_version: str
    export_format: str
    read_type: str
    data_type: str
    kinetic_points: int
    num_wavelengths: Optional[int]
    wavelengths: list[int]
    num_columns: int
    num_wells: int
    concept: str
    read_mode: str
    unit: str
    pmt_gain: Optional[str]
    num_rows: int
    excitation_wavelengths: Optional[list[int]]
    cutoff_filters: Optional[list[int]]


@dataclass(frozen=True)
class PlateBlock(Block):
    block_type: str
    header: PlateHeader
    well_data: defaultdict[str, WellData]

    @staticmethod
    def create(lines_reader: CsvReader) -> PlateBlock:
        raw_header_series = assert_not_none(
            lines_reader.pop_as_series(sep="\t"),
            msg="Unable to get plate block header",
        )
        header_series = raw_header_series.replace("", None).str.strip()

        cls = PlateBlock.get_plate_block_cls(header_series)
        header = cls.parse_header(header_series)

        well_data: defaultdict[str, WellData] = defaultdict(WellData.create)

        split_lines = [
            [value_or_none(value) for value in raw_line.split("\t")]
            for raw_line in lines_reader.lines
        ]
        data_header = split_lines[1]
        data_lines = split_lines[2:]

        if header.export_format == ExportFormat.TIME_FORMAT.value:
            PlateBlock._parse_time_format_data(
                header,
                well_data,
                data_header,
                data_lines,
            )
        elif header.export_format == ExportFormat.PLATE_FORMAT.value:
            PlateBlock._parse_plate_format_data(
                header,
                well_data,
                data_header,
                data_lines,
            )
        else:
            error = f"unrecognized export format {header.export_format}"
            raise AllotropeConversionError(error)

        return cls(
            block_type="Plate",
            raw_lines=lines_reader.lines,
            header=header,
            well_data=well_data,
        )

    @staticmethod
    def get_plate_block_cls(header_series: pd.Series[str]) -> type[PlateBlock]:
        plate_block_cls: dict[str, type[PlateBlock]] = {
            "Absorbance": AbsorbancePlateBlock,
            "Fluorescence": FluorescencePlateBlock,
            "Luminescence": LuminescencePlateBlock,
        }
        read_mode = header_series[5]
        cls = plate_block_cls.get(read_mode or "")
        if cls is None:
            msg = msg_for_error_on_unrecognized_value(
                "read mode", read_mode, plate_block_cls.keys()
            )
            raise AllotropeConversionError(msg)
        return cls

    @staticmethod
    def _parse_reduced_plate_rows(
        num_columns: int,
        data_header: list[Optional[str]],
        well_data: defaultdict[str, WellData],
        reduced_data_rows: list[list[Optional[str]]],
    ) -> None:
        for i, row in enumerate(reduced_data_rows):
            for j, value in enumerate(row[2 : num_columns + 2]):
                if value is None:
                    continue
                col_number = assert_not_none(data_header[j + 2], "column number")
                well = get_well_coordinates(i + 1, col_number)
                well_data[well].processed_data.append(float(value))

    @staticmethod
    def _parse_reduced_columns(
        data_header: list[Optional[str]],
        well_data: defaultdict[str, WellData],
        reduced_data_row: list[Optional[str]],
    ) -> None:
        for i, value in enumerate(reduced_data_row[2:]):
            if value is None:
                continue
            well = assert_not_none(data_header[i + 2], "well")
            well_data[well].processed_data.append(float(value))

    @staticmethod
    def _add_data_point(
        read_type: Optional[str],
        well_data: defaultdict[str, WellData],
        well: str,
        value: str,
        data_key: Optional[str],
        temperature: Optional[str],
        wavelength: Optional[int],
    ) -> None:
        dimension = wavelength if read_type == ReadType.ENDPOINT.value else data_key
        well_data[well].add_value(
            value=float(value),
            dimension=dimension,
            temperature=temperature,
            wavelength=wavelength,
        )

    @staticmethod
    def _parse_time_format_data(
        header: PlateHeader,
        well_data: defaultdict[str, WellData],
        data_header: list[Optional[str]],
        data_lines: list[list[Optional[str]]],
    ) -> None:
        if header.data_type == DataType.RAW.value:
            num_row_blocks = (
                header.num_wavelengths if header.num_wavelengths is not None else 1
            )
            for wavelength_index in range(num_row_blocks):
                start_index = wavelength_index * (header.kinetic_points + 1)
                wavelength_rows = data_lines[
                    start_index : start_index + header.kinetic_points
                ]
                for row in wavelength_rows:
                    for i, value in enumerate(row[2 : header.num_wells + 2]):
                        if value is None:
                            continue
                        well = assert_not_none(data_header[i + 2], "well")
                        PlateBlock._add_data_point(
                            header.read_type,
                            well_data,
                            well,
                            value,
                            data_key=row[0],
                            temperature=row[1],
                            wavelength=PlateBlock.get_wavelength(
                                header, wavelength_index
                            ),
                        )
            if len(data_lines) > (header.kinetic_points + 1) * num_row_blocks:
                reduced_row = data_lines[-1][: header.num_wells + 2]
                PlateBlock._parse_reduced_columns(data_header, well_data, reduced_row)
        elif header.data_type == DataType.REDUCED.value:
            reduced_row = data_lines[-1][: header.num_wells + 2]
            PlateBlock._parse_reduced_columns(data_header, well_data, reduced_row)
        else:
            msg = msg_for_error_on_unrecognized_value(
                "data type", header.data_type, DataType._member_names_
            )
            raise AllotropeConversionError(msg)

    @staticmethod
    def _parse_plate_format_data(
        header: PlateHeader,
        well_data: defaultdict[str, WellData],
        data_header: list[Optional[str]],
        data_lines: list[list[Optional[str]]],
    ) -> None:
        end_raw_data_index = 0
        if header.data_type == DataType.RAW.value:
            for read_index in range(header.kinetic_points):
                start_index = read_index * (header.num_rows + 1)
                read_rows = data_lines[start_index : start_index + header.num_rows]
                data_key = read_rows[0][0]
                temperature = read_rows[0][1]
                for i, row in enumerate(read_rows):
                    wavelength_index = 0
                    num_row_blocks = (
                        header.num_wavelengths
                        if header.num_wavelengths is not None
                        else 1
                    )
                    for wavelength_index in range(num_row_blocks):
                        col_start_index = 2 + (
                            wavelength_index * (header.num_columns + 1)
                        )
                        for j, value in enumerate(
                            row[col_start_index : col_start_index + header.num_columns]
                        ):
                            if value is None:
                                continue
                            col_number = assert_not_none(
                                data_header[j + 2], "column number"
                            )
                            well = get_well_coordinates(i + 1, col_number)
                            PlateBlock._add_data_point(
                                header.read_type,
                                well_data,
                                well,
                                value,
                                data_key=data_key,
                                temperature=temperature,
                                wavelength=PlateBlock.get_wavelength(
                                    header,
                                    wavelength_index,
                                ),
                            )
            end_raw_data_index = ((header.num_rows + 1) * header.kinetic_points) + 1
            reduced_data_rows = data_lines[end_raw_data_index:]
            if len(reduced_data_rows) == header.num_rows:
                PlateBlock._parse_reduced_plate_rows(
                    header.num_columns,
                    data_header,
                    well_data,
                    reduced_data_rows,
                )
        elif header.data_type == DataType.REDUCED.value:
            reduced_data_rows = data_lines[end_raw_data_index:]
            PlateBlock._parse_reduced_plate_rows(
                header.num_columns, data_header, well_data, reduced_data_rows
            )
        else:
            msg = msg_for_error_on_unrecognized_value(
                "data type", header.data_type, DataType._member_names_
            )
            raise AllotropeConversionError(msg)

    @staticmethod
    def parse_header(header: pd.Series[str]) -> PlateHeader:
        raise NotImplementedError

    @property
    def is_single_wavelength(self) -> bool:
        return (
            self.header.read_type in {ReadType.SPECTRUM.value, ReadType.ENDPOINT.value}
            and len(self.header.wavelengths) == 1
        )

    @property
    def has_wavelength_dimension(self) -> bool:
        return (
            self.header.read_type
            not in {ReadType.SPECTRUM.value, ReadType.ENDPOINT.value}
            and len(self.header.wavelengths) > 1
        )

    @staticmethod
    def get_wavelength(
        header: PlateHeader,
        wavelength_index: int,
    ) -> Optional[int]:
        if header.read_type == ReadType.SPECTRUM.value:
            return None
        else:
            return header.wavelengths[wavelength_index] if header.wavelengths else None

    def get_data_cube_dimensions(self) -> list[tuple[str, str, Optional[str]]]:
        dimensions: list[tuple[str, str, Optional[str]]] = []
        if self.header.read_type == ReadType.KINETIC.value:
            dimensions = [("double", "elapsed time", "s")]
        elif self.header.read_type == ReadType.WELL_SCAN.value:
            dimensions = [("int", "x", None)]
        elif self.header.read_type in {
            ReadType.SPECTRUM.value,
            ReadType.ENDPOINT.value,
        }:
            dimensions = [("int", "wavelength", "nm")]
        else:
            error = f"Cannot make data cube for read type {self.header.read_type}; only {sorted(ReadType._member_names_)} are supported."
            raise AllotropeConversionError(error)
        if self.has_wavelength_dimension:
            dimensions.append(("int", "wavelength", "nm"))
        return dimensions

    def generate_sample_document(self, well: str) -> SampleDocument:
        return SampleDocument(
            well_location_identifier=well, plate_barcode=self.header.name
        )

    def generate_data_cube(self, well_data: WellData) -> TDatacube:
        dimension_data = [well_data.dimensions] + (
            [well_data.wavelengths] if self.has_wavelength_dimension else []
        )
        return TDatacube(
            cube_structure=TDatacubeStructure(
                [
                    TDatacubeComponent(FieldComponentDatatype(data_type), concept, unit)
                    for data_type, concept, unit in self.get_data_cube_dimensions()
                ],
                [
                    TDatacubeComponent(
                        FieldComponentDatatype("double"),
                        self.header.concept,
                        self.header.unit,
                    )
                ],
            ),
            data=TDatacubeData(
                dimension_data,  # type: ignore[arg-type]
                [well_data.values],
            ),
        )

    def generate_processed_data_aggreate_document(
        self, well_data: WellData
    ) -> ProcessedDataAggregateDocument:
        return ProcessedDataAggregateDocument(
            [
                ProcessedDataDocumentItem(
                    val, data_processing_description="processed data"
                )
                for val in well_data.processed_data
            ]
        )

    def to_allotrope(self) -> Any:
        raise NotImplementedError


@dataclass(frozen=True)
class PlateBlockExtraAttr:
    concept: str
    read_mode: str
    unit: str
    pmt_gain: Optional[str]
    num_rows: int
    excitation_wavelengths: Optional[list[int]]
    cutoff_filters: Optional[list[int]]


@dataclass(frozen=True)
class FluorescencePlateBlock(PlateBlock):
    @staticmethod
    def parse_header(header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            _,  # Read mode
            _,
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            _,  # read_time_or_scan_pattern
            _,  # read_interval_or_scan_density
            _,  # start_wavelength
            _,  # end_wavelength
            _,  # wavelength_step
            num_wavelengths_raw,
            wavelengths_str,
            _,  # first_column
            num_columns_raw,
            num_wells_raw,
            excitation_wavelengths_str,
            _,  # cutoff
            cutoff_filters_str,
            _,  # sweep_wave
            _,  # sweep_wavelength
            _,  # reads_per_well
            pmt_gain,
            _,  # start_integration_time
            _,  # end_integration_time
            _,  # first_row
            num_rows,
        ] = header[:31]

        if export_version != EXPORT_VERSION:
            error = f"Unsupported export version {export_version}; only {EXPORT_VERSION} is supported."
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=try_int_or_none(num_wavelengths_raw),
            wavelengths=split_wavelengths(wavelengths_str) or [],
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="fluorescence",
            read_mode="Fluorescence",
            unit="RFU",
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=split_wavelengths(excitation_wavelengths_str),
            cutoff_filters=split_wavelengths(cutoff_filters_str),
        )

    # TODO: the reason we can't factor out DeviceControlDocumentItemFluorescence and the enclosing classes is because the
    # Fluorescence ASM model has these extra fields. We may be able to fix this by templating the PlateBlock
    # class on these classes, or some clever shared/models refactoring.
    def generate_device_control_doc(self) -> DeviceControlDocumentItemFluorescence:
        device_control_doc = DeviceControlDocumentItemFluorescence(
            detector_gain_setting=self.header.pmt_gain
        )

        if self.is_single_wavelength:
            device_control_doc.detector_wavelength_setting = TQuantityValueNanometer(
                self.header.wavelengths[0]
            )
        if (
            self.header.excitation_wavelengths
            and len(self.header.excitation_wavelengths) == 1
        ):
            device_control_doc.excitation_wavelength_setting = TQuantityValueNanometer(
                self.header.excitation_wavelengths[0]
            )
        if self.header.cutoff_filters and len(self.header.cutoff_filters) == 1:
            device_control_doc.wavelength_filter_cutoff_setting = (
                TQuantityValueNanometer(self.header.cutoff_filters[0])
            )

        return device_control_doc

    def generate_measurement_doc(
        self, well: str, well_data: WellData
    ) -> MeasurementDocumentItemFluorescence:
        measurement = MeasurementDocumentItemFluorescence(
            DeviceControlAggregateDocumentFluorescence(
                [self.generate_device_control_doc()]
            ),
            self.generate_sample_document(well),
        )

        if well_data.temperature is not None:
            measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                float(well_data.temperature)
            )

        if not well_data.is_empty:
            measurement.data_cube = self.generate_data_cube(well_data)

        if well_data.processed_data:
            measurement.processed_data_aggregate_document = (
                self.generate_processed_data_aggreate_document(well_data)
            )

        return measurement

    def to_allotrope(self) -> Any:
        wells = sorted(self.well_data.keys(), key=natural_sort_key)

        allotrope_file = ModelFluorescence(
            measurement_aggregate_document=MeasurementAggregateDocumentFluorescence(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(self.header.num_wells),
                measurement_document=[
                    self.generate_measurement_doc(well, self.well_data[well])
                    for well in wells
                ],
            )
        )

        return allotrope_file


@dataclass(frozen=True)
class LuminescencePlateBlock(PlateBlock):
    @staticmethod
    def parse_header(header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            _,  # Read mode
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            _,  # read_time_or_scan_pattern
            _,  # read_interval_or_scan_density
            _,  # start_wavelength
            _,  # end_wavelength
            _,  # wavelength_step
            num_wavelengths_raw,
            wavelengths_str,
            _,  # first_column
            num_columns_raw,
            num_wells_raw,
            excitation_wavelengths_str,
            _,  # cutoff
            cutoff_filters_str,
            _,  # sweep_wave
            _,  # sweep_wavelength
            _,  # reads_per_well
            pmt_gain,
            _,  # start_integration_time
            _,  # end_integration_time
            _,  # first_row
            num_rows,
        ] = header[:30]

        if export_version != EXPORT_VERSION:
            error = f"Invalid export version {export_version}"
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=try_int_or_none(num_wavelengths_raw),
            wavelengths=split_wavelengths(wavelengths_str) or [],
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="luminescence",
            read_mode="Luminescence",
            unit="RLU",
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=split_wavelengths(excitation_wavelengths_str),
            cutoff_filters=split_wavelengths(cutoff_filters_str),
        )

    def generate_device_control_doc(self) -> DeviceControlDocumentItemLuminescence:
        device_control_doc = DeviceControlDocumentItemLuminescence(
            detector_gain_setting=self.header.pmt_gain
        )

        if self.is_single_wavelength:
            device_control_doc.detector_wavelength_setting = TQuantityValueNanometer(
                self.header.wavelengths[0]
            )

        return device_control_doc

    def generate_measurement_doc(
        self, well: str, well_data: WellData
    ) -> MeasurementDocumentItemLuminescence:
        measurement = MeasurementDocumentItemLuminescence(
            DeviceControlAggregateDocumentLuminescence(
                [self.generate_device_control_doc()]
            ),
            self.generate_sample_document(well),
        )

        if well_data.temperature is not None:
            measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                float(well_data.temperature)
            )

        if not well_data.is_empty:
            measurement.data_cube = self.generate_data_cube(well_data)

        if well_data.processed_data:
            measurement.processed_data_aggregate_document = (
                self.generate_processed_data_aggreate_document(well_data)
            )

        return measurement

    def to_allotrope(self) -> Any:
        wells = sorted(self.well_data.keys(), key=natural_sort_key)

        allotrope_file = ModelLuminescence(
            measurement_aggregate_document=MeasurementAggregateDocumentLuminescence(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(self.header.num_wells),
                measurement_document=[
                    self.generate_measurement_doc(well, self.well_data[well])
                    for well in wells
                ],
            )
        )

        return allotrope_file


@dataclass(frozen=True)
class AbsorbancePlateBlock(PlateBlock):
    @staticmethod
    def parse_header(header: pd.Series[str]) -> PlateHeader:
        [
            _,  # Plate:
            name,
            export_version,
            export_format,
            read_type,
            _,  # Read mode
            data_type,
            _,  # Pre-read, always FALSE
            kinetic_points_raw,
            _,  # read_time_or_scan_pattern
            _,  # read_interval_or_scan_density
            _,  # start_wavelength
            _,  # end_wavelength
            _,  # wavelength_step
            num_wavelengths_raw,
            wavelengths_str,
            _,  # first_column
            num_columns_raw,
            num_wells_raw,
            _,
            num_rows_raw,
        ] = header[:21]

        if export_version != EXPORT_VERSION:
            error = f"Invalid export version {export_version}"
            raise AllotropeConversionError(error)

        return PlateHeader(
            name=name,
            export_version=export_version,
            export_format=export_format,
            read_type=read_type,
            data_type=data_type,
            kinetic_points=try_int(kinetic_points_raw, "kinetic_points"),
            num_wavelengths=try_int_or_none(num_wavelengths_raw),
            wavelengths=split_wavelengths(wavelengths_str) or [],
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="absorbance",
            read_mode="Absorbance",
            unit="mAU",
            pmt_gain=None,
            num_rows=try_int(num_rows_raw, "num_rows"),
            excitation_wavelengths=None,
            cutoff_filters=None,
        )

    def generate_device_control_doc(self) -> DeviceControlDocumentItemAbsorbance:
        device_control_doc = DeviceControlDocumentItemAbsorbance(
            detector_gain_setting=self.header.pmt_gain
        )

        if self.is_single_wavelength:
            device_control_doc.detector_wavelength_setting = TQuantityValueNanometer(
                self.header.wavelengths[0]
            )

        return device_control_doc

    def generate_measurement_doc(
        self, well: str, well_data: WellData
    ) -> MeasurementDocumentItemAbsorbance:
        measurement = MeasurementDocumentItemAbsorbance(
            DeviceControlAggregateDocumentAbsorbance(
                [self.generate_device_control_doc()]
            ),
            self.generate_sample_document(well),
        )

        if well_data.temperature is not None:
            measurement.compartment_temperature = TQuantityValueDegreeCelsius(
                float(well_data.temperature)
            )

        if not well_data.is_empty:
            measurement.data_cube = self.generate_data_cube(well_data)

        if well_data.processed_data:
            measurement.processed_data_aggregate_document = (
                self.generate_processed_data_aggreate_document(well_data)
            )

        return measurement

    def to_allotrope(self) -> Any:
        wells = sorted(self.well_data.keys(), key=natural_sort_key)

        allotrope_file = ModelAbsorbance(
            measurement_aggregate_document=MeasurementAggregateDocumentAbsorbance(
                measurement_identifier=str(uuid.uuid4()),
                plate_well_count=TQuantityValueNumber(self.header.num_wells),
                measurement_document=[
                    self.generate_measurement_doc(well, self.well_data[well])
                    for well in wells
                ],
            )
        )

        return allotrope_file


@dataclass(frozen=True)
class BlockList:
    blocks: list[Block]

    @staticmethod
    def create(lines_reader: CsvReader) -> BlockList:
        return BlockList(
            blocks=[
                Block.create(block) for block in BlockList._iter_blocks(lines_reader)
            ]
        )

    @staticmethod
    def _get_n_blocks(lines_reader: CsvReader) -> int:
        start_line = lines_reader.pop() or ""
        if search_result := re.search(BLOCKS_LINE_REGEX, start_line):
            return int(search_result.group(1))
        msg = msg_for_error_on_unrecognized_value("start line", start_line)
        raise AllotropeConversionError(msg)

    @staticmethod
    def _iter_blocks(lines_reader: CsvReader) -> Iterator[CsvReader]:
        n_blocks = BlockList._get_n_blocks(lines_reader)
        for _ in range(n_blocks):
            yield ListCsvReader(list(lines_reader.pop_until(END_LINE_REGEX)))
            lines_reader.pop()  # drop end line
            lines_reader.drop_empty()


@dataclass(frozen=True)
class Data:
    block_list: BlockList

    def get_plate_block(self) -> PlateBlock:
        plate_blocks = [
            block for block in self.block_list.blocks if isinstance(block, PlateBlock)
        ]

        if len(plate_blocks) != 1:
            block_types = [block.block_type for block in self.block_list.blocks]
            block_counts = {bt: block_types.count(bt) for bt in set(block_types)}
            error = f"Expected exactly 1 plate block; got {block_counts}."
            raise AllotropeConversionError(error)

        return plate_blocks[0]

    @staticmethod
    def create(lines_reader: CsvReader) -> Data:
        return Data(block_list=BlockList.create(lines_reader))
