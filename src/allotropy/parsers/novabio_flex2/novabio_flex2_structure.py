from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import numpy as np
import pandas as pd

from allotropy.exceptions import (
    AllotropeConversionError,
    get_key_or_error,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.constants import (
    ANALYTE_MAPPINGS,
    BLOOD_GAS_DETECTION_MAPPINGS,
    CELL_COUNTER_MAPPINGS,
    CONCENTRATION_CLASSES,
    CONCENTRATION_CLS_BY_UNIT,
    FILENAME_REGEX,
    INVALID_FILENAME_MESSAGE,
    OSMOLALITY_DETECTION_MAPPINGS,
    PH_DETECTION_MAPPINGS,
)
from allotropy.parsers.utils.pandas import read_csv, SeriesData
from allotropy.parsers.utils.values import try_float_or_none


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
    concentration: CONCENTRATION_CLASSES

    @staticmethod
    def create(raw_name: str, value: float) -> Analyte:
        mapping = get_key_or_error("analyte name", raw_name, ANALYTE_MAPPINGS)
        return Analyte(
            mapping["name"],
            CONCENTRATION_CLS_BY_UNIT[mapping["unit"]](value=value),
        )

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Analyte):
            return NotImplemented

        return self.name < other.name


@dataclass(frozen=True)
class Sample:
    identifier: str
    sample_type: str
    measurement_time: str
    batch_identifier: str | None
    analytes: list[Analyte]
    cell_counter_properties: dict[str, Any]
    blood_gas_properties: dict[str, Any]
    osmolality_properties: dict[str, Any]
    ph_properties: dict[str, Any]
    cell_type_processing_method: str | None
    cell_density_dilution_factor: float | None

    @classmethod
    def create(cls, series: pd.Series[Any]) -> Sample:
        data = SeriesData(series)
        cell_density_dilution = data.get(str, "Cell Density Dilution", "")
        if cell_density_dilution:
            cell_density_dilution = cell_density_dilution.split(":")[0]

        return Sample(
            identifier=data[str, "Sample ID"],
            sample_type=data[str, "Sample Type"],
            measurement_time=data[str, "Date & Time"],
            batch_identifier=data.get(str, "Batch ID"),
            analytes=sorted(
                [
                    Analyte.create(raw_name, data[float, raw_name])
                    for raw_name in ANALYTE_MAPPINGS
                    if data.get(float, raw_name) is not None
                ]
            ),
            cell_counter_properties=cls._get_properties(data, CELL_COUNTER_MAPPINGS),
            blood_gas_properties=cls._get_properties(
                data, BLOOD_GAS_DETECTION_MAPPINGS
            ),
            osmolality_properties=cls._get_properties(
                data, OSMOLALITY_DETECTION_MAPPINGS
            ),
            ph_properties=cls._get_properties(data, PH_DETECTION_MAPPINGS),
            cell_type_processing_method=data.get(str, "Cell Type"),
            cell_density_dilution_factor=try_float_or_none(str(cell_density_dilution)),
        )

    @classmethod
    def _get_properties(
        cls, data: SeriesData, property_mappings: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            property_name: property_dict["cls"](
                value=data.get(float, property_dict["col_name"])
            )
            for property_name, property_dict in property_mappings.items()
            if data.get(float, property_dict["col_name"]) is not None
        }


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
            analyst=str(analyst),
            samples=[Sample.create(sample_data) for sample_data in sample_data_rows],
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
