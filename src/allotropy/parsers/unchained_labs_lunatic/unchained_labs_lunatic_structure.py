from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.unchained_labs_lunatic.constants import (
    CALCULATED_DATA_LOOKUP,
    INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG,
    NO_DATE_OR_TIME_ERROR_MSG,
    NO_MEASUREMENT_IN_PLATE_ERROR_MSG,
    NO_WAVELENGTH_COLUMN_ERROR_MSG,
    WAVELENGTH_COLUMNS_RE,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float_from_series_or_nan,
    try_float_from_series_or_none,
    try_str_from_series,
    try_str_from_series_or_none,
)


@dataclass(frozen=True)
class DataSourceItem:
    identifier: str
    feature: str


@dataclass(frozen=True)
class CalculatedDataItem:
    identifier: str
    name: str
    value: float
    unit: str
    data_source_document: list[DataSourceItem]


@dataclass(frozen=True)
class Measurement:
    identifier: str
    wavelength: float
    absorbance: JsonFloat
    sample_identifier: str
    location_identifier: str
    well_plate_identifier: Optional[str]
    calculated_data: list[CalculatedDataItem]

    @staticmethod
    def create(well_plate_data: pd.Series[Any], wavelength_column: str) -> Measurement:
        if wavelength_column not in well_plate_data:
            msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
            raise AllotropeConversionError(msg)

        if not WAVELENGTH_COLUMNS_RE.match(wavelength_column):
            raise AllotropeConversionError(INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG)

        measurement_identifier = random_uuid_str()
        return Measurement(
            identifier=measurement_identifier,
            wavelength=float(wavelength_column[1:]),
            absorbance=try_float_from_series_or_nan(well_plate_data, wavelength_column),
            sample_identifier=try_str_from_series(well_plate_data, "Sample name"),
            location_identifier=try_str_from_series(well_plate_data, "Plate Position"),
            well_plate_identifier=try_str_from_series_or_none(
                well_plate_data, "Plate ID"
            ),
            calculated_data=Measurement._get_calculated_data(
                well_plate_data, wavelength_column, measurement_identifier
            ),
        )

    @staticmethod
    def _get_calculated_data(
        well_plate_data: pd.Series[Any],
        wavelength_column: str,
        measurement_identifier: str,
    ) -> list[CalculatedDataItem]:
        calculated_data_dict = CALCULATED_DATA_LOOKUP.get(wavelength_column)
        if not calculated_data_dict:
            return []

        calculated_data = []
        for item in calculated_data_dict:
            value = try_float_from_series_or_none(well_plate_data, item["column"])
            if value is None:
                continue

            calculated_data.append(
                CalculatedDataItem(
                    identifier=random_uuid_str(),
                    name=item["name"],
                    value=value,
                    unit=item["unit"],
                    data_source_document=[
                        DataSourceItem(
                            identifier=measurement_identifier,
                            feature=item["feature"],
                        )
                    ],
                )
            )
        return calculated_data


@dataclass(frozen=True)
class WellPlate:
    measurement_time: str
    analytical_method_identifier: Optional[str]
    measurements: list[Measurement]

    @staticmethod
    def create(plate_data: pd.Series[Any], wavelength_columns: list[str]) -> WellPlate:
        return WellPlate(
            measurement_time=WellPlate._get_datetime_from_plate(plate_data),
            analytical_method_identifier=try_str_from_series_or_none(
                plate_data, "Application"
            ),
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

    def get_calculated_data_document(self) -> list[CalculatedDataItem]:
        calculated_data_document = []
        for well_plate in self.well_plate_list:
            for measurement in well_plate.measurements:
                calculated_data_document.extend(measurement.calculated_data)

        return calculated_data_document
