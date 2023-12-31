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
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import (
    assert_not_none,
    natural_sort_key,
    num_to_chars,
    PrimitiveValue,
    str_or_none,
    try_float,
    try_float_or_none,
    try_int,
    try_int_or_none,
)

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"
EXPORT_VERSION = "1.3"


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
    def create(reader: CsvReader) -> Block:
        block_cls_by_type: dict[str, type[Block]] = {
            "Group": GroupBlock,
            "Note": NoteBlock,
            "Plate": PlateBlock,
        }

        for key, cls in block_cls_by_type.items():
            if reader.match(f"^{key}"):
                return cls.create(reader)

        error = f"Expected block '{reader.get()}' to start with one of {sorted(block_cls_by_type.keys())}."
        raise AllotropeConversionError(error)


@dataclass(frozen=True)
class GroupBlock(Block):
    block_type: str
    name: str
    group_data: list[str]

    @staticmethod
    def create(reader: CsvReader) -> GroupBlock:
        return GroupBlock(
            block_type="Group",
            raw_lines=reader.lines,
            name=(reader.pop() or "").removeprefix("Group: "),
            group_data=list(reader.pop_until("Group Column")),
        )


# TODO do we need to do anything with these?
@dataclass(frozen=True)
class NoteBlock(Block):
    @staticmethod
    def create(reader: CsvReader) -> NoteBlock:
        return NoteBlock(block_type="Note", raw_lines=reader.lines)


@dataclass
class WellData:
    values: list[Optional[float]]
    dimensions: list[Optional[PrimitiveValue]]
    wavelengths: list[Optional[int]]
    temperature: Optional[float]
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
        temperature: Optional[float],
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


@dataclass(frozen=True)
class PlateHeader:
    name: str
    export_version: str
    export_format: str
    read_type: str
    data_type: str
    kinetic_points: int
    num_wavelengths: int
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
class WavelengthElement:
    row: str
    col: str
    value: float

    @property
    def pos(self) -> str:
        return f"{self.row}{self.col}"


@dataclass(frozen=True)
class PlateWavelengthData:
    wavelength_data: pd.DataFrame

    @staticmethod
    def create(data: pd.DataFrame) -> PlateWavelengthData:
        rows, _ = data.shape
        data.index = pd.Index([num_to_chars(i) for i in range(rows)])
        return PlateWavelengthData(wavelength_data=data)

    def iter_elements(self) -> Iterator[WavelengthElement]:
        for letter, row in self.wavelength_data.iterrows():
            for number, value in row.items():
                yield WavelengthElement(
                    row=str(letter),
                    col=str(number),
                    value=try_float(value, "well data point"),
                )


@dataclass(frozen=True)
class PlateKineticData:
    data_key: Optional[str]
    temperature: Optional[float]
    wavelength_data: list[PlateWavelengthData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
        columns: pd.Series[str],
    ) -> PlateKineticData:
        data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t"),
            msg="unable to find data from plate block.",
        )
        data.columns = pd.Index(columns)

        raw_data_key = data.iloc[0, 0]
        raw_temperature = data.iloc[0, 1]

        return PlateKineticData(
            data_key=str_or_none(raw_data_key),
            temperature=try_float_or_none(str(raw_temperature)),
            wavelength_data=list(
                PlateKineticData._iter_wavelength_data(header, data.iloc[:, 2:])
            ),
        )

    @staticmethod
    def _iter_wavelength_data(
        header: PlateHeader, w_data: pd.DataFrame
    ) -> Iterator[PlateWavelengthData]:
        for idx in range(header.num_wavelengths):
            start = idx * (header.num_columns + 1)
            end = start + header.num_columns
            yield PlateWavelengthData.create(w_data.iloc[:, start:end])


@dataclass(frozen=True)
class PlateRawData:
    kinetic_data: list[PlateKineticData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> Optional[PlateRawData]:
        if header.data_type == DataType.REDUCED.value:
            return None

        columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find data columns for plate block raw data.",
        )

        return PlateRawData(
            kinetic_data=[
                PlateKineticData.create(reader, header, columns)
                for _ in range(header.kinetic_points)
            ]
        )


@dataclass(frozen=True)
class PlateReducedData:
    reduced_data: pd.DataFrame

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> Optional[PlateReducedData]:
        if not reader.current_line_exists():
            return None

        raw_data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t", header=0),
            msg="Unable to find reduced data for plate block.",
        )
        data = raw_data.iloc[:, 2 : header.num_columns + 2]
        rows, _ = data.shape
        data.index = pd.Index([num_to_chars(i) for i in range(rows)])
        return PlateReducedData(reduced_data=data)

    def iter_elements(self) -> Iterator[WavelengthElement]:
        for letter, row in self.reduced_data.iterrows():
            for number, value in row.items():
                yield WavelengthElement(
                    row=str(letter),
                    col=str(number),
                    value=try_float(value, "well data point"),
                )


