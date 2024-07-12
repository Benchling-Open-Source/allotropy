from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.thermo_fisher_qubit4.constants import (
    UNSUPPORTED_WAVELENGTH_ERROR,
)
from allotropy.parsers.utils.values import (
    try_float_from_series,
    try_float_from_series_or_none,
    try_non_nan_float_from_series_or_none,
    try_non_nan_float_or_none,
    try_str_from_series,
    try_str_from_series_or_default,
    try_str_from_series_or_none,
)


@dataclass
class Row:
    timestamp: str
    assay_name: str
    fluorescence: float
    batch_identifier: str
    sample_identifier: str

    sample_volume: float
    excitation: str
    emission: str

    std_1_rfu: float | None
    std_2_rfu: float | None
    std_3_rfu: float | None

    data: pd.Series

    def create(data: pd.Series) -> Row:
        emission_wavelength = try_str_from_series_or_default(data, "Emission", "").lower()
        options = {
            "green": "Green RFU",
            "far red": "Far Red RFU",
        }
        if emission_wavelength not in options:
            message = f"{UNSUPPORTED_WAVELENGTH_ERROR} {emission_wavelength}"
            raise AllotropeConversionError(message)

        return Row(
            timestamp=try_str_from_series(data, "Test Date"),
            assay_name=try_str_from_series_or_none(data, "Assay Name"),
            fluorescence=try_float_from_series(data, options[emission_wavelength]),
            batch_identifier=try_str_from_series_or_none(data, "Run ID"),
            sample_identifier=try_str_from_series_or_none(data, "Test Name"),
            std_1_rfu=try_non_nan_float_from_series_or_none(data, "Std 1 RFU"),
            std_2_rfu=try_non_nan_float_from_series_or_none(data, "Std 2 RFU"),
            std_3_rfu=try_non_nan_float_from_series_or_none(data, "Std 3 RFU"),
            sample_volume=try_non_nan_float_from_series_or_none(data, "Sample Volume (µL)"),
            excitation=try_str_from_series_or_none(data, "Excitation"),
            emission=try_str_from_series(data, "Emission"),
            data=data
        )

    def create_rows(data: pd.DataFrame) -> list[Row]:
        return [
            Row.create(data.iloc[i])
            for i in range(len(data.index))
        ]
