# plate (repeated for N plates measured)
#     Plate information
#     Background information (optional)
#     Calculated results (optional)
#     Measured results (repeated for N measurements performed per plate)
# Basic assay information
# Protocol information
# Plate type
# Platemap (repeated for N plates measured)
# Calculations
# Auto export parameters
# Operations
# Labels
#     Filters (dependent on detection modality)
#     Mirrors (dependent on detection modality)
# Instrument
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from re import search

import numpy as np
import pandas as pd

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ScanPositionSettingPlateReader,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.perkin_elmer_envision import constants
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    map_rows,
    SeriesData,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    num_to_chars,
)


class ReadType(Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"
    LUMINESCENCE = "Luminescence"

    @property
    def measurement_type(self) -> MeasurementType:
        if self is ReadType.ABSORBANCE:
            return MeasurementType.ULTRAVIOLET_ABSORBANCE
        elif self is ReadType.FLUORESCENCE:
            return MeasurementType.FLUORESCENCE
        elif self is ReadType.LUMINESCENCE:
            return MeasurementType.LUMINESCENCE

    @property
    def device_type(self) -> str:
        return f"{self.value.lower()} detector"


@dataclass(frozen=True)
class PlateInfo:
    number: str
    barcode: str
    measurement_time: str | None
    measured_height: float | None
    chamber_temperature_at_start: float | None

    @staticmethod
    def get_series(reader: CsvReader) -> SeriesData:
        assert_not_none(
            reader.pop_if_match("^Plate information"),
            msg="Unable to find expected plate information",
        )

        return df_to_series_data(
            assert_not_none(
                reader.pop_csv_block_as_df(header=0),
                "Plate information CSV block",
            ).replace(np.nan, None)
        )

    @staticmethod
    def get_plate_number_and_barcode(data: SeriesData) -> tuple[str, str]:
        plate_number = data[str, "Plate"]
        raw_barcode = data.get(str, "Barcode")
        barcode = (raw_barcode or '=""').removeprefix('="').removesuffix('"')
        barcode = barcode or f"Plate {plate_number}"
        return plate_number, barcode


@dataclass(frozen=True)
class CalculatedPlateInfo(PlateInfo):
    formula: str
    name: str

    @staticmethod
    def create(data: SeriesData) -> CalculatedPlateInfo:
        formula = data[str, "Formula"]

        name = assert_not_none(
            search(r"^([^=]*)=", formula),
            msg="Unable to find expected formula name for calculated results section.",
        ).group(1)

        plate_number, barcode = PlateInfo.get_plate_number_and_barcode(data)

        return CalculatedPlateInfo(
            number=plate_number,
            barcode=barcode,
            measurement_time=data.get(str, "Measurement date"),
            measured_height=data.get(float, "Measured height"),
            chamber_temperature_at_start=data.get(
                float, "Chamber temperature at start"
            ),
            formula=formula,
            name=name.strip(),
        )


@dataclass(frozen=True)
class ResultPlateInfo(PlateInfo):
    label: str
    measinfo: str
    emission_filter_id: str

    @staticmethod
    def create(data: SeriesData) -> ResultPlateInfo | None:
        label = data.get(str, "Label")
        if label is None:
            return None

        measinfo = data.get(str, "Measinfo")
        if measinfo is None:
            return None

        plate_number, barcode = PlateInfo.get_plate_number_and_barcode(data)

        return ResultPlateInfo(
            plate_number,
            barcode,
            data.get(str, "Measurement date"),
            data.get(float, "Measured height"),
            data.get(float, "Chamber temperature at start"),
            label=label,
            measinfo=measinfo,
            emission_filter_id=assert_not_none(
                search("De=(...)", measinfo),
                msg=f"Unable to find emission filter ID for Plate {barcode}.",
            ).group(1),
        )

    def match(self, background_info: BackgroundInfo) -> bool:
        return all(
            [
                background_info.plate_num == self.number,
                background_info.label in self.label,
                background_info.measinfo == self.measinfo,
            ]
        )


@dataclass
class BackgroundInfo:
    plate_num: str
    label: str
    measinfo: str

    @staticmethod
    def create(data: SeriesData) -> BackgroundInfo:
        return BackgroundInfo(
            plate_num=data[str, "Plate"],
            label=data[str, "Label"],
            measinfo=data[str, "MeasInfo"],
        )


def create_background_infos(reader: CsvReader) -> list[BackgroundInfo]:
    title = reader.pop_if_match("^Background information")
    if title is None:
        return []

    data_frame = assert_not_none(
        reader.pop_csv_block_as_df(header=0),
        "background information",
    )
    return map_rows(data_frame, BackgroundInfo.create)


@dataclass
class CalculatedResult:
    col: str
    row: str
    value: float

    @property
    def pos(self) -> str:
        return f"{self.col}{self.row}"


def create_calculated_results(reader: CsvReader) -> list[CalculatedResult]:
    # Calculated results may or may not have a title
    reader.pop_if_match("^Calculated results")

    data_frame = assert_not_none(
        reader.pop_csv_block_as_df(),
        "results data",
    )
    series = (
        data_frame.drop(0, axis="index").drop(0, axis="columns")
        if data_frame.iloc[1, 0] == "A"
        else data_frame
    )
    rows, cols = series.shape
    series.index = pd.Index([num_to_chars(i) for i in range(rows)])
    series.columns = pd.Index([str(i) for i in range(1, cols + 1)])

    return [
        CalculatedResult(
            col=col,
            row=row,
            value=series.loc[col, row],
        )
        for col, row in series.stack().index
    ]


@dataclass
class Result:
    uuid: str
    col: str
    row: str
    value: int


def create_results(reader: CsvReader) -> list[Result]:
    # Results may or may not have a title
    reader.pop_if_match("^Results")

    data_frame = assert_not_none(
        reader.pop_csv_block_as_df(),
        "reader data",
    )
    series = (
        data_frame.drop(0, axis="index").drop(0, axis="columns")
        if data_frame.iloc[1, 0] == "A"
        else data_frame
    )
    rows, cols = series.shape
    series.index = pd.Index([num_to_chars(i) for i in range(rows)])
    series.columns = pd.Index([str(i) for i in range(1, cols + 1)])

    return [
        Result(
            uuid=random_uuid_str(),
            col=col,
            row=row,
            value=int(series.loc[col, row]),
        )
        for col, row in series.stack().index
    ]


@dataclass
class Plate:
    plate_info: PlateInfo
    background_infos: list[BackgroundInfo]


@dataclass
class ResultPlate(Plate):
    plate_info: ResultPlateInfo
    results: list[Result]


@dataclass
class CalculatedPlate(Plate):
    plate_info: CalculatedPlateInfo
    results: list[CalculatedResult]

    def get_source_results(self, plate_list: PlateList) -> Iterator[list[Result]]:
        if not self.background_infos:
            msg = f"Unable to collect result plates for calculated data, there is no background information for plate {self.plate_info.number}"
            raise AllotropeConversionError(msg)

        source_results = [
            assert_not_none(
                plate_list.get_result_plate(background_info),
                msg=f"Unable to find result plate {background_info.label}.",
            ).results
            for background_info in self.background_infos
        ]

        if not all(len(source_results[0]) == len(sr) for sr in source_results):
            msg = f"Unable to collect result plates for calculated data, expected all result plates to have the same number of results, get: {[len(sr) for sr in source_results]}."
            raise AllotropeConversionError(msg)

        yield from [list(tup) for tup in zip(*source_results, strict=True)]

    def get_result_and_sources(
        self, plate_list: PlateList
    ) -> Iterator[tuple[CalculatedResult, list[Result]]]:
        yield from zip(self.results, self.get_source_results(plate_list), strict=True)


def create_plate(reader: CsvReader) -> ResultPlate | CalculatedPlate:
    series = PlateInfo.get_series(reader)
    if result_plate_info := ResultPlateInfo.create(series):
        return ResultPlate(
            plate_info=result_plate_info,
            background_infos=create_background_infos(reader),
            results=create_results(reader),
        )
    else:
        return CalculatedPlate(
            plate_info=CalculatedPlateInfo.create(series),
            background_infos=create_background_infos(reader),
            results=create_calculated_results(reader),
        )


@dataclass
class PlateList:
    results: list[ResultPlate]
    calculated: list[CalculatedPlate]

    @staticmethod
    def create(reader: CsvReader) -> PlateList:
        results: list[ResultPlate] = []
        calculated: list[CalculatedPlate] = []

        while reader.match("^Plate information"):
            plate = create_plate(reader)
            if isinstance(plate, CalculatedPlate):
                calculated.append(plate)
            else:
                results.append(plate)
        return PlateList(results, calculated)

    def get_result_plate(self, background_info: BackgroundInfo) -> ResultPlate | None:
        for plate in self.results:
            if plate.plate_info.match(background_info):
                return plate
        return None

    def get_measurement_time(self) -> str:
        try:
            return min(
                [
                    plate.plate_info.measurement_time
                    for plate in self.results
                    if plate.plate_info.measurement_time
                ]
            )
        except ValueError as err:
            msg = "Unable to determine the measurement time."
            raise AllotropeConversionError(msg) from err


@dataclass(frozen=True)
class BasicAssayInfo:
    protocol_id: str | None
    assay_id: str | None

    @staticmethod
    def create(reader: CsvReader) -> BasicAssayInfo:
        reader.drop_until_inclusive("^Basic assay information")
        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(index_col=0),
            "Basic assay information",
        ).T
        data_frame.columns = (
            data_frame.columns.astype(str).str.replace(":", "").str.strip()
        )
        data = df_to_series_data(data_frame)
        return BasicAssayInfo(data.get(str, "Protocol ID"), data.get(str, "Assay ID"))


