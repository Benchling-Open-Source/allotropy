from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from io import StringIO
import re
from typing import Optional

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
)
from allotropy.parsers.lines_reader import read_csv
from allotropy.parsers.utils.values import (
    try_str_from_series,
    try_str_from_series_or_none,
)

RE_READ_TYPE = r"Fluorescence \(FP\)(?=,)|^Fluorescence(?=,)|^Fluorescence \(FI\)(?=,)|^Absorbance(?=,)|^Time resolved fluorescence \(dual emission\)(?=,)"


class ReadType(Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"
    LUMINESCENCE = "Luminescence"


@dataclass(frozen=True)
class Header:
    user: str
    test_name: str
    date: str
    time: str
    id1: str
    id2: Optional[str] = None
    id3: Optional[str] = None
    path: Optional[str] = None
    test_id: Optional[str] = None

    @staticmethod
    def create(reader: list[str]) -> Header:
        csv_stream = StringIO("\n".join(reader))
        raw_data = read_csv(csv_stream, header=None)
        df = pd.melt(raw_data, value_vars=raw_data.columns).dropna(axis="index")
        new = df["value"].str.split(": ", expand=True, n=1)
        data = pd.Series(new[1])
        data.index = new[0].str.upper()

        return Header(
            user=try_str_from_series(data, "USER"),
            path=try_str_from_series_or_none(data, "PATH"),
            test_id=try_str_from_series_or_none(data, "TEST ID"),
            test_name=try_str_from_series(data, "TEST NAME"),
            date=try_str_from_series(data, "DATE"),
            time=try_str_from_series(data, "TIME"),
            id1=try_str_from_series(data, "ID1"),
            id2=try_str_from_series_or_none(data, "ID2"),
            id3=try_str_from_series_or_none(data, "ID3"),
        )


@dataclass(frozen=True)
class Wavelength:
    wavelength: float
    ex_wavelength: Optional[float] = None

    @staticmethod
    def create(csv_data: list[str]) -> Wavelength:
        raw_wavelengths = re.search(
            r"Raw Data \((?P<wavelength1>\d+)(?:/)?(?P<wavelength2>\d+)?(?:\))",
            "\n".join(csv_data),
        )
        if raw_wavelengths.group("wavelength2"):
            return Wavelength(
                wavelength=float(raw_wavelengths.group("wavelength2")),
                ex_wavelength=float(raw_wavelengths.group("wavelength1")),
            )
        else:
            return Wavelength(wavelength=float(raw_wavelengths.group("wavelength1")))


@dataclass(frozen=True)
class PlateWellCount:
    plate_well_count: TQuantityValueNumber

    @staticmethod
    def create(csv_data: list[str]) -> PlateWellCount:
        if re.search(r"23,24\nA", "\n".join(csv_data)):
            return PlateWellCount(plate_well_count=TQuantityValueNumber(384))
        if re.search(r"11,12\nA", "\n".join(csv_data)):
            return PlateWellCount(plate_well_count=TQuantityValueNumber(96))


@dataclass(frozen=True)
class Result:
    uuid: str
    row: str
    col: str
    value: float
