from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    JsonFloat,
    NaN,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.thermo_fisher_qubit4.constants import (
    UNSUPPORTED_WAVELENGTH_ERROR,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData


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
    def create(data: SeriesData) -> Row:
        emission_wavelength = data.get(str, "Emission", "").lower()
        options = {
            "green": "Green RFU",
            "far red": "Far Red RFU",
        }
        if emission_wavelength not in options:
            message = f"{UNSUPPORTED_WAVELENGTH_ERROR} {emission_wavelength}"
            raise AllotropeConversionError(message)

        return Row(
            timestamp=data[str, "Test Date"],
            assay_name=data.get(str, "Assay Name"),
            fluorescence=data[float, options[emission_wavelength]],
            batch_identifier=data.get(str, "Run ID"),
            sample_identifier=data[str, "Test Name"],
            sample_volume=data.get(
                float, "Sample Volume (µL)", validate=SeriesData.NOT_NAN
            ),
            excitation=data.get(str, "Excitation"),
            emission=data[str, "Emission"],
            dilution_factor=data.get(
                float, "Dilution Factor", validate=SeriesData.NOT_NAN
            ),
            original_sample_concentration=data.get(float, "Original sample conc.", NaN),
            original_sample_unit=data.get(str, "Units_Original sample conc."),
            qubit_tube_concentration=data.get(float, "Qubit® tube conc.", NaN),
            qubit_tube_unit=data.get(str, "Units_Qubit® tube conc."),
            std_1_rfu=data.get(float, "Std 1 RFU", validate=SeriesData.NOT_NAN),
            std_2_rfu=data.get(float, "Std 2 RFU", validate=SeriesData.NOT_NAN),
            std_3_rfu=data.get(float, "Std 3 RFU", validate=SeriesData.NOT_NAN),
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[Row]:
        return map_rows(data, Row.create)
