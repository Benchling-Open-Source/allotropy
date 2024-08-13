from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import numpy as np
import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.exceptions import (
    AllotropeConversionError,
    get_key_or_error,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.constants import (
    ANALYTE_MAPPINGS,
    FILENAME_REGEX,
    INVALID_FILENAME_MESSAGE,
    MOLAR_CONCENTRATION_CLASSES,
    MOLAR_CONCENTRATION_CLS_BY_UNIT,
    PROPERTY_MAPPINGS,
)
from allotropy.parsers.utils.pandas import SeriesData


@dataclass(frozen=True)
class Title:
    processing_time: str
    device_identifier: str | None

    @staticmethod
    def create(filename: str) -> Title:
        matches = re.match(FILENAME_REGEX, filename, flags=re.IGNORECASE)

        if not matches:
            raise AllotropeConversionError(INVALID_FILENAME_MESSAGE.format(filename))

        matches_dict = matches.groupdict()
        return Title(
            processing_time=matches_dict["processing_time"].replace("_", " "),
            device_identifier=matches_dict["device_identifier"] or None,
        )


@dataclass(frozen=True)
class Analyte:
    name: str
    molar_concentration: MOLAR_CONCENTRATION_CLASSES

    @staticmethod
    def create(raw_name: str, value: float) -> Analyte:
        mapping = get_key_or_error("analyte name", raw_name, ANALYTE_MAPPINGS)
        return Analyte(
            mapping["name"],
            MOLAR_CONCENTRATION_CLS_BY_UNIT[mapping["unit"]](value=value),
        )

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Analyte):
            return NotImplemented

        return self.name < other.name


@dataclass(frozen=True)
class Sample:
    identifier: str
    role_type: str
    measurement_time: str
    batch_identifier: str | None
    analytes: list[Analyte]
    properties: dict[str, Any]

    @staticmethod
    def create(series: pd.Series[Any]) -> Sample:
        data = SeriesData(series)
        properties: dict[str, Any] = {
            property_name: property_dict["cls"](
                value=data.get(float, property_dict["col_name"])
            )
            for property_name, property_dict in PROPERTY_MAPPINGS.items()
            if data.get(float, property_dict["col_name"]) is not None
        }
        return Sample(
            identifier=data[str, "Sample ID"],
            role_type=data[str, "Sample Type"],
            measurement_time=data[str, "Date & Time"],
            batch_identifier=data.get(str, "Batch ID"),
            analytes=sorted(
                [
                    Analyte.create(raw_name, data[float, raw_name])
                    for raw_name in ANALYTE_MAPPINGS
                    if data.get(float, raw_name) is not None
                ]
            ),
            properties=properties,
        )


@dataclass(frozen=True)
class SampleList:
    analyst: str
    samples: list[Sample]

    @staticmethod
    def create(data: pd.DataFrame) -> SampleList:
        sample_data_rows = [row for _, row in data.iterrows()]

        if not sample_data_rows:
            msg = "Unable to find any sample."
            raise AllotropeConversionError(msg)

        analyst = sample_data_rows[0].get("Operator")

        if analyst is None:
            msg = "Unable to find the Operator."
            raise AllotropeConversionError(msg)

        return SampleList(
            str(analyst),
            [Sample.create(sample_data) for sample_data in sample_data_rows],
        )


@dataclass(frozen=True)
class Data:
    title: Title
    sample_list: SampleList

    @staticmethod
    def create(named_file_contents: NamedFileContents) -> Data:
        contents = named_file_contents.contents
        filename = named_file_contents.original_file_name
        data = read_csv(contents, parse_dates=["Date & Time"]).replace(np.nan, None)
        return Data(Title.create(filename), SampleList.create(data))
