from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import Optional

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.revvity_kaleido.kaleido_common_structure import (
    PLATEMAP_TO_SAMPLE_ROLE_TYPE,
    WellPosition,
)
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_float_or_none,
)


@dataclass
class BackgroundInfo:
    experiment_type: str


@dataclass(frozen=True)
class Results:
    barcode: str
    results: pd.DataFrame

    def iter_wells(self) -> Iterator[WellPosition]:
        for row, row_series in self.results.iterrows():
            for column in row_series.index:
                yield WellPosition(column=str(column), row=str(row))

    def get_plate_well_dimentions(self) -> tuple[int, int]:
        return self.results.shape

    def get_plate_well_count(self) -> int:
        n_rows, n_columns = self.get_plate_well_dimentions()
        return n_rows * n_columns

    def get_well_float_value(self, well_position: WellPosition) -> float:
        return try_float(
            self.get_well_str_value(well_position),
            f"result well at '{well_position}'",
        )

    def get_well_str_value(self, well_position: WellPosition) -> str:
        try:
            return str(self.results.loc[well_position.row, well_position.column])
        except KeyError as e:
            error = f"Unable to get well at position '{well_position}' from results section."
            raise AllotropeConversionError(error) from e


@dataclass(frozen=True)
class AnalysisResult:
    analysis_parameter: str
    results: pd.DataFrame

    @staticmethod
    def create(reader: CsvReader) -> AnalysisResult:
        barcode_line = assert_not_none(
            reader.drop_until_inclusive("^Barcode:(.+),"),
            msg="Unable to find background information.",
        )

        analysis_parameter = None
        for element in barcode_line.split(","):
            if re.search("^.+:.+$", element):
                key, value = element.split(":", maxsplit=1)
                if "AnalysisParameter" in key:
                    analysis_parameter = value
                    break

        analysis_parameter = assert_not_none(
            analysis_parameter,
            msg="Unable to find analysis parameter in Analysis Results section.",
        )

        results = assert_not_none(
            reader.pop_csv_block_as_df(header=0, index_col=0),
            msg="Unable to find results table.",
        )

        for column in results:
            if str(column).startswith("Unnamed"):
                results = results.drop(columns=column)

        return AnalysisResult(
            analysis_parameter=analysis_parameter,
            results=results,
        )

    def get_image_feature_name(self) -> str:
        return self.analysis_parameter

    def is_valid_result(self) -> bool:
        a1 = WellPosition(column="1", row="A")
        first_result = self.get_result(a1)
        return try_float_or_none(first_result) is not None

    def get_result(self, well_position: WellPosition) -> str:
        try:
            return str(self.results.loc[well_position.row, well_position.column])
        except KeyError as e:
            error = f"Unable to get well at position '{well_position}' from analysis result '{self.analysis_parameter}'."
            raise AllotropeConversionError(error) from e

    def get_image_feature_result(self, well_position: WellPosition) -> float:
        return try_float(
            self.get_result(well_position),
            f"analysis result '{self.analysis_parameter}' at '{well_position}'",
        )


@dataclass(frozen=True)
class PlateType:
    elements: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> PlateType:
        assert_not_none(
            reader.drop_until_inclusive("^Plate Type"),
            msg="Unable to find Plate Type section.",
        )
        reader.drop_until("^Platemap")
        return PlateType({})


@dataclass(frozen=True)
class Platemap:
    data: pd.DataFrame

    def get_well_value(self, well_position: WellPosition) -> str:
        try:
            return str(self.data.loc[well_position.row, well_position.column])
        except KeyError as e:
            error = f"Unable to get well at position '{well_position}' from platemap section."
            raise AllotropeConversionError(error) from e

    def get_sample_role_type(self, well_position: WellPosition) -> Optional[str]:
        raw_value = self.get_well_value(well_position)
        if raw_value == "-":
            return None

        value = assert_not_none(
            re.match(r"^([A-Z]+)\d+$", raw_value),
            msg=f"Unable to understand platemap value '{raw_value}' for well position '{well_position}'.",
        ).group(1)

        return assert_not_none(
            PLATEMAP_TO_SAMPLE_ROLE_TYPE.get(value),
            msg=f"Unable to find sample role type for well position '{well_position}'.",
        )


@dataclass(frozen=True)
class Data:
    version: str
    background_info: BackgroundInfo
    results: Results
    analysis_results: list[AnalysisResult]
    plate_type: PlateType
    platemap: Platemap

    def get_experiment_type(self) -> str:
        return self.background_info.experiment_type

    def iter_wells(self) -> Iterator[WellPosition]:
        yield from self.results.iter_wells()

    def get_plate_well_count(self) -> int:
        return self.results.get_plate_well_count()

    def get_well_float_value(self, well_position: WellPosition) -> float:
        return self.results.get_well_float_value(well_position)

    def get_well_str_value(self, well_position: WellPosition) -> str:
        return self.results.get_well_str_value(well_position)

    def get_well_plate_identifier(self) -> str:
        return self.results.barcode

    def get_platemap_well_value(self, well_position: WellPosition) -> str:
        return self.platemap.get_well_value(well_position)

    def get_sample_role_type(self, well_position: WellPosition) -> Optional[str]:
        return self.platemap.get_sample_role_type(well_position)
