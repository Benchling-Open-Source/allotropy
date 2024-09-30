import re

import pandas as pd
import pytest

from allotropy.allotrope.models.shared.definitions.definitions import NaN
from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError
from allotropy.parsers.utils.pandas import read_csv, read_excel, SeriesData

EXPECTED_DATA_FRAME = pd.DataFrame({"Hello": ["World"]})
TESTDATA = "tests/parsers/utils/testdata"
CSV_FILE = f"{TESTDATA}/HelloWorld.csv"
EXCEL_FILE = f"{TESTDATA}/HelloWorld.xlsx"
EXCEL_FILE_TWO_SHEETS = f"{TESTDATA}/HelloWorldTwoSheets.xlsx"


def test_read_csv() -> None:
    pd.testing.assert_frame_equal(read_csv(CSV_FILE), EXPECTED_DATA_FRAME)


def test_read_csv_fails_parsing() -> None:
    expected_regex = re.escape(
        "Error calling pd.read_csv(): 'utf-8' codec can't decode bytes in position 15-16: invalid continuation byte"
    )
    with pytest.raises(AllotropeParsingError, match=expected_regex):
        read_csv(EXCEL_FILE)


def test_read_csv_fails_invalid_output() -> None:
    expected_regex = re.escape(
        "pd.read_csv() returned a TextFileReader, which is not supported."
    )
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        read_csv(CSV_FILE, iterator=True)


@pytest.mark.parametrize("filename", [EXCEL_FILE, EXCEL_FILE_TWO_SHEETS])
def test_read_excel(filename: str) -> None:
    pd.testing.assert_frame_equal(read_excel(filename), EXPECTED_DATA_FRAME)


def test_read_excel_fails_parsing() -> None:
    expected_regex = re.escape(
        "Error calling pd.read_excel(): Missing column provided to 'parse_dates': 'MissingColumn' (sheet: 0)"
    )
    with pytest.raises(AllotropeParsingError, match=expected_regex):
        read_excel(EXCEL_FILE, parse_dates=["MissingColumn"])


def test_read_excel_fails_invalid_output() -> None:
    with pytest.raises(
        AllotropeConversionError, match="Expected a single-sheet Excel file."
    ):
        read_excel(EXCEL_FILE_TWO_SHEETS, sheet_name=[0, 1])


def test_get() -> None:
    data = SeriesData(pd.Series({"Plate": "4"}))

    assert data.get(int, "Plate") == 4
    assert isinstance(data.get(int, "Plate"), int)
    assert data.get(str, "Plate") == "4"
    assert data.get(float, "Plate") == 4.0
    assert isinstance(data.get(float, "Plate"), float)

    assert data.get(int, "MISSING") is None
    assert data.get(str, "MISSING") is None
    assert data.get(float, "MISSING") is None

    assert data.get(int, "MISSING", 1) == 1
    assert data.get(str, "MISSING", "default") == "default"
    assert data.get(float, "MISSING", 2.0) == 2.0


def test_get_bool() -> None:
    data = SeriesData(
        pd.Series(
            {
                "YES": "yes",
                "ONE": 1,
                "TWO": 2,
            }
        )
    )

    assert data.get(bool, "YES")
    assert data.get(bool, "YES", default=False)
    assert data.get(bool, "ONE")
    assert not data.get(bool, "TWO")
    assert data.get(bool, "MISSING") is None
    assert data.get(bool, "MISSING", False) is False


def test_get_float() -> None:
    data = SeriesData(
        pd.Series(
            {
                "percent": "10.1%",
                "comma": "10,0",
            }
        )
    )

    assert data.get(float, "percent") == 10.1
    assert data.get(float, "comma") == 10.0


def test_get_not_nan() -> None:
    data = SeriesData(
        pd.Series(
            {
                "nan_val": pd.NA,
                "int_val": "1",
            }
        )
    )

    assert data.get(str, "nan_val", validate=SeriesData.NOT_NAN) is None
    assert data.get(str, "int_val", validate=SeriesData.NOT_NAN) == "1"
    assert data.get(float, "nan_val", validate=SeriesData.NOT_NAN) is None
    assert data.get(float, "int_val", validate=SeriesData.NOT_NAN) == 1.0
    assert data.get(float, ["nan_val", "int_val"], validate=SeriesData.NOT_NAN) == 1.0


def test_try_float_or_nan() -> None:
    data = SeriesData(
        pd.Series(
            {
                "nan_val": "NA",
                "int_val": "1",
                "zero_val": "0",
            }
        )
    )

    assert data.get(float, "nan_val", NaN) is NaN
    assert data.get(float, "int_val", NaN) == 1.0
    assert data.get(float, "zero_val", NaN) == 0.0


def test_get_multikey() -> None:
    data = SeriesData(
        pd.Series(
            {
                "Plate": "4",
                "Backup Plate": "8",
                "Bad Plate": "N/A",
            }
        )
    )

    assert data.get(int, ["Plate", "Backup Plate"]) == 4
    assert data.get(int, ["MISSING", "Backup Plate"]) == 8
    assert data.get(int, ["Bad Plate", "Backup Plate"]) == 8


def test_index() -> None:
    data = SeriesData(pd.Series({"Plate": "4"}))

    assert data[int, "Plate"] == 4
    assert isinstance(data[int, "Plate"], int)
    assert data[str, "Plate"] == "4"
    assert data[float, "Plate"] == 4.0
    assert isinstance(data[float, "Plate"], float)

    with pytest.raises(
        AllotropeConversionError, match="Expected non-null value for MISSING."
    ):
        data[int, "MISSING"]

    with pytest.raises(AllotropeConversionError, match="This is an error"):
        data[int, "MISSING", "This is an error"]


def test_index_multikey() -> None:
    data = SeriesData(
        pd.Series(
            {
                "Plate": "4",
                "Backup Plate": "8",
                "Bad Plate": "N/A",
            }
        )
    )

    assert data[int, ["Plate", "Backup Plate"]] == 4
    assert data[int, ["MISSING", "Backup Plate"]] == 8
    assert data[int, ["Bad Plate", "Backup Plate"]] == 8
    with pytest.raises(
        AllotropeConversionError,
        match=re.escape("Expected non-null value for ['Bad Plate', 'Missing Plate']."),
    ):
        data[int, ["Bad Plate", "Missing Plate"]]