@dataclass(frozen=True)
class PlateType:
    number_of_wells: float

    @staticmethod
    def create(reader: CsvReader) -> PlateType:
        reader.drop_until_inclusive("^Plate type")
        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(index_col=0), "Plate type"
        )
        data = df_to_series_data(data_frame.T)
        return PlateType(
            number_of_wells=data[float, "Number of the wells in the plate"]
        )


def get_sample_role_type(encoding: str) -> SampleRoleType:
    # BL        blank               blank_role
    # CTL       control             control_sample_role
    # LB        lance_blank         blank_role
    # LC        lance_crosstalk     control_sample_role
    # LH        lance_high          control_sample_role
    # S         pl_sample           sample_role
    # STD       standard            standard_sample_role
    # -         unknown             unknown_sample_role
    # UNK       unknown             unknown_sample_role
    # ZH        z_high              control_sample_role
    # ZL        z_low               control_sample_role
    sample_role_type_map = {
        "BL": SampleRoleType.blank_role,
        "CTL": SampleRoleType.control_sample_role,
        "LB": SampleRoleType.blank_role,
        "LC": SampleRoleType.control_sample_role,
        "LH": SampleRoleType.control_sample_role,
        "STD": SampleRoleType.standard_sample_role,
        "S": SampleRoleType.sample_role,
        "-": SampleRoleType.unknown_sample_role,
        "UNK": SampleRoleType.unknown_sample_role,
        "ZH": SampleRoleType.control_sample_role,
        "ZL": SampleRoleType.control_sample_role,
    }
    for pattern, value in sample_role_type_map.items():
        if encoding.startswith(pattern):
            return value

    msg = f"Unable to determine sample role type of plate map encoding {encoding}; expected to start with one of {sorted(sample_role_type_map.keys())}."
    raise AllotropeConversionError(msg)


