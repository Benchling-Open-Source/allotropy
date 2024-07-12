from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicrogramPerMicroliter,
    TQuantityValueMicrogramPerMilliliter,
    TQuantityValueMilligramPerMilliliter,
    TQuantityValueNanogramPerMicroliter,
    TQuantityValueNanogramPerMilliliter,
    TQuantityValuePicogramPerMilliliter,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    JsonFloat,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float_from_series_or_nan,
    try_float_from_series_or_none,
    try_str_from_series_or_none,
)

ConcentrationType = (
    TQuantityValueMicrogramPerMicroliter
    | TQuantityValueMicrogramPerMilliliter
    | TQuantityValueMilligramPerMilliliter
    | TQuantityValueNanogramPerMicroliter
    | TQuantityValueNanogramPerMilliliter
    | TQuantityValuePicogramPerMilliliter
)
ConcentrationClassType = (
    type[TQuantityValueMicrogramPerMicroliter]
    | type[TQuantityValueMicrogramPerMilliliter]
    | type[TQuantityValueMilligramPerMilliliter]
    | type[TQuantityValueNanogramPerMicroliter]
    | type[TQuantityValueNanogramPerMilliliter]
    | type[TQuantityValuePicogramPerMilliliter]
)

CONCENTRATION_UNIT_TO_TQUANTITY: Mapping[str, ConcentrationClassType] = {
    "ug/ul": TQuantityValueMicrogramPerMicroliter,
    "ug/ml": TQuantityValueMicrogramPerMilliliter,
    "mg/ml": TQuantityValueMilligramPerMilliliter,
    "ng/ul": TQuantityValueNanogramPerMicroliter,
    "ng/ml": TQuantityValueNanogramPerMilliliter,
    "pg/ul": TQuantityValuePicogramPerMilliliter,
}


def _get_concentration(conc: JsonFloat, unit: str | None) -> ConcentrationType | None:
    if unit and unit in CONCENTRATION_UNIT_TO_TQUANTITY and isinstance(conc, float):
        cls = CONCENTRATION_UNIT_TO_TQUANTITY[unit]
        return cls(value=conc)

    return None


@dataclass
class SpectroscopyMeasurement:
    measurement_id: str
    mass_concentration: ConcentrationType | None
    wavelength: int
    absorbance: float
    sample_identifier: str
    well_plate_identifier: str | None
    location_identifier: str | None


@dataclass
class SpectroscopyRow:
    analyst: str | None
    timestamp: str
    experiment_type: str | None
    measurements: dict[float, SpectroscopyMeasurement]
    a260_230: float | None
    a260_280: float | None

    @staticmethod
    def create(data: pd.Series[str]) -> SpectroscopyRow:
        experiment_type = try_str_from_series_or_none(data, "na type")
        is_na_experiment = experiment_type and "NA" in experiment_type

        a280_col = "a280"
        if a280_col not in data.index and "a280 10mm" in data.index:
            a280_col = "a280 10mm"

        concentration_col = None
        for possible_value in ["conc.", "conc", "concentration"]:
            if possible_value in data.index:
                concentration_col = possible_value
        concentration = (
            _get_concentration(
                try_float_from_series_or_nan(data, concentration_col),
                try_str_from_series_or_none(data, "units"),
            )
            if concentration_col
            else None
        )

        sample_id = try_str_from_series_or_none(data, "sample id") or NOT_APPLICABLE
        well_plate_id = try_str_from_series_or_none(data, "plate id")
        location_id = try_str_from_series_or_none(data, "well")

        measurements: dict[float, SpectroscopyMeasurement] = {}
        # capture concentration on the A260 measurement document if the experiment type is
        # DNA or RNA, protein and other concentration is captured on A280 measurment
        # if there is no experiment type and no 280 column add the concentration here
        capture_concentration = is_na_experiment or not (
            experiment_type or a280_col in data.index
        )
        a260_absorbance = try_float_from_series_or_none(data, "a260")
        if a260_absorbance:
            measurements[260] = SpectroscopyMeasurement(
                random_uuid_str(),
                concentration if capture_concentration else None,
                260,
                a260_absorbance,
                sample_id,
                well_plate_id,
                location_id,
            )

        # capture concentration on the A280 measurement document if the experiment type is
        # something other than DNA or RNA or if the experiment type is not specified
        capture_concentration = not (experiment_type and is_na_experiment)
        a280_absorbance = try_float_from_series_or_none(data, a280_col)
        if a280_absorbance:
            measurements[280] = SpectroscopyMeasurement(
                random_uuid_str(),
                concentration if capture_concentration else None,
                280,
                a280_absorbance,
                sample_id,
                well_plate_id,
                location_id,
            )

        timestamp = f'{try_str_from_series_or_none(data, "date")} {try_str_from_series_or_none(data, "time")}'
        return SpectroscopyRow(
            try_str_from_series_or_none(data, "user id"),
            timestamp,
            experiment_type,
            measurements,
            try_float_from_series_or_none(data, "260/230"),
            try_float_from_series_or_none(data, "260/280"),
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[SpectroscopyRow]:
        data.columns = data.columns.str.lower()
        return list(data.apply(SpectroscopyRow.create, axis="columns"))  # type: ignore[call-overload]
