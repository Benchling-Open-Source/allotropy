import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.NEXCELOM_MATRIX


def test_parse_nexcelom_matrix_file_without_required_fields_then_raise() -> None:
    test_filepath = "tests/parsers/nexcelom_matrix/testdata/nexcelom_matrix_error.xlsx"
    expected_regex = re.escape("Expected non-null value for Live Cells/mL")
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        from_file(test_filepath, VENDOR_TYPE)


class TestParser(ParserTest):
    VENDOR = Vendor.NEXCELOM_MATRIX
