from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.thermo_fisher_qubit4.constants import (
    UNSUPPORTED_WAVELENGTH_ERROR,
)
from allotropy.parsers.utils.pandas import SeriesData


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
    def create(series: pd.Series[str]) -> Row:
        data = SeriesData(series)
        emission_wavelength = data.try_str_or_default("Emission", "").lower()
        options = {
            "green": "Green RFU",
            "far red": "Far Red RFU",
        }
        if emission_wavelength not in options:
            message = f"{UNSUPPORTED_WAVELENGTH_ERROR} {emission_wavelength}"
            raise AllotropeConversionError(message)

        return Row(
            timestamp=data.try_str("Test Date"),
            assay_name=data.try_str_or_none("Assay Name"),
            fluorescence=data.try_float(options[emission_wavelength]),
            batch_identifier=data.try_str_or_none("Run ID"),
            sample_identifier=data.try_str("Test Name"),
            sample_volume=data.try_non_nan_float_or_none("Sample Volume (µL)"),
            excitation=data.try_str_or_none("Excitation"),
            emission=data.try_str("Emission"),
            dilution_factor=data.try_non_nan_float_or_none("Dilution Factor"),
            original_sample_concentration=data.try_float_or_nan(
                "Original sample conc."
            ),
            original_sample_unit=data.try_str_or_none("Units_Original sample conc."),
            qubit_tube_concentration=data.try_float_or_nan("Qubit® tube conc."),
            qubit_tube_unit=data.try_str_or_none("Units_Qubit® tube conc."),
            std_1_rfu=data.try_non_nan_float_or_none("Std 1 RFU"),
            std_2_rfu=data.try_non_nan_float_or_none("Std 2 RFU"),
            std_3_rfu=data.try_non_nan_float_or_none("Std 3 RFU"),
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[Row]:
        return list(data.apply(Row.create, axis="columns"))  # type: ignore[call-overload]
