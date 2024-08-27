import pandas as pd

from allotropy.parsers.methodical_mind.methodical_mind_structure import (
    Header,
    PlateData,
)
from allotropy.parsers.utils.pandas import SeriesData


def test_create_header() -> None:
    data = SeriesData(
        pd.Series(
            {
                "FileName": "Z:\\MSD-WP\\Export\\22M0TALA85_2023-09-08-133933.txt",
                "Version": "MMPR 1.0.38",
                "Model": "HTS",
                "Serial #": "1298873245",
            }
        )
    )
    assert Header.create(data) == Header(
        file_name="Z:\\MSD-WP\\Export\\22M0TALA85_2023-09-08-133933.txt",
        version="MMPR 1.0.38",
        model="HTS",
        serial_number="1298873245",
    )


def test_create_plate_well_data_multiple_rows() -> None:
    header = SeriesData(
        pd.Series(
            {
                "Read Time": "2022-01-01",
                "User": "Jeffy P",
                "Barcode1": "WP002",
            }
        )
    )
    data = [
        [8213, 3475, 5589, 2131, 761],
        [8062, 2341, 3147, 1846, 67778],
        [463, 1485, 15855, 9587, 3226],
        [2181, 6665, 70504, 40572, 13664],
        [839, 2692, 247, 128, 5024],
    ]
    plate_df = pd.DataFrame(
        data, index=["A", "A", "A", "A", "A"], columns=["1", "2", "3", "4", "5"]
    )

    result = PlateData.create(header, plate_df)

    assert result.plate_well_count == 5
    assert len(result.well_data) == 25
    assert result.well_data[0].luminescence == 8213
    assert result.well_data[0].location_identifier == "A1_1"
    assert result.well_data[-1].luminescence == 5024
    assert result.well_data[-1].location_identifier == "A5_5"


def test_create_plate_well_data_single_row() -> None:
    header = SeriesData(
        pd.Series(
            {
                "Read Time": "2022-01-01",
                "User": "Jeffy P",
                "Barcode1": "WP002",
            }
        )
    )
    data = [
        [8213, 3475, 5589, 2131, 761],
        [8062, 2341, 3147, 1846, 67778],
        [463, 1485, 15855, 9587, 3226],
        [2181, 6665, 70504, 40572, 13664],
        [839, 2692, 247, 128, 5024],
    ]
    plate_df = pd.DataFrame(
        data, index=["A", "B", "C", "D", "E"], columns=["1", "2", "3", "4", "5"]
    )

    result = PlateData.create(header, plate_df)

    assert result.plate_well_count == 25
    assert len(result.well_data) == 25
    assert result.well_data[0].luminescence == 8213
    assert result.well_data[0].location_identifier == "A1_1"
    assert result.well_data[-1].luminescence == 5024
    assert result.well_data[-1].location_identifier == "E5_1"
