import re
from typing import Any

import pandas as pd
import pytest

from allotropy.allotrope.pandas_util import read_excel
from allotropy.exceptions import AllotropeConversionError

EXCEL_FILE = "HelloWorld.xlsx"
EXCEL_FILE_TWO_SHEETS = "HelloWorldTwoSheets.xlsx"
EXPECTED_DATA_FRAME = pd.DataFrame({"Hello": ["World"]})


def _get_path(filename: str) -> str:
    return f"tests/allotrope/testdata/{filename}"


def _read_excel(filename: str, **kwargs: Any) -> pd.DataFrame:
    path = _get_path(filename)
    return read_excel(path, **kwargs)


def _test_df(actual: pd.DataFrame) -> None:
    pd.testing.assert_frame_equal(actual, EXPECTED_DATA_FRAME)


@pytest.mark.parametrize("filename", [EXCEL_FILE, EXCEL_FILE_TWO_SHEETS])
def test_read_excel(filename: str) -> None:
    _test_df(_read_excel(filename))


def test_read_excel_fails_parsing() -> None:
    expected_regex = re.escape(
        "Error calling pd.read_excel(): Missing column provided to 'parse_dates': 'MissingColumn' (sheet: 0)"
    )
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        _read_excel(EXCEL_FILE, parse_dates=["MissingColumn"])


def test_read_excel_fails_invalid_output() -> None:
    with pytest.raises(
        AllotropeConversionError, match="Expected a single-sheet Excel file."
    ):
        _read_excel(EXCEL_FILE_TWO_SHEETS, sheet_name=[0, 1])
