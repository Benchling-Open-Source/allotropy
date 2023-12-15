import re

import pandas as pd
import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.unchained_labs_lunatic.constants import (
    INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG,
    NO_DATE_OR_TIME_ERROR_MSG,
    NO_MEASUREMENT_IN_PLATE_ERROR_MSG,
)
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_structure import (
    Data,
    Measurement,
    WellPlate,
)


@pytest.mark.parametrize(
    "wavelength,absorbance_value,sample_identifier,location_identifier,well_plate_identifier",
    [
        (245, 590, "Sample Name 1", "plateID1", "A1"),
        (230, 90, "Sample Name 2", "plateID2", "A3"),
        (450, 34.9, "Sample Name 3", "plateID3", None),
    ],
)
@pytest.mark.short
def test_create_measurement(
    wavelength: int,
    absorbance_value: float,
    sample_identifier: str,
    location_identifier: str,
    well_plate_identifier: str,
) -> None:
    wavelength_column = f"A{wavelength}"
    well_plate_data = {
        wavelength_column: absorbance_value,
        "Sample name": sample_identifier,
        "Plate ID": location_identifier,
        "Plate Position": well_plate_identifier,
    }
    measurement = Measurement.create(pd.Series(well_plate_data), wavelength_column)

    assert measurement.wavelength == wavelength
    assert measurement.absorbance == absorbance_value
    assert measurement.sample_identifier == sample_identifier
    assert measurement.location_identifier == location_identifier
    assert measurement.well_plate_identifier == well_plate_identifier


@pytest.mark.short
def test_create_measurement_with_no_wavelength_column() -> None:
    well_plate_data = {
        "Sample name": "dummy name",
        "Plate ID": "dummy ID",
        "Plate Position": "B3",
    }
    series = pd.Series(well_plate_data)
    wavelength_column = "A250"
    msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
    with pytest.raises(AllotropeConversionError, match=msg):
        Measurement.create(series, wavelength_column)


@pytest.mark.short
def test_create_title_with_incorrect_wavelength_column_format() -> None:
    msg = INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG
    well_plate_data = pd.Series({"Sample name": "dummy name"})
    with pytest.raises(AllotropeConversionError, match=re.escape(msg)):
        Measurement.create(well_plate_data, "Sample name")


@pytest.mark.short
def test_create_well_plate() -> None:
    analytical_method_identifier = "dummy method"
    date = "17/10/2016"
    time = "7:19:18"
    plate_data = {
        "A250": 23.45,
        "Sample name": "dummy name",
        "Plate ID": "dummy ID",
        "Application": analytical_method_identifier,
        "Date": date,
        "Time": time,
    }
    well_plate = WellPlate.create(pd.Series(plate_data), ["A250"])
    assert well_plate.analytical_method_identifier == analytical_method_identifier
    assert well_plate.measurement_time == f"{date} {time}"
    assert well_plate.measurements[0].absorbance == 23.45


@pytest.mark.short
def test_create_well_plate_with_two_measurements() -> None:
    plate_data = {
        "A452": 23.45,
        "A280": 23.45,
        "Sample name": "dummy name",
        "Plate ID": "dummy ID",
        "Date": "17/10/2016",
        "Time": "7:19:18",
    }
    well_plate = WellPlate.create(pd.Series(plate_data), ["A452", "A280"])

    assert len(well_plate.measurements) == 2


@pytest.mark.short
def test_create_well_plate_without_date_column_then_raise() -> None:
    plate_data = {
        "Sample name": "dummy name",
        "Plate ID": "dummy ID",
        "Time": "7:19:18",
    }
    series = pd.Series(plate_data)
    with pytest.raises(AllotropeConversionError, match=NO_DATE_OR_TIME_ERROR_MSG):
        WellPlate.create(series, [])


@pytest.mark.short
def test_create_data() -> None:
    plate_data = {
        "Sample name": ["batch_id", "batch_id", ""],
        "Plate ID": ["Plate1", "Plate1", "Plate1"],
        "Application": ["dummyApp", "dummyApp", "dummyApp"],
        "Date": ["2021-05-20", "2021-05-20", "2023-05-20"],
        "Time": ["16:55:51", "16:56:51", "16:55:51"],
        "Instrument ID": [14, 14, 14],
        "A250": [23.4, 32.6, 439],
    }
    data = Data.create(pd.DataFrame(plate_data))

    assert data.device_identifier == "14"
    assert len(data.well_plate_list) == 3
