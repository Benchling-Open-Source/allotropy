from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import uuid

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.unchained_labs_lunatic.constants import (
    INCORRECT_WAVELENGHT_COLUMN_FORMAT_ERROR_MSG,
    NO_DATE_OR_TIME_ERROR_MSG,
    NO_WAVELENGHT_COLUMN_ERROR_MSG,
    WAVELENGHT_COLUMNS_RE,
)
from allotropy.parsers.utils.values import assert_not_none


@dataclass(frozen=True)
class Measurement:
    measurement_identifier: str
    wavelenght: float
    absorbance: float
    sample_identifier: Optional[str]
    location_identifier: str
    well_plate_identifier: str

    @staticmethod
    def create(plate_data: pd.Series[Any], wavelenght_column: str) -> Measurement:
        if not WAVELENGHT_COLUMNS_RE.match(wavelenght_column):
            raise AllotropeConversionError(INCORRECT_WAVELENGHT_COLUMN_FORMAT_ERROR_MSG)

        if wavelenght_column not in plate_data:
            msg = f"The plate data does not contain absorbance measurement for {wavelenght_column}."
            raise AllotropeConversionError(msg)
        wavelenght = float(wavelenght_column[1:])

        return Measurement(
            measurement_identifier=str(uuid.uuid4()),
            wavelenght=wavelenght,
            absorbance=assert_not_none(plate_data.get(wavelenght_column)),  # type: ignore[arg-type]
            sample_identifier=plate_data.get("Sample name"),  # type: ignore[arg-type]
            location_identifier=assert_not_none(plate_data.get("Plate ID"), "Plate ID"),  # type: ignore[arg-type]
            well_plate_identifier=assert_not_none(plate_data.get("Plate Position"), "Plate Position"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class Plate:
    measurement_time: str
    analytical_method_identifier: Optional[str]
    measurements: list[Measurement]

    @staticmethod
    def create(plate_data: pd.Series[Any], wavelenght_columns: list[str]) -> Plate:
        return Plate(
            measurement_time=Plate.get_datetime_from_plate(plate_data),
            analytical_method_identifier=plate_data.get("Application"),  # type: ignore[arg-type]
            measurements=[
                Measurement.create(plate_data, wavelenght_column)
                for wavelenght_column in wavelenght_columns
            ],
        )

    @staticmethod
    def get_datetime_from_plate(plate_data: pd.Series[Any]) -> str:
        date = plate_data.get("Date")
        time = plate_data.get("Time")

        if not date or not time:
            raise AllotropeConversionError(NO_DATE_OR_TIME_ERROR_MSG)

        return f"{date} {time}"


@dataclass(frozen=True)
class Data:
    device_identifier: str
    plate_list: list[Plate]

    @staticmethod
    def create(data: pd.DataFrame) -> Data:
        device_identifier = Data.get_device_identifier(data.iloc[0])

        wavelenght_columns = list(filter(WAVELENGHT_COLUMNS_RE.match, data.columns))
        if not wavelenght_columns:
            raise AllotropeConversionError(NO_WAVELENGHT_COLUMN_ERROR_MSG)

        return Data(
            device_identifier=device_identifier,
            plate_list=[
                Plate.create(data.iloc[i], wavelenght_columns)
                for i in range(len(data.index))
            ],
        )

    @staticmethod
    def get_device_identifier(data: pd.Series[Any]) -> str:
        device_identifier = assert_not_none(data.get("Instrument ID"), "Instrument ID")

        return str(device_identifier)
