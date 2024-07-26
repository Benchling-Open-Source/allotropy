from __future__ import annotations

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import NaN
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
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _create_measurement(
    well_plate_data: SeriesData, wavelength_column: str
) -> Measurement:
    if wavelength_column not in well_plate_data.series:
        msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
        raise AllotropeConversionError(msg)

    if not WAVELENGTH_COLUMNS_RE.match(wavelength_column):
        raise AllotropeConversionError(INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG)

    measurement_identifier = random_uuid_str()
    return Measurement(
        type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
        identifier=measurement_identifier,
        detector_wavelength_setting=float(wavelength_column[1:]),
        absorbance=well_plate_data.get(float, wavelength_column, NaN),
        sample_identifier=well_plate_data[str, "Sample name"],
        location_identifier=well_plate_data[str, "Plate Position"],
        well_plate_identifier=well_plate_data.get(str, "Plate ID"),
        calculated_data=_get_calculated_data(
            well_plate_data, wavelength_column, measurement_identifier
        ),
    )


def _get_calculated_data(
    well_plate_data: SeriesData,
    wavelength_column: str,
    measurement_identifier: str,
) -> list[CalculatedDataItem]:
    calculated_data = []
    for item in CALCULATED_DATA_LOOKUP.get(wavelength_column, []):
        value = well_plate_data.get(float, item["column"])
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
    data: SeriesData, wavelength_columns: list[str]
) -> MeasurementGroup:
    date = data.get(str, "Date")
    time = data.get(str, "Time")

    if not date or not time:
        raise AllotropeConversionError(NO_DATE_OR_TIME_ERROR_MSG)

    return MeasurementGroup(
        _measurement_time=f"{date} {time}",
        analytical_method_identifier=data.get(str, "Application"),
        plate_well_count=96,
        measurements=[
            _create_measurement(data, wavelength_column)
            for wavelength_column in wavelength_columns
        ],
    )


def _create_metadata(data: pd.DataFrame, file_name: str) -> Metadata:
    return Metadata(
        device_type="plate reader",
        model_number="Lunatic",
        product_manufacturer="Unchained Labs",
        device_identifier=SeriesData(data.iloc[0])[str, "Instrument ID"],
        software_name="Lunatic and Stunner Analysis",
        file_name=file_name,
    )


def create_data(data: pd.DataFrame, file_name: str) -> Data:
    wavelength_columns = list(filter(WAVELENGTH_COLUMNS_RE.match, data.columns))
    if not wavelength_columns:
        raise AllotropeConversionError(NO_WAVELENGTH_COLUMN_ERROR_MSG)

    def make_group(data: SeriesData) -> MeasurementGroup:
        return _create_measurement_group(data, wavelength_columns)

    return Data(
        metadata=_create_metadata(data, file_name),
        measurement_groups=map_rows(data, make_group),
    )
