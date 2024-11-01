from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from re import Match
from typing import ClassVar, TypeAlias

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    valid_value_or_raise,
)
from allotropy.parsers.bmg_mars import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


class ReadType(Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"
    LUMINESCENCE = "Luminescence"

    @property
    def measurement_type(self) -> MeasurementType:
        if self is ReadType.ABSORBANCE:
            return MeasurementType.ULTRAVIOLET_ABSORBANCE
        elif self is ReadType.LUMINESCENCE:
            return MeasurementType.LUMINESCENCE
        else:
            return MeasurementType.FLUORESCENCE

    @property
    def device_type(self) -> str:
        return f"{self.detection_type} detector"

    @property
    def detection_type(self) -> str:
        return self.value.lower()


FilterHandler: TypeAlias = Callable[[Match[str]], tuple[float | None, float | None]]


@dataclass(frozen=True)
class Header:
    read_type: ReadType
    wavelength: float | None
    excitation_wavelength: float | None
    user: str
    test_name: str
    date: str
    time: str
    id1: str
    id2: str | None
    id3: str | None
    path: str | None
    test_id: str | None

    FILTER_FORMATS: ClassVar[dict[str, tuple[str, FilterHandler]]] = {
        "Raw Data (Ex/Em)": (
            r"Raw Data \((\d+\.?\d*)/(\d+\.?\d*)\)",
            lambda m: (float(m.group(2)), float(m.group(1))),
        ),
        "Raw Data (Em)": (
            r"Raw Data \((\d+\.?\d*)\)",
            lambda m: (float(m.group(1)), None),
        ),
        "Raw Data (No filter)": (
            r"Raw Data \(No filter\)",
            lambda _: (None, None),
        ),
    }

    @staticmethod
    def create(data: SeriesData, header_content: str) -> Header:
        # Search for read type in header content
        read_types = {
            read_type
            for read_type in ReadType
            if read_type.value.lower() in header_content.lower()
        }
        read_type = valid_value_or_raise("read type", read_types, ReadType)

        # Get wavelengths from RawData line
        raw_data_line = assert_not_none(
            re.search(r"Raw Data \(.*?\)", header_content),
            msg="Raw Data line not found in input file.",
        ).group(0)

        # iterate over filter formats, to parse Ex/Em
        for _, (pattern, handler) in Header.FILTER_FORMATS.items():
            match = re.match(pattern, raw_data_line)
            if match:
                try:
                    wavelength, excitation_wavelength = handler(match)
                    break
                except ValueError as err:
                    msg = f"Failed to convert filters in line: '{raw_data_line}'"
                    raise AllotropeConversionError(msg) from err
        else:
            msg = (
                f"Invalid Raw Data format: '{raw_data_line}'. "
                "Expected/supported formats include: "
                f"{', '.join(Header.FILTER_FORMATS.keys())}"
            )
            raise AllotropeConversionError(msg)

        return Header(
            read_type=read_type,
            wavelength=wavelength,
            excitation_wavelength=excitation_wavelength,
            user=data[str, "USER"],
            path=data.get(str, "PATH"),
            test_id=data.get(str, "TEST ID"),
            test_name=data[str, "TEST NAME"],
            date=data[str, "DATE"],
            time=data[str, "TIME"],
            id1=data[str, "ID1"],
            id2=data.get(str, "ID2"),
            id3=data.get(str, "ID3"),
        )


def create_metadata(header: Header, file_path: str) -> Metadata:
    asm_file_identifier = Path(file_path).with_suffix(".json")
    return Metadata(
        file_name=Path(file_path).name,
        asm_file_identifier=asm_file_identifier.name,
        unc_path=header.path or file_path,
        device_identifier=NOT_APPLICABLE,
        model_number=NOT_APPLICABLE,
        data_system_instance_id=NOT_APPLICABLE,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_name=constants.SOFTWARE_NAME,
    )


def _create_measurement(
    row_name: str,
    col_name: str,
    value: float,
    header: Header,
) -> Measurement:
    well_location = f"{row_name}{col_name}"
    return Measurement(
        type_=header.read_type.measurement_type,
        identifier=random_uuid_str(),
        sample_identifier=f"{header.id1} {well_location}",
        location_identifier=well_location,
        well_plate_identifier=header.id1,
        device_type=header.read_type.device_type,
        detection_type=header.read_type.detection_type,
        detector_wavelength_setting=header.wavelength,
        excitation_wavelength_setting=header.excitation_wavelength,
        absorbance=value if header.read_type is ReadType.ABSORBANCE else None,
        fluorescence=value if header.read_type is ReadType.FLUORESCENCE else None,
        luminescence=value if header.read_type is ReadType.LUMINESCENCE else None,
    )


def create_measurement_groups(
    data: pd.DataFrame,
    header: Header,
) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            measurement_time=f"{header.date} {header.time}",
            plate_well_count=data.size,
            experiment_type=header.test_name,
            experimental_data_identifier=header.id2,
            analyst=header.user,
            measurements=[
                _create_measurement(str(row_name), str(col_name), value, header)
            ],
        )
        for row_name, row in data.iterrows()
        for col_name, value in row.items()
        if not pd.isnull(value)
    ]
