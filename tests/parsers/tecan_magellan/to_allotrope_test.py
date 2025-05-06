import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, get_testdata_dir
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.TECAN_MAGELLAN
TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_missing_well_positions_column() -> None:
    with pytest.raises(
        AllotropeConversionError, match="Missing well positions column from the file."
    ):
        from_file(f"{TESTDATA}/errors/no_well_positions.xlsx", VENDOR_TYPE)
