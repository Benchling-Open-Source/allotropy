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
    try_float_from_series,
    try_float_from_series_or_nan,
    try_float_from_series_or_none,
    try_str_from_series,
    try_str_from_series_or_none,
)


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
    def create(data: pd.Series[str]) -> Row | None:
        if "Total (cells/ml)" not in data.index:
            return None
        return Row(
            model_number=try_str_from_series_or_none(data, "Instrument type")
            or DEFAULT_MODEL_NUMBER,
            equipment_serial_number=try_str_from_series_or_none(data, "Instrument s/n"),
            software_version=try_str_from_series_or_none(
                data, "Application SW version"
            ),
            analyst=try_str_from_series_or_none(data, "Operator") or DEFAULT_ANALYST,
            timestamp=try_str_from_series_or_none(data, "datetime")
            or DEFAULT_EPOCH_TIMESTAMP,
            sample_identifier=try_str_from_series(data, "Sample ID"),
            multiplication_factor=try_float_from_series_or_none(
                data, "Multiplication factor"
            ),
            viability_percent=try_float_from_series(data, "Viability (%)"),
            # Cell counts are measured in cells/mL, but reported in millions of cells/mL
            live_cell_count=try_float_from_series_or_nan(data, "Live (cells/ml)") / 1e6,
            dead_cell_count=try_float_from_series_or_nan(data, "Dead (cells/ml)") / 1e6,
            total_cell_count=try_float_from_series_or_nan(data, "Total (cells/ml)")
            / 1e6,
            estimated_cell_diameter=try_float_from_series_or_nan(
                data, "Estimated cell diameter (um)"
            ),
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[Row]:
        return [row for row in data.apply(Row.create, axis="columns") if row]  # type: ignore[call-overload]
