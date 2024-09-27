from __future__ import annotations

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import NaN
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    CalculatedDataItem,
    DataSource,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.unchained_labs_lunatic.constants import (
    CALCULATED_DATA_LOOKUP,
    DETECTION_TYPE,
    DEVICE_TYPE,
    INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG,
    MODEL_NUMBER,
    NO_DATE_OR_TIME_ERROR_MSG,
    NO_DEVICE_IDENTIFIER_ERROR_MSG,
    NO_MEASUREMENT_IN_PLATE_ERROR_MSG,
    NO_WAVELENGTH_COLUMN_ERROR_MSG,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
    WAVELENGTH_COLUMNS_RE,
)
from allotropy.parsers.utils.pandas import (
    map_rows,
    SeriesData,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


def _create_measurement(
    well_plate_data: SeriesData,
    header: SeriesData,
    wavelength_column: str,
    calculated_data: list[CalculatedDataItem],
) -> Measurement:
    if wavelength_column not in well_plate_data.series:
        msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
        raise AllotropeConversionError(msg)

    if not WAVELENGTH_COLUMNS_RE.match(wavelength_column):
        raise AllotropeConversionError(INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG)

    measurement_identifier = random_uuid_str()
    calculated_data.extend(
        _get_calculated_data(well_plate_data, wavelength_column, measurement_identifier)
    )
    return Measurement(
        type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
        device_type=DEVICE_TYPE,
        detection_type=DETECTION_TYPE,
        identifier=measurement_identifier,
        detector_wavelength_setting=float(wavelength_column[1:]),
        absorbance=well_plate_data.get(float, wavelength_column, NaN),
        sample_identifier=well_plate_data[str, "Sample name"],
        location_identifier=well_plate_data[str, "Plate Position"],
        well_plate_identifier=well_plate_data.get(str, "Plate ID"),
        firmware_version=header.get(str, "Client version"),
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
    data: SeriesData,
    wavelength_columns: list[str],
    calculated_data: list[CalculatedDataItem],
    header: SeriesData,
) -> MeasurementGroup:
    timestamp = header.get(str, "Date")
    # Support timestamp from metadata section, but overide with columns in data if specified.
    date = data.get(str, "Date")
    time = data.get(str, "Time")
    if date and time:
        timestamp = f"{date} {time}"

    return MeasurementGroup(
        measurement_time=assert_not_none(timestamp, msg=NO_DATE_OR_TIME_ERROR_MSG),
        analyst=header.get(str, "Test performed by"),
        analytical_method_identifier=data.get(str, "Application"),
        experimental_data_identifier=header.get(str, "Experiment name"),
        plate_well_count=96,
        measurements=[
            _create_measurement(data, header, wavelength_column, calculated_data)
            for wavelength_column in wavelength_columns
        ],
    )


def create_metadata(header: SeriesData, file_name: str) -> Metadata:
    device_identifier = header.get(str, "Instrument ID") or header.get(
        str, "Instrument"
    )
    return Metadata(
        model_number=MODEL_NUMBER,
        product_manufacturer=PRODUCT_MANUFACTURER,
        device_identifier=assert_not_none(
            device_identifier, msg=NO_DEVICE_IDENTIFIER_ERROR_MSG
        ),
        software_name=SOFTWARE_NAME,
        software_version=header.get(str, "Software version"),
        file_name=file_name,
    )


def create_measurement_groups(
    header: SeriesData, data: pd.DataFrame
) -> tuple[list[MeasurementGroup], list[CalculatedDataItem]]:
    wavelength_columns = list(filter(WAVELENGTH_COLUMNS_RE.match, data.columns))
    if not wavelength_columns:
        raise AllotropeConversionError(NO_WAVELENGTH_COLUMN_ERROR_MSG)

    # TODO: we are reporting calculated data for measurements globally instead of in the measurement doc,
    # which is why we have to pass this list to collect them. Why are we reporting globally when data is
    # pertains to the individual measurements?
    calculated_data: list[CalculatedDataItem] = []

    def make_group(data: SeriesData) -> MeasurementGroup:
        return _create_measurement_group(
            data, wavelength_columns, calculated_data, header
        )

    return map_rows(data, make_group), calculated_data
