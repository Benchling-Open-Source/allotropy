from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    JsonFloat,
    NaN,
)
from allotropy.parsers.chemometec_nucleoview.constants import (
    DEFAULT_ANALYST,
    DEFAULT_EPOCH_TIMESTAMP,
    DEFAULT_MODEL_NUMBER,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData


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
    def create(data: SeriesData) -> Row | None:
        # TODO: implement __in__?
        if "Total (cells/ml)" not in data.series.index:
            return None
        return Row(
            model_number=data.get(str, "Instrument type", DEFAULT_MODEL_NUMBER),
            equipment_serial_number=data.get(str, "Instrument s/n"),
            software_version=data.get(str, "Application SW version"),
            analyst=data.get(str, "Operator", DEFAULT_ANALYST),
            timestamp=data.get(str, "datetime", DEFAULT_EPOCH_TIMESTAMP),
            sample_identifier=data[str, "Sample ID"],
            multiplication_factor=data.get(float, "Multiplication factor"),
            viability_percent=data[float, "Viability (%)"],
            # Cell counts are measured in cells/mL, but reported in millions of cells/mL
            live_cell_count=data.get(float, "Live (cells/ml)", NaN) / 1e6,
            dead_cell_count=data.get(float, "Dead (cells/ml)", NaN) / 1e6,
            total_cell_count=data.get(float, "Total (cells/ml)", NaN) / 1e6,
            estimated_cell_diameter=data.get(
                float, "Estimated cell diameter (um)", NaN
            ),
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[Row]:
        return [row for row in map_rows(data, Row.create) if row]