@dataclass(frozen=True)
class PlateMap:
    plate_n: str
    group_n: str
    sample_role_type_mapping: dict[str, dict[str, SampleRoleType]]

    @staticmethod
    def create(reader: CsvReader) -> PlateMap | None:
        if not reader.current_line_exists() or reader.match("^Calculations"):
            return None

        *_, plate_n = assert_not_none(reader.pop(), "Platemap number").split(",")
        *_, group_n = assert_not_none(reader.pop(), "Platemap group").split(",")

        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(),
            "Platemap data",
        ).replace(" ", "", regex=True)

        reader.pop_data()  # drop type specification
        reader.drop_empty()

        series = (
            data_frame.drop(0, axis="index").drop(0, axis="columns")
            if data_frame.iloc[1, 0] == "A"
            else data_frame
        )
        rows, cols = series.shape
        series.index = pd.Index([num_to_chars(i) for i in range(rows)])
        series.columns = pd.Index([str(i) for i in range(1, cols + 1)])

        sample_role_type_mapping: dict[str, dict[str, SampleRoleType]] = {}
        for row, row_data in series.replace([np.nan, "''"], None).to_dict().items():
            col_mapping: dict[str, SampleRoleType] = {}
            for col, value in row_data.items():
                if value:
                    if role_type := get_sample_role_type(str(value)):
                        col_mapping[str(col)] = role_type
            if col_mapping:
                sample_role_type_mapping[str(row)] = col_mapping

        return PlateMap(plate_n, group_n, sample_role_type_mapping)

    def get_sample_role_type(self, col: str, row: str) -> SampleRoleType:
        try:
            return self.sample_role_type_mapping[row][col]
        except KeyError as e:
            msg = (
                f"Invalid plate map location for plate map {self.plate_n}: {col} {row}."
            )
            raise AllotropeConversionError(msg) from e


