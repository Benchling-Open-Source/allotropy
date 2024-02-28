import re

import pandas as pd
import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.unchained_labs_lunatic.constants import (
    CALCULATED_DATA_LOOKUP,
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
        "Plate ID": well_plate_identifier,
        "Plate Position": location_identifier,
    }
    measurement = Measurement.create(pd.Series(well_plate_data), wavelength_column)

    assert measurement.wavelength == wavelength
    assert measurement.absorbance == absorbance_value
    assert measurement.sample_identifier == sample_identifier
    assert measurement.location_identifier == location_identifier
    assert measurement.well_plate_identifier == well_plate_identifier


@pytest.mark.short
def test_create_measurement_with_no_wavelength_column() -> None:
    well_plate_data = pd.Series(
        {
            "Sample name": "dummy name",
            "Plate ID": "some plate",
            "Plate Position": "B3",
        }
    )
    wavelength_column = "A250"
    msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
    with pytest.raises(AllotropeConversionError, match=msg):
        Measurement.create(well_plate_data, wavelength_column)


@pytest.mark.short
def test_create_measurement_with_incorrect_wavelength_column_format() -> None:
    msg = INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG
    well_plate_data = pd.Series({"Sample name": "dummy name"})
    with pytest.raises(AllotropeConversionError, match=re.escape(msg)):
        Measurement.create(well_plate_data, "Sample name")


@pytest.mark.short
def test_get_calculated_data_from_measurement_for_unknown_wavelength() -> None:
    well_plate_data = {
        "Sample name": "dummy name",
        "Plate ID": "some plate",
        "Plate Position": "B3",
        "A240": 0.5,
        "A260": 0,
        "A260 Concentration (ng/ul)": 4.5,
        "Background (A260)": 0.523,
    }
    measurement = Measurement.create(pd.Series(well_plate_data), "A240")

    assert not measurement.calculated_data


@pytest.mark.short
def test_get_calculated_data_from_measurement_for_A260() -> None:  # noqa: N802
    well_plate_data = {
        "Sample name": "dummy name",
        "Plate ID": "some plate",
        "Plate Position": "B3",
        "A260": 34.5,
        "A260 Concentration (ng/ul)": 4.5,
        "Background (A260)": 0.523,
        "A260/A230": 2.5,
        "A260/A280": 24.9,
    }
    wavelength = "A260"
    measurement = Measurement.create(pd.Series(well_plate_data), wavelength)

    calculated_data_dict = {data.name: data for data in measurement.calculated_data}

    for item in CALCULATED_DATA_LOOKUP[wavelength]:
        if item["column"] in well_plate_data:
            calculated_data_item = calculated_data_dict[item["name"]]
            assert calculated_data_item.value == well_plate_data[item["column"]]


@pytest.mark.short
def test_create_well_plate() -> None:
    analytical_method_identifier = "dummy method"
    date = "17/10/2016"
    time = "7:19:18"
    plate_data = {
        "A250": 23.45,
        "Sample name": "dummy name",
        "Plate Position": "some plate",
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
        "Plate Position": "some plate",
        "Date": "17/10/2016",
        "Time": "7:19:18",
    }
    well_plate = WellPlate.create(pd.Series(plate_data), ["A452", "A280"])

    assert len(well_plate.measurements) == 2


@pytest.mark.short
def test_create_well_plate_without_date_column_then_raise() -> None:
    plate_data = pd.Series(
        {
            "Sample name": "dummy name",
            "Plate Position": "some plate",
            "Time": "7:19:18",
        }
    )
    with pytest.raises(AllotropeConversionError, match=NO_DATE_OR_TIME_ERROR_MSG):
        WellPlate.create(plate_data, [])


@pytest.mark.short
def test_get_calculated_data_document_from_data_with_the_right_values() -> None:
    plate_data = {
        "Sample name": ["batch_id"],
        "Plate Position": ["Plate1"],
        "Application": ["dummyApp"],
        "Date": ["2021-05-20"],
        "Time": ["16:55:51"],
        "Instrument ID": [14],
        "A260": [23.4],
        "A260 Concentration (ng/ul)": [4.5],
    }
    data = Data.create(pd.DataFrame(plate_data))
    calculated_data_document = data.get_calculated_data_document()
    calculated_data_item = calculated_data_document[0]

    assert calculated_data_item.name == "Concentration"
    assert calculated_data_item.value == 4.5
    assert calculated_data_item.unit == "ng/mL"
    assert calculated_data_item.data_source_document[0].feature == "absorbance"


@pytest.mark.short
def test_get_calculated_data_document_from_data_create_right_ammount_of_items() -> None:
    plate_data = {
        "Sample name": ["batch_id"],
        "Plate Position": ["Plate1"],
        "Application": ["dummyApp"],
        "Date": ["2021-05-20"],
        "Time": ["16:55:51"],
        "Instrument ID": [14],
        "A260": [23.4],
        "A260 Concentration (ng/ul)": [4.5],
        "Background (A260)": [0.523],
        "A260/A230": [2.5],
        "A260/A280": [24.9],
    }
    data = Data.create(pd.DataFrame(plate_data))
    calculated_data_document = data.get_calculated_data_document()

    assert len(calculated_data_document) == 4


@pytest.mark.short
def test_get_calculated_data_document_from_data_with_no_calculated_data_columns() -> (
    None
):
    plate_data = {
        "Sample name": ["batch_id"],
        "Plate Position": ["Plate1"],
        "Application": ["dummyApp"],
        "Date": ["2021-05-20"],
        "Time": ["16:55:51"],
        "Instrument ID": [14],
        "A260": [23.4],
    }
    data = Data.create(pd.DataFrame(plate_data))
    calculated_data_document = data.get_calculated_data_document()

    assert not calculated_data_document


@pytest.mark.short
def test_create_data() -> None:
    plate_data = {
        "Sample name": ["batch_id", "batch_id", ""],
        "Plate Position": ["Plate1", "Plate1", "Plate1"],
        "Application": ["dummyApp", "dummyApp", "dummyApp"],
        "Date": ["2021-05-20", "2021-05-20", "2023-05-20"],
        "Time": ["16:55:51", "16:56:51", "16:55:51"],
        "Instrument ID": [14, 14, 14],
        "A250": [23.4, 32.6, 439],
    }
    data = Data.create(pd.DataFrame(plate_data))

    assert data.device_identifier == "14"
    assert len(data.well_plate_list) == 3