@dataclass(frozen=True)
class PlateData:
    raw_data: Optional[PlateRawData]
    reduced_data: Optional[PlateReducedData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> PlateData:
        return PlateData(
            raw_data=PlateRawData.create(reader, header),
            reduced_data=PlateReducedData.create(reader, header),
        )

    def get_raw_data(self) -> PlateRawData:
        return assert_not_none(
            self.raw_data,
            msg="Unable to find plate block raw data.",
        )

    def get_reduced_data(self) -> PlateReducedData:
        return assert_not_none(
            self.reduced_data,
            msg="Unable to find plate block reduced data.",
        )


@dataclass(frozen=True)
class TimeWavelengthRow:
    data_key: float
    temperature: float
    data: pd.Series[float]

    @staticmethod
    def create(row: pd.Series[float]) -> TimeWavelengthRow:
        return TimeWavelengthRow(
            data_key=row.iloc[0],
            temperature=row.iloc[1],
            data=row.iloc[2:],
        )


@dataclass(frozen=True)
class TimeWavelengthData:
    data: pd.DataFrame

    def iter_wavelength_rows(self) -> Iterator[TimeWavelengthRow]:
        for _, row in self.data.iterrows():
            yield TimeWavelengthRow.create(row)


@dataclass(frozen=True)
class TimeRawData:
    wavelength_data: list[TimeWavelengthData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> Optional[TimeRawData]:
        if header.data_type == DataType.REDUCED.value:
            return None

        columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find data columns for time block raw data.",
        )
        data = assert_not_none(
            reader.pop_csv_block_as_df(sep="\t"),
            msg="unable to find raw data from time block.",
        )
        data.columns = pd.Index(columns)
        return TimeRawData(
            wavelength_data=list(TimeRawData._iter_wavelength_data(header, data)),
        )

    @staticmethod
    def _iter_wavelength_data(
        header: PlateHeader, data: pd.DataFrame
    ) -> Iterator[TimeWavelengthData]:
        for idx in range(header.num_wavelengths):
            start = idx * (header.kinetic_points + 1)
            end = start + header.kinetic_points
            yield TimeWavelengthData(data.iloc[start:end, :])


@dataclass(frozen=True)
class TimeReducedData:
    columns: list[str]
    data: list[str]

    @staticmethod
    def create(reader: CsvReader) -> Optional[TimeReducedData]:
        if not reader.current_line_exists():
            return None

        _, _, *columns = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find columns for time block reduced data.",
        )
        _, _, *data = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="unable to find reduced data from time block.",
        )
        return TimeReducedData(columns, data)

    def iter_data(self) -> Iterator[tuple[str, float]]:
        for pos, value in zip(self.columns, self.data):
            yield pos, try_float(value, "time block reduced data element")


@dataclass(frozen=True)
class TimeData:
    raw_data: Optional[TimeRawData]
    reduced_data: Optional[TimeReducedData]

    @staticmethod
    def create(
        reader: CsvReader,
        header: PlateHeader,
    ) -> TimeData:
        return TimeData(
            raw_data=TimeRawData.create(reader, header),
            reduced_data=TimeReducedData.create(reader),
        )

    def get_raw_data(self) -> TimeRawData:
        return assert_not_none(
            self.raw_data,
            msg="Unable to find plate block raw data.",
        )

    def get_reduced_data(self) -> TimeReducedData:
        return assert_not_none(
            self.reduced_data,
            msg="Unable to find plate block reduced data.",
        )