def create_plate_maps(reader: CsvReader) -> dict[str, PlateMap]:
    assert_not_none(
        reader.drop_until("^Platemap"),
        msg="No 'Platemap' section found.",
    )

    reader.pop()  # remove title

    maps: dict[str, PlateMap] = {}
    while _map := PlateMap.create(reader):
        maps[_map.plate_n] = _map
    return maps


@dataclass(frozen=True)
class Filter:
    name: str
    wavelength: float
    bandwidth: float | None = None

    @staticmethod
    def create(reader: CsvReader) -> Filter | None:
        if not reader.current_line_exists() or reader.match(
            "(^Mirror modules)|(^Instrument:)|(^Aperture:)"
        ):
            return None

        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(index_col=0),
            "Filter information",
        )
        data = df_to_series_data(data_frame.T)
        name = str(data.series.index[0])
        description = data[str, "Description"]

        if search_result := search("Longpass=(\\d+)nm", description):
            return Filter(name, wavelength=float(search_result.group(1)))
        return Filter(
            name,
            wavelength=float(
                assert_not_none(
                    search("CWL=(\\d+)nm", description),
                    msg=f"Unable to find wavelength for filter {name}.",
                ).group(1)
            ),
            bandwidth=float(
                assert_not_none(
                    search(r"BW=([\d ]+)nm", description),
                    msg=f"Unable to find bandwidth for filter {name}.",
                )
                .group(1)
                .replace(" ", "")
            ),
        )


def create_filters(reader: CsvReader) -> dict[str, Filter]:
    reader.drop_until("(^Filters:)|^Instrument:")

    if reader.match("^Instrument"):
        return {}

    reader.pop()  # remove title

    filters = {}
    while _filter := Filter.create(reader):
        filters[_filter.name] = _filter
    return filters


@dataclass(frozen=True)
class Labels:
    label: str
    excitation_filter: Filter | None
    emission_filters: dict[str, Filter | None]
    scan_position_setting: ScanPositionSettingPlateReader | None = None
    number_of_flashes: float | None = None
    detector_gain_setting: str | None = None

    @staticmethod
    def create(reader: CsvReader) -> Labels:
        reader.drop_until_inclusive("^Labels")
        data_frame = assert_not_none(
            reader.pop_csv_block_as_df(index_col=0),
            "Labels",
        )
        data = df_to_series_data(data_frame.T.replace(np.nan, None))
        filters = create_filters(reader)
        filter_position_map = {
            "Bottom": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
            "Top": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
        }

        return Labels(
            label=data.series.index[0],
            excitation_filter=filters.get(data.get(str, "Exc. filter", NOT_APPLICABLE)),
            emission_filters={
                "1st": filters.get(
                    data.get(str, "Ems. filter", NOT_APPLICABLE),
                ),
                "2nd": filters.get(data.get(str, "2nd ems. filter", NOT_APPLICABLE)),
            },
            scan_position_setting=filter_position_map.get(
                data.get(str, "Using of emission filter", NOT_APPLICABLE)
            ),
            number_of_flashes=data.get(float, "Number of flashes"),
            detector_gain_setting=data.get(str, "Reference AD gain"),
        )

    def get_emission_filter(self, id_val: str) -> Filter | None:
        return self.emission_filters.get(id_val)

    def get_read_type(self) -> ReadType:
        patterns = {
            "ABS": ReadType.ABSORBANCE,
            "Absorbance": ReadType.ABSORBANCE,
            "LUM": ReadType.LUMINESCENCE,
            "Luminescence": ReadType.LUMINESCENCE,
            "Fluorescence": ReadType.FLUORESCENCE,
        }
        read_types = {
            read_type for key, read_type in patterns.items() if key in self.label
        }

        if len(read_types) > 1:
            msg = f"Unable to determine unique read type from label: '{self.label}'"
            raise AllotropeConversionError(msg)
        if len(read_types) == 1:
            return read_types.pop()
        # TODO check if this is correct, this is the original behavior
        return ReadType.FLUORESCENCE


@dataclass(frozen=True)
class Instrument:
    serial_number: str
    nickname: str

    @staticmethod
    def create(reader: CsvReader) -> Instrument:
        assert_not_none(
            reader.drop_until("^Instrument"),
            msg="No 'Instrument' section found.",
        )

        reader.pop()  # remove title

        *_, serial_number = assert_not_none(reader.pop(), "serial number").split(",")
        *_, nickname = assert_not_none(reader.pop(), "nickname").split(",")

        return Instrument(serial_number, nickname)


