from __future__ import annotations

from typing import Any

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    CalculatedDataItem,
    Data,
    DataSource,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
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


def _create_measurement(
    well_plate_data: pd.Series[Any], wavelength_column: str
) -> Measurement:
    if wavelength_column not in well_plate_data:
        msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
        raise AllotropeConversionError(msg)

    if not WAVELENGTH_COLUMNS_RE.match(wavelength_column):
        raise AllotropeConversionError(INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG)

    measurement_identifier = random_uuid_str()
    return Measurement(
        type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
        identifier=measurement_identifier,
        detector_wavelength_setting=float(wavelength_column[1:]),
        absorbance=try_float_from_series_or_nan(well_plate_data, wavelength_column),
        sample_identifier=try_str_from_series(well_plate_data, "Sample name"),
        location_identifier=try_str_from_series(well_plate_data, "Plate Position"),
        well_plate_identifier=try_str_from_series_or_none(well_plate_data, "Plate ID"),
        calculated_data=_get_calculated_data(
            well_plate_data, wavelength_column, measurement_identifier
        ),
    )


def _get_calculated_data(
    well_plate_data: pd.Series[Any],
    wavelength_column: str,
    measurement_identifier: str,
) -> list[CalculatedDataItem]:
    calculated_data = []
    for item in CALCULATED_DATA_LOOKUP.get(wavelength_column, []):
        value = try_float_from_series_or_none(well_plate_data, item["column"])
        if value is None:
            continue

        calculated_data.append(
            CalculatedDataItem(
                identifier=random_uuid_str(),
                name=item["name"],
                value=value,
                unit=item["unit"],
                data_sources=[
                    DataSource(
                        identifier=measurement_identifier,
                        feature=item["feature"],
                    )
                ],
            )
        )
    return calculated_data


def _create_measurement_group(
    plate_data: pd.Series[Any], wavelength_columns: list[str]
) -> MeasurementGroup:
    date = plate_data.get("Date")
    time = plate_data.get("Time")

    if not date or not time:
        raise AllotropeConversionError(NO_DATE_OR_TIME_ERROR_MSG)

    return MeasurementGroup(
        _measurement_time=f"{date} {time}",
        analytical_method_identifier=try_str_from_series_or_none(
            plate_data, "Application"
        ),
        plate_well_count=96,
        measurements=[
            _create_measurement(plate_data, wavelength_column)
            for wavelength_column in wavelength_columns
        ],
    )


def _create_metadata(data: pd.DataFrame) -> Metadata:
    return Metadata(
        device_type="plate reader",
        model_number="Lunatic",
        product_manufacturer="Unchained Labs",
        device_identifier=try_str_from_series(data.iloc[0], "Instrument ID"),
        software_name="Lunatic and Stunner Analysis",
    )


def create_data(data: pd.DataFrame) -> Data:
    wavelength_columns = list(filter(WAVELENGTH_COLUMNS_RE.match, data.columns))
    if not wavelength_columns:
        raise AllotropeConversionError(NO_WAVELENGTH_COLUMN_ERROR_MSG)

    return Data(
        metadata=_create_metadata(data),
        measurement_groups=list(
            data.apply(  # type: ignore[call-overload]
                lambda plate_data: _create_measurement_group(
                    plate_data, wavelength_columns
                ),
                axis="columns",
            )
        ),
    )