@dataclass(frozen=True)
class PlateBlock(Block):
    block_type: str
    header: PlateHeader
    well_data: defaultdict[str, WellData]

    @staticmethod
    def create(reader: CsvReader) -> PlateBlock:
        header_series = PlateBlock.read_header(reader)
        cls = PlateBlock.get_plate_block_cls(header_series)
        header = cls.parse_header(header_series)
        well_data: defaultdict[str, WellData] = defaultdict(WellData.create)

        if header.export_format == ExportFormat.TIME_FORMAT.value:
            PlateBlock._parse_time_format_data(
                header,
                well_data,
                time_data=TimeData.create(reader, header),
            )
        elif header.export_format == ExportFormat.PLATE_FORMAT.value:
            PlateBlock._parse_plate_format_data(
                header,
                well_data,
                plate_data=PlateData.create(reader, header),
            )
        else:
            error = f"unrecognized export format {header.export_format}"
            raise AllotropeConversionError(error)

        return cls(
            block_type="Plate",
            raw_lines=reader.lines,
            header=header,
            well_data=well_data,
        )

    @staticmethod
    def read_header(reader: CsvReader) -> pd.Series[str]:
        raw_header_series = assert_not_none(
            reader.pop_as_series(sep="\t"),
            msg="Unable to find plate block header.",
        )
        return raw_header_series.replace("", None).str.strip()

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
    def _add_data_point(
        header: PlateHeader,
        well_data: defaultdict[str, WellData],
        well: str,
        value: float,
        data_key: Optional[str],
        temperature: Optional[float],
        wavelength_index: int,
    ) -> None:
        wavelength = (
            header.wavelengths[wavelength_index]
            if header.read_type != ReadType.SPECTRUM.value
            else None
        )
        dimension = (
            wavelength if header.read_type == ReadType.ENDPOINT.value else data_key
        )
        well_data[well].add_value(
            value=value,
            dimension=dimension,
            temperature=temperature,
            wavelength=wavelength,
        )

    @staticmethod
    def _parse_time_format_data(
        header: PlateHeader,
        well_data: defaultdict[str, WellData],
        time_data: TimeData,
    ) -> None:
        if header.data_type == DataType.RAW.value:
            for idx, wavelength_data in enumerate(
                time_data.get_raw_data().wavelength_data
            ):
                for wavelength_row in wavelength_data.iter_wavelength_rows():
                    for pos, val in wavelength_row.data.items():
                        PlateBlock._add_data_point(
                            header,
                            well_data,
                            str(pos),
                            val,
                            data_key=str(int(wavelength_row.data_key)),
                            temperature=wavelength_row.temperature,
                            wavelength_index=idx,
                        )
            if time_data.reduced_data:
                for pos, val in time_data.reduced_data.iter_data():
                    well_data[pos].processed_data.append(val)
        elif header.data_type == DataType.REDUCED.value:
            for pos, val in time_data.get_reduced_data().iter_data():
                well_data[pos].processed_data.append(val)
        else:
            msg = msg_for_error_on_unrecognized_value(
                "data type", header.data_type, DataType._member_names_
            )
            raise AllotropeConversionError(msg)

    @staticmethod
    def _parse_plate_format_data(
        header: PlateHeader,
        well_data: defaultdict[str, WellData],
        plate_data: PlateData,
    ) -> None:
        if header.data_type == DataType.RAW.value:
            for kinetic_data in plate_data.get_raw_data().kinetic_data:
                for idx, wavelength_data in enumerate(kinetic_data.wavelength_data):
                    for wavelength_element in wavelength_data.iter_elements():
                        PlateBlock._add_data_point(
                            header,
                            well_data,
                            wavelength_element.pos,
                            wavelength_element.value,
                            data_key=kinetic_data.data_key,
                            temperature=kinetic_data.temperature,
                            wavelength_index=idx,
                        )
            if plate_data.reduced_data:
                for reduced_element in plate_data.reduced_data.iter_elements():
                    well_data[reduced_element.pos].processed_data.append(
                        reduced_element.value
                    )
        elif header.data_type == DataType.REDUCED.value:
            for reduced_element in plate_data.get_reduced_data().iter_elements():
                well_data[reduced_element.pos].processed_data.append(
                    reduced_element.value
                )
        else:
            msg = msg_for_error_on_unrecognized_value(
                "data type", header.data_type, DataType._member_names_
            )
            raise AllotropeConversionError(msg)

    @staticmethod
    def split_wavelengths(values: Optional[str]) -> Optional[list[int]]:
        return None if values is None else [int(v) for v in values.split()]

    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
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
    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
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
            num_wavelengths=try_int_or_none(num_wavelengths_raw) or 1,
            wavelengths=PlateBlock.split_wavelengths(wavelengths_str) or [],
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="fluorescence",
            read_mode="Fluorescence",
            unit="RFU",
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=PlateBlock.split_wavelengths(
                excitation_wavelengths_str
            ),
            cutoff_filters=PlateBlock.split_wavelengths(cutoff_filters_str),
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
                well_data.temperature
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
    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
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
            num_wavelengths=try_int_or_none(num_wavelengths_raw) or 1,
            wavelengths=PlateBlock.split_wavelengths(wavelengths_str) or [],
            num_columns=try_int(num_columns_raw, "num_columns"),
            num_wells=try_int(num_wells_raw, "num_wells"),
            concept="luminescence",
            read_mode="Luminescence",
            unit="RLU",
            pmt_gain=pmt_gain,
            num_rows=try_int(num_rows, "num_rows"),
            excitation_wavelengths=PlateBlock.split_wavelengths(
                excitation_wavelengths_str
            ),
            cutoff_filters=PlateBlock.split_wavelengths(cutoff_filters_str),
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
                well_data.temperature
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
    @classmethod
    def parse_header(cls, header: pd.Series[str]) -> PlateHeader:
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
            num_wavelengths=try_int_or_none(num_wavelengths_raw) or 1,
            wavelengths=PlateBlock.split_wavelengths(wavelengths_str) or [],
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
                well_data.temperature
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
    def create(reader: CsvReader) -> BlockList:
        return BlockList(
            blocks=[Block.create(block) for block in BlockList._iter_blocks(reader)]
        )

    @staticmethod
    def _get_n_blocks(reader: CsvReader) -> int:
        start_line = reader.pop() or ""
        if search_result := re.search(BLOCKS_LINE_REGEX, start_line):
            return int(search_result.group(1))
        msg = msg_for_error_on_unrecognized_value("start line", start_line)
        raise AllotropeConversionError(msg)

    @staticmethod
    def _iter_blocks(reader: CsvReader) -> Iterator[CsvReader]:
        n_blocks = BlockList._get_n_blocks(reader)
        for _ in range(n_blocks):
            yield CsvReader(list(reader.pop_until(END_LINE_REGEX)))
            reader.pop()  # drop end line
            reader.drop_empty()


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
    def create(reader: CsvReader) -> Data:
        return Data(block_list=BlockList.create(reader))