@dataclass(frozen=True)
class Software:
    software_name: str
    software_version: str

    @staticmethod
    def create(reader: CsvReader) -> Software:
        exported_with_regex = "Exported with (.+) version (.+)"
        assert_not_none(
            reader.drop_until(exported_with_regex),
            msg="Unable to find software information; no 'Exported with' section found.",
        )

        search_result = assert_not_none(
            search(
                exported_with_regex,
                assert_not_none(
                    reader.pop(),
                    "software information",
                ),
            )
        )

        return Software(
            software_name=search_result.group(1),
            software_version=search_result.group(2),
        )


@dataclass(frozen=True)
class Data:
    software: Software
    plate_list: PlateList
    basic_assay_info: BasicAssayInfo
    number_of_wells: float
    plate_maps: dict[str, PlateMap]
    labels: Labels
    instrument: Instrument

    @staticmethod
    def create(reader: CsvReader) -> Data:
        return Data(
            plate_list=PlateList.create(reader),
            basic_assay_info=BasicAssayInfo.create(reader),
            number_of_wells=PlateType.create(reader).number_of_wells,
            plate_maps=create_plate_maps(reader),
            labels=Labels.create(reader),
            instrument=Instrument.create(reader),
            software=Software.create(reader),
        )


def create_metadata(
    software: Software, instrument: Instrument, file_path: str
) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        unc_path=file_path,
        asm_file_identifier=path.with_suffix(".json").name,
        software_name=software.software_name,
        software_version=software.software_version,
        model_number=constants.MODEL_NUMBER,
        data_system_instance_id=NOT_APPLICABLE,
        equipment_serial_number=instrument.serial_number,
        device_identifier=instrument.nickname,
    )


def _create_measurement(
    plate_info: ResultPlateInfo,
    result: Result,
    plate_maps: dict[str, PlateMap],
    labels: Labels,
    read_type: ReadType,
) -> Measurement:
    plate_barcode = plate_info.barcode
    well_location = f"{result.col}{result.row}"
    ex_filter = labels.excitation_filter
    em_filter = labels.get_emission_filter(plate_info.emission_filter_id)
    return Measurement(
        type_=read_type.measurement_type,
        device_type=read_type.device_type,
        identifier=result.uuid,
        sample_identifier=f"{plate_barcode} {well_location}",
        well_plate_identifier=plate_barcode,
        location_identifier=well_location,
        sample_role_type=(
            p_map.get_sample_role_type(result.col, result.row)
            if (p_map := plate_maps.get(plate_info.number))
            else None
        ),
        compartment_temperature=plate_info.chamber_temperature_at_start,
        absorbance=result.value if read_type is ReadType.ABSORBANCE else None,
        fluorescence=result.value if read_type is ReadType.FLUORESCENCE else None,
        luminescence=result.value if read_type is ReadType.LUMINESCENCE else None,
        detector_distance_setting=plate_info.measured_height,
        number_of_averages=labels.number_of_flashes,
        detector_gain_setting=labels.detector_gain_setting,
        scan_position_setting=labels.scan_position_setting,
        detector_wavelength_setting=em_filter.wavelength if em_filter else None,
        detector_bandwidth_setting=em_filter.bandwidth if em_filter else None,
        excitation_wavelength_setting=ex_filter.wavelength if ex_filter else None,
        excitation_bandwidth_setting=ex_filter.bandwidth if ex_filter else None,
    )


def create_measurement_groups(data: Data) -> list[MeasurementGroup]:
    read_type = data.labels.get_read_type()
    well_loc_measurements = defaultdict(list)
    for plate in data.plate_list.results:
        for result in plate.results:
            measurement = _create_measurement(
                plate.plate_info,
                result,
                data.plate_maps,
                data.labels,
                read_type,
            )
            well_loc_measurements[
                (plate.plate_info.number, measurement.location_identifier)
            ].append(measurement)

    measurement_time = data.plate_list.get_measurement_time()
    return [
        MeasurementGroup(
            measurement_time=measurement_time,
            plate_well_count=data.number_of_wells,
            analytical_method_identifier=data.basic_assay_info.protocol_id,
            experimental_data_identifier=data.basic_assay_info.assay_id,
            measurements=well_loc_measurements[well_location],
        )
        for well_location in sorted(
            well_loc_measurements.keys(),
            key=lambda key: (key[0], key[1][0], int(key[1][1:])),
        )
    ]
