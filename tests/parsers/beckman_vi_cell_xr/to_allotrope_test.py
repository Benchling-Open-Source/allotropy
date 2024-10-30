import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, get_testdata_dir
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.BECKMAN_VI_CELL_XR
TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_parse_vi_cell_xr_file_without_required_fields_then_raise() -> None:
    test_filepath = (
        f"{TESTDATA}/v2.04/Beckman_Vi-Cell-XR_example02_instrumentOutput_error.xls"
    )
    expected_regex = re.escape("Expected non-null value for Viability (%).")
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        from_file(test_filepath, VENDOR_TYPE)


def test_parse_vi_cell_xr_file_invalid_datetime_header_then_raise() -> None:
    test_filepath = f"{TESTDATA}/v2.06/Beckman_Vi-Cell-XR_example01_instrumentOutput_invalid_date_header_error.xlsx"
    expected_regex = r"Unable to find key 'Sample date' in dataframe headers: .*"
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        from_file(test_filepath, VENDOR_TYPE)
