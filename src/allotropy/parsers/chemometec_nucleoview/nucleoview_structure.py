from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.parsers.chemometec_nucleoview.constants import (
    DEFAULT_ANALYST,
    DEFAULT_EPOCH_TIMESTAMP,
    DEFAULT_MODEL_NUMBER,
)
from allotropy.parsers.utils.values import (
    try_float_from_series_or_nan,
    try_float_from_series_or_none,
    try_str_from_series,
    try_str_from_series_or_none,
)


@dataclass
class Row:
    analyst: str
    timestamp: str
    sample_identifier: str
    multiplication_factor: float | None
    viability_percent: float | None
    live_cell_count: JsonFloat
    dead_cell_count: JsonFloat
    total_cell_count: JsonFloat
    estimated_cell_diameter: float | None

    data: pd.Series

    @staticmethod
    def create(data: pd.Series):
        # Cell counts are measured in cells/mL, but reported in millions of cells/mL
        live_cell_count = try_float_from_series_or_nan(data, "Live (cells/ml)")
        live_cell_count = live_cell_count / 1e6 if isinstance(live_cell_count, float) else live_cell_count
        dead_cell_count = try_float_from_series_or_nan(data, "Dead (cells/ml)")
        dead_cell_count = dead_cell_count / 1e6 if isinstance(dead_cell_count, float) else dead_cell_count
        total_cell_count = try_float_from_series_or_nan(data, "Total (cells/ml)") / 1e6
        total_cell_count = total_cell_count / 1e6 if isinstance(total_cell_count, float) else total_cell_count

        return Row(
            analyst=try_str_from_series_or_none(data, "Operator") or DEFAULT_ANALYST,
            timestamp=try_str_from_series_or_none(data, "datetime") or DEFAULT_EPOCH_TIMESTAMP,
            sample_identifier=try_str_from_series(data, "Sample ID"),
            multiplication_factor=try_float_from_series_or_none(data, "Multiplication factor"),
            viability_percent=try_float_from_series_or_none(data, "Viability (%)"),
            live_cell_count=live_cell_count,
            dead_cell_count=dead_cell_count,
            total_cell_count=total_cell_count,
            estimated_cell_diameter=try_float_from_series_or_nan(data, "Estimated cell diameter (um)"),
            data=data,
        )


@dataclass
class Data:
    model_number: str
    equipment_serial_number: str | None
    software_version: str | None

    rows: list[Row]

    data: pd.DataFrame

    @staticmethod
    def create(data: pd.DataFrame) -> Data:
        rows = list(data.apply(Row.create, axis="columns"))
        return Data(
            model_number=try_str_from_series_or_none(rows[0].data, "Instrument type") or DEFAULT_MODEL_NUMBER,
            equipment_serial_number=try_str_from_series_or_none(rows[0].data, "Instrument s/n"),
            software_version=try_str_from_series_or_none(rows[0].data, "Application SW version"),
            rows=rows,
            data=data,
        )
