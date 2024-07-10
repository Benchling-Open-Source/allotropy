import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

VENDOR_TYPE = Vendor.BECKMAN_VI_CELL_XR


def test_parse_vi_cell_xr_file_without_required_fields_then_raise() -> None:
    test_filepath = "tests/parsers/beckman_vi_cell_xr/testdata/v2.04/Beckman_Vi-Cell-XR_example02_instrumentOutput_error.xls"
    expected_regex = re.escape(
        "Expected to find lines with all of these headers: ['Viability (%)', 'Viable cells/ml (x10^6)']."
    )
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        from_file(test_filepath, VENDOR_TYPE)


def test_parse_vi_cell_xr_file_invalid_datetime_header_then_raise() -> None:
    test_filepath = "tests/parsers/beckman_vi_cell_xr/testdata/v2.06/Beckman_Vi-Cell-XR_example01_instrumentOutput_invalid_date_header_error.xlsx"
    expected_regex = r"Unable to find key 'Sample date/time' in dataframe headers: .*"
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        from_file(test_filepath, VENDOR_TYPE)
