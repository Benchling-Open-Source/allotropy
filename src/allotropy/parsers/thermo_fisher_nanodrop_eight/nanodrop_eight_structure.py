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
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
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


ABSORBANCE_RATIOS = [
    (260, 280),
    (260, 230),
]


def _get_concentration(
    conc: JsonFloat | None, unit: str | None
) -> ConcentrationType | None:
    if unit and unit in CONCENTRATION_UNIT_TO_TQUANTITY and isinstance(conc, float):
        cls = CONCENTRATION_UNIT_TO_TQUANTITY[unit]
        return cls(value=conc)

    return None


@dataclass
class SpectroscopyMeasurement:
    id_: str
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
    measurements: list[SpectroscopyMeasurement]
    absorbance_ratios: dict[tuple[int, int], float]

    @staticmethod
    def create(data: pd.Series[str]) -> SpectroscopyRow:
        analyst = try_str_from_series_or_none(data, "user id")
        timestamp = f'{try_str_from_series_or_none(data, "date")} {try_str_from_series_or_none(data, "time")}'
        experiment_type = try_str_from_series_or_none(data, "na type")

        sample_id = try_str_from_series_or_none(data, "sample id") or NOT_APPLICABLE
        well_plate_id = try_str_from_series_or_none(data, "plate id")
        location_id = try_str_from_series_or_none(data, "well")

        is_na_experiment = experiment_type and "NA" in experiment_type

        a260_absorbance = try_float_from_series_or_none(data, "a260")
        a280_absorbance = get_first_not_none(
            lambda key: try_float_from_series_or_none(data, key), ["a280", "a280 10mm"]
        )
        concentration = _get_concentration(
            get_first_not_none(
                lambda key: try_float_from_series_or_none(data, key),
                ["conc.", "conc", "concentration"],
            ),
            try_str_from_series_or_none(data, "units"),
        )

        measurements = []
        # capture concentration on the A260 measurement document if the experiment type is
        # DNA or RNA, protein and other concentration is captured on A280 measurement
        # if there is no experiment type and no 280 column add the concentration here
        capture_concentration = is_na_experiment or not (
            experiment_type or a280_absorbance is not None
        )
        if a260_absorbance:
            measurements.append(
                SpectroscopyMeasurement(
                    random_uuid_str(),
                    concentration if capture_concentration else None,
                    260,
                    a260_absorbance,
                    sample_id,
                    well_plate_id,
                    location_id,
                )
            )

        # capture concentration on the A280 measurement document if the experiment type is
        # something other than DNA or RNA or if the experiment type is not specified
        capture_concentration = not (experiment_type and is_na_experiment)
        if a280_absorbance:
            measurements.append(
                SpectroscopyMeasurement(
                    random_uuid_str(),
                    concentration if capture_concentration else None,
                    280,
                    a280_absorbance,
                    sample_id,
                    well_plate_id,
                    location_id,
                )
            )

        absorbance_ratios = {}
        for numerator, denominator in ABSORBANCE_RATIOS:
            ratio = try_float_from_series_or_none(data, f"{numerator}/{denominator}")
            if ratio:
                absorbance_ratios[(numerator, denominator)] = ratio

        return SpectroscopyRow(
            analyst,
            timestamp,
            experiment_type,
            measurements,
            absorbance_ratios,
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[SpectroscopyRow]:
        data.columns = data.columns.str.lower()
        return list(data.apply(SpectroscopyRow.create, axis="columns"))  # type: ignore[call-overload]
