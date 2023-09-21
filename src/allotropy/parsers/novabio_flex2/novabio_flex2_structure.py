from __future__ import annotations

from dataclasses import dataclass
import io
import re
from typing import Any, Optional

import numpy as np
import pandas as pd

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.novabio_flex2.constants import (
    ANALYTE_MAPPINGS,
    FILENAME_REGEX,
    INVALID_FILENAME_MESSAGE,
    MOLAR_CONCENTRATION_CLASSES,
    MOLAR_CONCENTRATION_CLS_BY_UNIT,
    PROPERTY_MAPPINGS,
)


@dataclass
class Title:
    processing_time: str
    device_identifier: Optional[str]

    @staticmethod
    def create(filename: str) -> Title:
        matches = re.match(FILENAME_REGEX, filename)

        if not matches:
            raise AllotropeConversionError(
                filename, INVALID_FILENAME_MESSAGE.format(filename)
            )

        matches_dict = matches.groupdict()
        return Title(
            processing_time=matches_dict["processing_time"].replace("_", " "),
            device_identifier=matches_dict["device_identifier"] or None,
        )


@dataclass
class Analyte:
    name: str
    molar_concentration: MOLAR_CONCENTRATION_CLASSES

    @staticmethod
    def create(raw_name: str, value: float) -> Analyte:
        if raw_name not in ANALYTE_MAPPINGS:
            msg = "Invalid analyte name"
            raise AllotropeConversionError(msg)

        mapping = ANALYTE_MAPPINGS[raw_name]
        return Analyte(
            mapping["name"],
            MOLAR_CONCENTRATION_CLS_BY_UNIT[mapping["unit"]](value=value),
        )

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Analyte):
            return NotImplemented

        return self.name < other.name


@dataclass
class Sample:
    identifier: str
    role_type: str
    measurement_time: str
    batch_identifier: Optional[str]
    analytes: list[Analyte]
    properties: dict[str, Any]

    @staticmethod
    def create(data: pd.Series) -> Sample:
        properties: dict[str, Any] = {
            property_name: property_dict["cls"](data[property_dict["col_name"]])
            for property_name, property_dict in PROPERTY_MAPPINGS.items()
            if property_dict["col_name"] in data
            and data[property_dict["col_name"]] is not None
        }

        batch_identifier = data.get("Batch ID")

        return Sample(
            identifier=data["Sample ID"],
            role_type=data["Sample Type"],
            measurement_time=data["Date & Time"].isoformat(),
            batch_identifier=str(batch_identifier) if batch_identifier else None,
            analytes=sorted(
                [
                    Analyte.create(raw_name, data[raw_name])
                    for raw_name in ANALYTE_MAPPINGS
                    if raw_name in data
                ]
            ),
            properties=properties,
        )


@dataclass
class SampleList:
    analyst: str
    samples: list[Sample]

    @staticmethod
    def create(data: pd.DataFrame) -> SampleList:
        sample_data_rows = [row for _, row in data.iterrows()]

        if not sample_data_rows:
            msg = "Unable to get any sample"
            raise AllotropeConversionError(msg)

        analyst = sample_data_rows[0].get("Operator")

        if analyst is None:
            msg = "Unable to get analyst from data"
            raise AllotropeConversionError(msg)

        return SampleList(
            str(analyst),
            [Sample.create(sample_data) for sample_data in sample_data_rows],
        )


@dataclass
class Data:
    title: Title
    sample_list: SampleList

    @staticmethod
    def create(contents: io.IOBase, filename: str) -> Data:
        # NOTE: type ignore is an issue with pandas typing, it accepts an io.IOBase that implements read.
        data = pd.read_csv(contents, parse_dates=["Date & Time"]).replace(np.nan, None)  # type: ignore[call-overload]
        return Data(Title.create(filename), SampleList.create(data))
