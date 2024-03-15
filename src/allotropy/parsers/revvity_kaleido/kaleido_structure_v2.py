from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import (
    assert_not_none,
)


@dataclass(frozen=True)
class BackgroundInfo:
    info: str

    @staticmethod
    def create(reader: CsvReader) -> BackgroundInfo:
        line = assert_not_none(
            reader.drop_until_inclusive("^Results for"),
            msg="Unable to find background information.",
        )
        return BackgroundInfo(line)


@dataclass(frozen=True)
class Results:
    barcode: str
    results: pd.DataFrame

    @staticmethod
    def create(reader: CsvReader) -> Results:
        barcode = assert_not_none(
            reader.drop_until_inclusive("^Barcode"),
            msg="Unable to find background information.",
        )

        results = assert_not_none(
            reader.pop_csv_block_as_df(header=0, index_col=0),
            msg="Unable to find results table.",
        )

        return Results(
            barcode=barcode,
            results=results,
        )


@dataclass(frozen=True)
class AnalysisResults:
    @staticmethod
    def create(reader: CsvReader) -> Optional[AnalysisResults]:
        section_title = assert_not_none(
            reader.drop_until("^Results for|^Measurement Basic Information"),
            msg="Unable to find Analysis Result or Measurement Basic Information section.",
        )

        if section_title.startswith("Measurement Basic Information"):
            return None

        return AnalysisResults()


@dataclass(frozen=True)
class MeasurementBasicInfo:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> MeasurementBasicInfo:
        assert_not_none(
            reader.drop_until_inclusive("^Measurement Basic Information"),
            msg="Unable to find Measurement Basic Information section.",
        )

        elements = {}
        for raw_line in reader.pop_until("^Plate Type"):
            if raw_line == "":
                continue

            key, _, value, *_ = raw_line.split(",")
            elements[key.rstrip(":")] = value

        return MeasurementBasicInfo(elements)


@dataclass(frozen=True)
class DataV2:
    background_info: BackgroundInfo
    results: Results
    analysis_results: Optional[AnalysisResults]
    measurement_basic_info: MeasurementBasicInfo

    @staticmethod
    def create(reader: CsvReader) -> DataV2:
        return DataV2(
            background_info=BackgroundInfo.create(reader),
            results=Results.create(reader),
            analysis_results=AnalysisResults.create(reader),
            measurement_basic_info=MeasurementBasicInfo.create(reader),
        )
