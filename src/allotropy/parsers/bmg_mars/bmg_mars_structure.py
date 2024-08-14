from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from io import StringIO
import re

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
)
from allotropy.allotrope.models.shared.definitions.definitions import InvalidJsonFloat
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.pandas import read_csv, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


class ReadType(Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"


@dataclass(frozen=True)
class Header:
    user: str
    test_name: str
    date: str
    time: str
    id1: str
    id2: str | None
    id3: str | None
    path: str | None
    test_id: str | None

    @staticmethod
    def create(reader: list[str]) -> Header:
        csv_stream = StringIO("\n".join(reader))
        raw_data = read_csv(csv_stream, header=None)
        df = pd.melt(raw_data, value_vars=raw_data.columns.to_list()).dropna(
            axis="index"
        )
        new = df["value"].str.split(": ", expand=True, n=1)
        data = SeriesData(pd.Series(new[1].values, index=new[0].str.upper()))
        return Header(
            user=assert_not_none(data.get(str, "USER"), msg="User not found in file."),
            path=data.get(str, "PATH"),
            test_id=data.get(str, "TEST ID"),
            test_name=assert_not_none(
                data.get(str, "TEST NAME"), msg="User not found in file."
            ),
            date=assert_not_none(
                data.get(str, "DATE"), msg="Datestamp not found in file."
            ),
            time=assert_not_none(
                data.get(str, "TIME"), msg="Timestamp not found in file."
            ),
            id1=assert_not_none(data.get(str, "ID1"), msg="ID1 not found in file."),
            id2=data.get(str, "ID2"),
            id3=data.get(str, "ID3"),
        )


@dataclass(frozen=True)
class Wavelength:
    wavelength: float
    ex_wavelength: float | InvalidJsonFloat

    @staticmethod
    def create(csv_data: list[str]) -> Wavelength:
        raw_wavelengths = assert_not_none(
            re.search(
                r"Raw Data \((?P<wavelength1>\d+)(?:/)?(?P<wavelength2>\d+)?(?:\))",
                "\n".join(csv_data),
            ),
            msg="Wavelengths not found in input file.",
        )
        if raw_wavelengths.group("wavelength2"):
            return Wavelength(
                wavelength=float(raw_wavelengths.group("wavelength2")),
                ex_wavelength=float(raw_wavelengths.group("wavelength1")),
            )
        else:  # wavelength 1 only
            return Wavelength(
                wavelength=float(raw_wavelengths.group("wavelength1")),
                ex_wavelength=InvalidJsonFloat.NaN,
            )


def get_plate_data(csv_data: list[str]) -> pd.DataFrame:
    csv_reader = CsvReader(csv_data)
    raw_data = assert_not_none(
        csv_reader.lines_as_df(csv_data, skiprows=2),
        msg="Dataframe not found.",
    )
    raw_data.rename(columns={0: "row"}, inplace=True)
    data = raw_data.melt(id_vars=["row"], var_name="col", value_name="value")
    data.dropna(inplace=True)
    data["uuid"] = [random_uuid_str() for _ in range(len(data))]
    return data


def get_plate_well_count(csv_data: list[str]) -> TQuantityValueNumber:
    if re.search(r"23,24\nA", "\n".join(csv_data)):
        plate_well_count = 384
    if re.search(r"11,12\nA", "\n".join(csv_data)):
        plate_well_count = 384
    return TQuantityValueNumber(value=plate_well_count)
