from __future__ import annotations

from dataclasses import dataclass

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
class DataV2:
    background_info: BackgroundInfo
    results: Results

    @staticmethod
    def create(reader: CsvReader) -> DataV2:
        return DataV2(
            background_info=BackgroundInfo.create(reader),
            results=Results.create(reader),
        )
