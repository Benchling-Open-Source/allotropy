from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.revvity_kaleido.kaleido_common_structure import WellPosition
from allotropy.parsers.utils.values import (
    try_float,
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
class Data:
    version: str
    background_info: BackgroundInfo
    results: Results

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
