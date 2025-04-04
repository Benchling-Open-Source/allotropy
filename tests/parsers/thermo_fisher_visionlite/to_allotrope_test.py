import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.thermo_fisher_visionlite.constants import (
    UNSUPPORTED_KINETIC_MEASUREMENTS_ERROR,
)
from allotropy.testing.utils import from_file, get_testdata_dir
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.THERMO_FISHER_VISIONLITE
TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_to_allotrope_unsupported_rate_file() -> None:
    filepath = f"{TESTDATA}/exclude/Thermo_VISIONlite_example_rate.csv"
    with pytest.raises(
        AllotropeConversionError, match=UNSUPPORTED_KINETIC_MEASUREMENTS_ERROR
    ):
        from_file(filepath, VENDOR_TYPE)


def test_to_allotrope_incomplete_headers_file() -> None:
    filepath = f"{TESTDATA}/exclude/not_all_headers.csv"
    with pytest.raises(AllotropeConversionError, match="Expected 4 columns, but got 3"):
        from_file(filepath, VENDOR_TYPE)
