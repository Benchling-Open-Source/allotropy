from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.parsers.chemometec_nucleoview.constants import (
    DEFAULT_ANALYST,
    DEFAULT_EPOCH_TIMESTAMP,
    DEFAULT_MODEL_NUMBER,
)
from allotropy.parsers.utils.pandas import SeriesData


@dataclass
class Row:
    model_number: str
    equipment_serial_number: str | None
    software_version: str | None
    analyst: str
    timestamp: str
    sample_identifier: str
    multiplication_factor: float | None
    viability_percent: float
    live_cell_count: JsonFloat
    dead_cell_count: JsonFloat
    total_cell_count: JsonFloat
    estimated_cell_diameter: JsonFloat

    @staticmethod
    def create(series: pd.Series[str]) -> Row | None:
        data = SeriesData(series)
        # TODO: implement __in__?
        if "Total (cells/ml)" not in data.series.index:
            return None
        return Row(
            model_number=data.try_str_or_none("Instrument type")
            or DEFAULT_MODEL_NUMBER,
            equipment_serial_number=data.try_str_or_none("Instrument s/n"),
            software_version=data.try_str_or_none("Application SW version"),
            analyst=data.try_str_or_none("Operator") or DEFAULT_ANALYST,
            timestamp=data.try_str_or_none("datetime")
            or DEFAULT_EPOCH_TIMESTAMP,
            sample_identifier=data.try_str("Sample ID"),
            multiplication_factor=data.try_float_or_none("Multiplication factor"),
            viability_percent=data.try_float("Viability (%)"),
            # Cell counts are measured in cells/mL, but reported in millions of cells/mL
            live_cell_count=data.try_float_or_nan("Live (cells/ml)") / 1e6,
            dead_cell_count=data.try_float_or_nan("Dead (cells/ml)") / 1e6,
            total_cell_count=data.try_float_or_nan("Total (cells/ml)")
            / 1e6,
            estimated_cell_diameter=data.try_float_or_nan("Estimated cell diameter (um)"),
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[Row]:
        return [row for row in data.apply(Row.create, axis="columns") if row]  # type: ignore[call-overload]
