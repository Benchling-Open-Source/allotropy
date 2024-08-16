from __future__ import annotations

from pathlib import PureWindowsPath

import numpy as np
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
from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.unchained_labs_lunatic.constants import (
    CALCULATED_DATA_LOOKUP,
    INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG,
    NO_DATE_OR_TIME_ERROR_MSG,
    NO_DEVICE_IDENTIFIER_ERROR_MSG,
    NO_MEASUREMENT_IN_PLATE_ERROR_MSG,
    NO_WAVELENGTH_COLUMN_ERROR_MSG,
    WAVELENGTH_COLUMNS_RE,
)
from allotropy.parsers.utils.pandas import (
    assert_not_empty_df,
    map_rows,
    read_csv,
    read_excel,
    SeriesData,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


def _create_measurement(
    well_plate_data: SeriesData,
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
        identifier=measurement_identifier,
        detector_wavelength_setting=float(wavelength_column[1:]),
        absorbance=well_plate_data.get(float, wavelength_column, NaN),
        sample_identifier=well_plate_data[str, "Sample name"],
        location_identifier=well_plate_data[str, "Plate Position"],
        well_plate_identifier=well_plate_data.get(str, "Plate ID"),
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
    timestamp: str | None,
) -> MeasurementGroup:
    # Support timestamp from metadata section, but overide with columns in data if specified.
    date = data.get(str, "Date")
    time = data.get(str, "Time")
    if date and time:
        timestamp = f"{date} {time}"

    return MeasurementGroup(
        _measurement_time=assert_not_none(timestamp, msg=NO_DATE_OR_TIME_ERROR_MSG),
        analytical_method_identifier=data.get(str, "Application"),
        plate_well_count=96,
        measurements=[
            _create_measurement(data, wavelength_column, calculated_data)
            for wavelength_column in wavelength_columns
        ],
    )


def _create_metadata(data: SeriesData, file_name: str) -> Metadata:
    device_identifier = data.get(str, "Instrument ID") or data.get(str, "Instrument")
    return Metadata(
        device_type="plate reader",
        model_number="Lunatic",
        product_manufacturer="Unchained Labs",
        device_identifier=assert_not_none(
            device_identifier, msg=NO_DEVICE_IDENTIFIER_ERROR_MSG
        ),
        software_name="Lunatic and Stunner Analysis",
        file_name=file_name,
    )


def _parse_contents(
    named_file_contents: NamedFileContents,
) -> tuple[pd.DataFrame, SeriesData]:
    extension = PureWindowsPath(named_file_contents.original_file_name).suffix
    if extension == ".csv":
        data = read_csv(named_file_contents.contents).replace(np.nan, None)
        assert_not_empty_df(data, "Unable to parse data from empty dataset.")
        # Use the first row in the data block for metadata, since it has all required columns.
        metadata_data = SeriesData(data.iloc[0])
    elif extension == ".xlsx":
        data = read_excel(named_file_contents.contents)

        # Parse the metadata section out and turn it into a series.
        metadata = None
        for idx, row in data.iterrows():
            if row.iloc[0] == "Table":
                index = int(str(idx))
                metadata = data[:index].T
                data.columns = pd.Index(data.iloc[index + 1]).str.replace("\n", " ")
                data = data[index + 2 :]
                assert_not_empty_df(data, "Unable to parse data from empty dataset.")
                break

        if metadata is None:
            msg = "Unable to identify the end of metadata section, expecting a row with 'Table' at start."
            raise AllotropeParsingError(msg)

        if metadata.shape[0] < 2:  # noqa: PLR2004
            msg = "Unable to parse data after metadata section, expecting at least one row in table."
            raise AllotropeConversionError(msg)

        metadata.columns = pd.Index(metadata.iloc[0])
        metadata_data = SeriesData(metadata.iloc[1])
    else:
        msg = f"Unsupported file extension: '{extension}' expected one of 'csv' or 'xlsx'."
        raise AllotropeConversionError(msg)

    return data, metadata_data


def create_data(named_file_contents: NamedFileContents) -> Data:
    data, metadata_data = _parse_contents(named_file_contents)

    wavelength_columns = list(filter(WAVELENGTH_COLUMNS_RE.match, data.columns))
    if not wavelength_columns:
        raise AllotropeConversionError(NO_WAVELENGTH_COLUMN_ERROR_MSG)

    # TODO: we are reporting calculated data for measurements globally instead of in the measurement doc,
    # which is why we have to pass this list to collect them. Why are we reporting globally when data is
    # pertains to the individual measurements?
    calculated_data: list[CalculatedDataItem] = []

    def make_group(data: SeriesData) -> MeasurementGroup:
        return _create_measurement_group(
            data, wavelength_columns, calculated_data, metadata_data.get(str, "Date")
        )

    return Data(
        metadata=_create_metadata(
            metadata_data, named_file_contents.original_file_name
        ),
        measurement_groups=map_rows(data, make_group),
        calculated_data=calculated_data,
    )
