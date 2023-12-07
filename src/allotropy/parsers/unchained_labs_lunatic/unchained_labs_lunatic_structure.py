from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import uuid

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.unchained_labs_lunatic.constants import (
    INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG,
    NO_DATE_OR_TIME_ERROR_MSG,
    NO_MEASUREMENT_IN_PLATE_ERROR_MSG,
    NO_WAVELENGTH_COLUMN_ERROR_MSG,
    WAVELENGTH_COLUMNS_RE,
)
from allotropy.parsers.utils.values import try_float_from_series, try_str_from_series


@dataclass(frozen=True)
class Measurement:
    measurement_identifier: str
    wavelength: float
    absorbance: float
    sample_identifier: str
    location_identifier: str
    well_plate_identifier: Optional[str]

    @staticmethod
    def create(well_plate_data: pd.Series[Any], wavelength_column: str) -> Measurement:
        if wavelength_column not in well_plate_data:
            msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
            raise AllotropeConversionError(msg)

        if not WAVELENGTH_COLUMNS_RE.match(wavelength_column):
            raise AllotropeConversionError(INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG)

        wavelength = float(wavelength_column[1:])

        return Measurement(
            measurement_identifier=str(uuid.uuid4()),
            wavelength=wavelength,
            absorbance=try_float_from_series(well_plate_data, wavelength_column),
            sample_identifier=try_str_from_series(well_plate_data, "Sample name"),
            location_identifier=try_str_from_series(well_plate_data, "Plate ID"),
            well_plate_identifier=well_plate_data.get("Plate Position"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class WellPlate:
    measurement_time: str
    analytical_method_identifier: Optional[str]
    measurements: list[Measurement]

    @staticmethod
    def create(plate_data: pd.Series[Any], wavelength_columns: list[str]) -> WellPlate:
        return WellPlate(
            measurement_time=WellPlate._get_datetime_from_plate(plate_data),
            analytical_method_identifier=plate_data.get("Application"),  # type: ignore[arg-type]
            measurements=[
                Measurement.create(plate_data, wavelength_column)
                for wavelength_column in wavelength_columns
            ],
        )

    @staticmethod
    def _get_datetime_from_plate(plate_data: pd.Series[Any]) -> str:
        date = plate_data.get("Date")
        time = plate_data.get("Time")

        if not date or not time:
            raise AllotropeConversionError(NO_DATE_OR_TIME_ERROR_MSG)

        return f"{date} {time}"


@dataclass(frozen=True)
class Data:
    device_identifier: str
    well_plate_list: list[WellPlate]

    @staticmethod
    def create(data: pd.DataFrame) -> Data:
        device_identifier = Data._get_device_identifier(data.iloc[0])

        wavelength_columns = list(filter(WAVELENGTH_COLUMNS_RE.match, data.columns))
        if not wavelength_columns:
            raise AllotropeConversionError(NO_WAVELENGTH_COLUMN_ERROR_MSG)

        return Data(
            device_identifier=device_identifier,
            well_plate_list=[
                WellPlate.create(data.iloc[i], wavelength_columns)
                for i in range(len(data.index))
            ],
        )

    @staticmethod
    def _get_device_identifier(data: pd.Series[Any]) -> str:
        device_identifier = try_str_from_series(data, "Instrument ID")

        return str(device_identifier)
