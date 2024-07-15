from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.thermo_fisher_qubit4.constants import (
    UNSUPPORTED_WAVELENGTH_ERROR,
)
from allotropy.parsers.utils.values import (
    try_float_from_series,
    try_float_from_series_or_nan,
    try_non_nan_float_from_series_or_none,
    try_str_from_series,
    try_str_from_series_or_default,
    try_str_from_series_or_none,
)


@dataclass
class Row:
    timestamp: str
    assay_name: str | None
    fluorescence: float
    batch_identifier: str | None
    sample_identifier: str
    sample_volume: float | None
    excitation: str | None
    emission: str | None
    dilution_factor: float | None
    original_sample_concentration: JsonFloat | None
    original_sample_unit: str | None
    qubit_tube_concentration: JsonFloat | None
    qubit_tube_unit: str | None
    std_1_rfu: float | None
    std_2_rfu: float | None
    std_3_rfu: float | None

    @staticmethod
    def create(data: pd.Series[str]) -> Row:
        emission_wavelength = try_str_from_series_or_default(
            data, "Emission", ""
        ).lower()
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
            sample_identifier=try_str_from_series(data, "Test Name"),
            sample_volume=try_non_nan_float_from_series_or_none(
                data, "Sample Volume (µL)"
            ),
            excitation=try_str_from_series_or_none(data, "Excitation"),
            emission=try_str_from_series(data, "Emission"),
            dilution_factor=try_non_nan_float_from_series_or_none(
                data, "Dilution Factor"
            ),
            original_sample_concentration=try_float_from_series_or_nan(
                data, "Original sample conc."
            ),
            original_sample_unit=try_str_from_series_or_none(
                data, "Units_Original sample conc."
            ),
            qubit_tube_concentration=try_float_from_series_or_nan(
                data, "Qubit® tube conc."
            ),
            qubit_tube_unit=try_str_from_series_or_none(
                data, "Units_Qubit® tube conc."
            ),
            std_1_rfu=try_non_nan_float_from_series_or_none(data, "Std 1 RFU"),
            std_2_rfu=try_non_nan_float_from_series_or_none(data, "Std 2 RFU"),
            std_3_rfu=try_non_nan_float_from_series_or_none(data, "Std 3 RFU"),
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[Row]:
        return list(data.apply(Row.create, axis="columns"))  # type: ignore[call-overload]
