import re
from typing import Any

import pandas as pd
import pytest

from allotropy.allotrope.pandas_util import read_excel
from allotropy.exceptions import AllotropeConversionError

FILENAME = "HelloWorld.xlsx"
FILENAME_TWO_SHEETS = "HelloWorldTwoSheets.xlsx"


def _read_excel(filename: str, **kwargs: Any) -> pd.DataFrame:
    path = f"tests/allotrope/testdata/{filename}"
    return read_excel(path, **kwargs)


@pytest.mark.parametrize("filename", [FILENAME, FILENAME_TWO_SHEETS])
def test_read_excel(filename: str) -> None:
    actual = _read_excel(filename)
    expected = pd.DataFrame({"Hello": ["World"]})
    pd.testing.assert_frame_equal(actual, expected)


def test_read_excel_fails_parsing() -> None:
    expected_regex = re.escape(
        "Error calling pd.read_excel(): Missing column provided to 'parse_dates': 'MissingColumn' (sheet: 0)"
    )
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        _read_excel(FILENAME, parse_dates=["MissingColumn"])


def test_read_excel_fails_multiple_sheets_returned() -> None:
    with pytest.raises(
        AllotropeConversionError, match="Expected a single-sheet Excel file."
    ):
        _read_excel(FILENAME_TWO_SHEETS, sheet_name=[0, 1])
